"""Characterization tests for unmodified scripts/fetch_yfinance.py.

A failure means the original screener changed, not that the formula was corrected.
"""

import math

import pandas as pd

from research.tests.conftest import load_script

yf = load_script("fetch_yfinance.py", "fetch_yfinance_original")


def _raw_row(**overrides):
    row = {
        "ticker": "AAA",
        "name": "Aaa",
        "sector": "Technology",
        "industry": "Software - Infrastructure",
        "price": 10.0,
        "market_cap": 1_000_000_000.0,
        "enterprise_value": 1_000_000_000.0,
        "ebit": 100_000_000.0,
        "current_assets": 300.0,
        "current_liabilities": 100.0,
        "net_working_capital": 200.0,
        "net_ppe": 300.0,
        "total_debt": 50.0,
        "total_equity": 100.0,
        "debt_equity": 0.5,
        "current_ratio": 3.0,
        "years_listed": 10.0,
        "data_complete": True,
    }
    row.update(overrides)
    return row


def test_earnings_yield_and_roc_match_the_ratios():
    frame = pd.DataFrame(
        [
            _raw_row(ticker="CHEAP", ebit=250.0, enterprise_value=1000.0, net_working_capital=100.0, net_ppe=150.0),
            _raw_row(ticker="RICH", ebit=80.0, enterprise_value=1000.0, net_working_capital=50.0, net_ppe=50.0),
        ]
    )
    ranked = yf.calculate_magic_formula(frame)
    cheap = ranked.loc[ranked["ticker"] == "CHEAP"].iloc[0]
    rich = ranked.loc[ranked["ticker"] == "RICH"].iloc[0]
    assert cheap["earnings_yield"] == 250.0 / 1000.0
    assert cheap["return_on_capital"] == 250.0 / 250.0
    assert rich["earnings_yield"] == 80.0 / 1000.0
    assert rich["return_on_capital"] == 80.0 / 100.0
    assert int(cheap["roc_rank"]) == 1
    assert int(rich["roc_rank"]) == 2
    assert int(cheap["ey_rank"]) == 1
    assert list(ranked["mf_rank"]) == [1, 2]


def test_roc_is_capped_at_500_percent():
    frame = pd.DataFrame(
        [
            _raw_row(ticker="TINY", ebit=100.0, enterprise_value=100.0, net_working_capital=1.0, net_ppe=1.0),
            _raw_row(ticker="NORMAL", ebit=10.0, enterprise_value=100.0, net_working_capital=20.0, net_ppe=30.0),
        ]
    )
    ranked = yf.calculate_magic_formula(frame)
    tiny = ranked.loc[ranked["ticker"] == "TINY"].iloc[0]
    assert tiny["return_on_capital"] == 5.0
    assert 100.0 / 2.0 > 5.0


def test_zero_enterprise_value_ranks_as_best_earnings_yield():
    frame = pd.DataFrame(
        [
            _raw_row(ticker="ZERO", ebit=10.0, enterprise_value=0.0, net_working_capital=10.0, net_ppe=10.0),
            _raw_row(ticker="OK", ebit=50.0, enterprise_value=100.0, net_working_capital=10.0, net_ppe=10.0),
        ]
    )
    ranked = yf.calculate_magic_formula(frame)
    zero = ranked.loc[ranked["ticker"] == "ZERO"].iloc[0]
    assert math.isinf(zero["earnings_yield"])
    assert int(zero["ey_rank"]) == 1


def test_negative_enterprise_value_is_kept():
    frame = pd.DataFrame(
        [
            _raw_row(ticker="NEG", ebit=10.0, enterprise_value=-100.0, net_working_capital=10.0, net_ppe=10.0),
        ]
    )
    ranked = yf.calculate_magic_formula(frame)
    assert len(ranked) == 1
    assert ranked.iloc[0]["earnings_yield"] == 10.0 / -100.0


def test_nonpositive_tangible_capital_is_dropped():
    frame = pd.DataFrame(
        [
            _raw_row(ticker="NEG", net_working_capital=-80.0, net_ppe=30.0),
            _raw_row(ticker="ZERO", net_working_capital=-50.0, net_ppe=50.0),
            _raw_row(ticker="OK", net_working_capital=10.0, net_ppe=10.0),
        ]
    )
    ranked = yf.calculate_magic_formula(frame)
    assert list(ranked["ticker"]) == ["OK"]


def test_tied_yields_share_the_minimum_rank():
    frame = pd.DataFrame(
        [
            _raw_row(ticker="A", ebit=10.0, enterprise_value=100.0, net_working_capital=10.0, net_ppe=10.0),
            _raw_row(ticker="B", ebit=10.0, enterprise_value=100.0, net_working_capital=20.0, net_ppe=20.0),
            _raw_row(ticker="C", ebit=5.0, enterprise_value=100.0, net_working_capital=10.0, net_ppe=10.0),
        ]
    )
    ranked = yf.calculate_magic_formula(frame)
    ey = dict(zip(ranked["ticker"], ranked["ey_rank"]))
    assert ey["A"] == ey["B"] == 1
    assert ey["C"] == 3


def test_filters_drop_thresholds_and_let_missing_ratios_pass():
    rows = [
        _raw_row(ticker="PASS"),
        _raw_row(ticker="EBIT", ebit=0.0),
        _raw_row(ticker="CAP", market_cap=299_000_000.0),
        _raw_row(ticker="FIN", sector="Financials"),
        _raw_row(ticker="UTIL_IND", industry="Utilities—Renewable"),
        _raw_row(ticker="DE", debt_equity=2.0),
        _raw_row(ticker="CR", current_ratio=1.0),
        _raw_row(ticker="NEW", years_listed=1.0),
        _raw_row(ticker="MISSING", debt_equity=None, current_ratio=None, years_listed=None),
        _raw_row(ticker="NEG_EQ", debt_equity=None, total_equity=-5.0),
        _raw_row(ticker="INCOMPLETE", data_complete=False),
    ]
    filtered = yf.apply_filters(pd.DataFrame(rows), min_market_cap=300_000_000)
    assert set(filtered["ticker"]) == {"PASS", "MISSING", "NEG_EQ"}


def test_industry_substring_excludes_banks_and_keeps_software():
    rows = [
        _raw_row(ticker="SOFT", industry="Software - Infrastructure"),
        _raw_row(ticker="BANK", industry="Banks—Regional"),
        _raw_row(ticker="INS", industry="Insurance Brokers"),
    ]
    filtered = yf.apply_filters(pd.DataFrame(rows), min_market_cap=300_000_000)
    assert list(filtered["ticker"]) == ["SOFT"]


def test_readme_mit_claim_has_no_license_file():
    root = yf.__file__
    assert root.endswith("fetch_yfinance.py")
    license_path = root.replace("scripts/fetch_yfinance.py", "LICENSE")
    import os

    assert not os.path.exists(license_path)

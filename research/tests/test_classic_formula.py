"""Tests for the independent research implementation, not the screener."""

import pandas as pd

from research.classic_formula import apply_repo_ratio_filters, rank_magic_formula


def _row(**overrides):
    row = {
        "ticker": "AAA",
        "ebit": 100.0,
        "enterprise_value": 1_000.0,
        "net_working_capital": 100.0,
        "net_ppe": 100.0,
        "market_cap": 1_000_000_000.0,
        "debt_equity": 0.4,
        "current_ratio": 1.5,
    }
    row.update(overrides)
    return row


def test_classic_does_not_cap_roc_and_drops_nonpositive_ev():
    frame = pd.DataFrame(
        [
            _row(ticker="TINY", ebit=100.0, enterprise_value=50.0, net_working_capital=1.0, net_ppe=1.0),
            _row(ticker="ZERO", ebit=10.0, enterprise_value=0.0),
            _row(ticker="NEG", ebit=10.0, enterprise_value=-20.0),
        ]
    )
    ranked = rank_magic_formula(frame, roc_cap=None)
    assert list(ranked["ticker"]) == ["TINY"]
    assert ranked.iloc[0]["return_on_capital"] == 50.0


def test_tie_break_prefers_higher_earnings_yield_then_ticker():
    frame = pd.DataFrame(
        [
            _row(ticker="BBB", ebit=10.0, enterprise_value=100.0, net_working_capital=10.0, net_ppe=10.0),
            _row(ticker="AAA", ebit=10.0, enterprise_value=100.0, net_working_capital=10.0, net_ppe=10.0),
            _row(ticker="CCC", ebit=30.0, enterprise_value=100.0, net_working_capital=50.0, net_ppe=50.0),
        ]
    )
    ranked = rank_magic_formula(frame)
    # CCC has the best yield and the worst ROC. AAA and BBB tie on both ratios.
    # Combined scores: CCC = 1 (ey) + 3 (roc) = 4. AAA and BBB = 2 + 1 = 3.
    # AAA wins the remaining tie on ticker.
    assert list(ranked["ticker"]) == ["AAA", "BBB", "CCC"]
    assert list(ranked["mf_rank"]) == [1, 2, 3]


def test_repo_ratio_filter_keeps_missing_values():
    frame = pd.DataFrame(
        [
            _row(ticker="MISS", debt_equity=None, current_ratio=None),
            _row(ticker="DE", debt_equity=2.0),
            _row(ticker="CR", current_ratio=1.0),
            _row(ticker="OK"),
        ]
    )
    kept = apply_repo_ratio_filters(frame)
    assert set(kept["ticker"]) == {"MISS", "OK"}

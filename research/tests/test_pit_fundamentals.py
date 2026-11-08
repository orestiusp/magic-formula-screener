"""Fixture tests for point-in-time SEC selection. Numbers are MSFT companyfacts values."""

from datetime import date

from research.pit_fundamentals import (
    balance_sheet_snapshot,
    snapshot_from_slim,
    ttm_operating_income,
    weighted_average_basic_shares,
)

ASOF_BEFORE_Q1 = date(2026, 9, 30)
ASOF_AFTER_Q1 = date(2026, 11, 8)


def _oi(start, end, filed, val, form):
    return {"start": start, "end": end, "filed": filed, "form": form, "accn": filed, "val": val, "fp": "FY"}


def _instant(end, filed, val, form="10-K"):
    return {"end": end, "filed": filed, "form": form, "accn": filed, "val": val}


OPERATING_INCOME = [
    _oi("2024-07-01", "2025-06-30", "2025-07-30", 128_528_000_000, "10-K"),
    # Later restatement of the same year. Visible only after it is filed.
    _oi("2024-07-01", "2025-06-30", "2026-07-29", 128_528_000_000, "10-K"),
    _oi("2024-07-01", "2025-03-31", "2025-04-30", 90_567_000_000, "10-Q"),
    _oi("2025-07-01", "2025-09-30", "2025-10-29", 37_961_000_000, "10-Q"),
    _oi("2025-07-01", "2025-12-31", "2026-01-28", 76_236_000_000, "10-Q"),
    _oi("2025-10-01", "2025-12-31", "2026-01-28", 38_275_000_000, "10-Q"),
    _oi("2025-07-01", "2026-03-31", "2026-04-29", 114_634_000_000, "10-Q"),
    _oi("2026-01-01", "2026-03-31", "2026-04-29", 38_398_000_000, "10-Q"),
    _oi("2025-07-01", "2026-06-30", "2026-07-29", 155_237_000_000, "10-K"),
    _oi("2026-07-01", "2026-09-30", "2026-10-28", 45_915_000_000, "10-Q"),
]


def test_september_asof_uses_the_july_10k_not_the_october_10q():
    result = ttm_operating_income(OPERATING_INCOME, ASOF_BEFORE_Q1)
    assert result["ok"] is True
    assert result["method"] == "annual"
    assert result["value"] == 155_237_000_000
    assert result["period_end"] == "2026-06-30"
    assert result["filed"] == "2026-07-29"


def test_november_asof_bridges_the_filed_quarter_without_future_data():
    result = ttm_operating_income(OPERATING_INCOME, ASOF_AFTER_Q1)
    assert result["ok"] is True
    assert result["method"] == "ytd_bridge"
    assert result["value"] == 45_915_000_000 + 155_237_000_000 - 37_961_000_000
    assert result["period_end"] == "2026-09-30"
    assert result["filed"] == "2026-10-28"


def test_future_restatement_is_invisible_and_prior_filing_is_used():
    rows = [
        _oi("2024-07-01", "2025-06-30", "2025-07-30", 100.0, "10-K"),
        _oi("2024-07-01", "2025-06-30", "2025-08-15", 140.0, "10-K"),
    ]
    early = ttm_operating_income(rows, date(2025, 8, 1))
    late = ttm_operating_income(rows, date(2025, 9, 30))
    assert early["value"] == 100.0
    assert late["value"] == 140.0


def test_stale_annual_is_not_eligible():
    rows = [_oi("2023-07-01", "2024-06-30", "2024-07-30", 50.0, "10-K")]
    result = ttm_operating_income(rows, date(2026, 9, 30))
    assert result["ok"] is False
    assert result["reason"] == "stale_report"


def test_balance_sheet_stays_on_the_filing_known_at_asof():
    instants = {
        "AssetsCurrent": [
            _instant("2026-06-30", "2026-07-29", 207_710_000_000),
            _instant("2026-09-30", "2026-10-28", 186_137_000_000, "10-Q"),
        ],
        "LiabilitiesCurrent": [
            _instant("2026-06-30", "2026-07-29", 168_825_000_000),
            _instant("2026-09-30", "2026-10-28", 151_968_000_000, "10-Q"),
        ],
        "PropertyPlantAndEquipmentNet": [
            _instant("2026-06-30", "2026-07-29", 313_076_000_000),
            _instant("2026-09-30", "2026-10-28", 346_844_000_000, "10-Q"),
        ],
        "CashAndCashEquivalentsAtCarryingValue": [
            _instant("2026-06-30", "2026-07-29", 20_935_000_000),
        ],
        "LongTermDebt": [
            _instant("2026-06-30", "2026-07-29", 40_294_000_000),
        ],
        "LongTermDebtCurrent": [
            _instant("2026-06-30", "2026-07-29", 9_227_000_000),
        ],
        "LongTermDebtNoncurrent": [
            _instant("2026-06-30", "2026-07-29", 31_067_000_000),
        ],
        "StockholdersEquity": [
            _instant("2026-06-30", "2026-07-29", 442_387_000_000),
        ],
    }
    early = balance_sheet_snapshot(instants, ASOF_BEFORE_Q1)
    assert early["ok"] is True
    assert early["period_end"] == "2026-06-30"
    assert early["net_working_capital"] == 207_710_000_000 - 168_825_000_000
    assert early["debt"] == 40_294_000_000
    assert early["debt_how"] == "LongTermDebt"
    late = balance_sheet_snapshot(instants, ASOF_AFTER_Q1)
    assert late["ok"] is False
    assert late["reason"] == "no_cash"


def test_missing_debt_tag_is_zero_and_successor_ppe_tag_is_used():
    instants = {
        "AssetsCurrent": [_instant("2026-09-30", "2026-10-28", 100.0, "10-Q")],
        "LiabilitiesCurrent": [_instant("2026-09-30", "2026-10-28", 40.0, "10-Q")],
        "PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization": [
            _instant("2026-09-30", "2026-10-28", 70.0, "10-Q")
        ],
        "CashAndCashEquivalentsAtCarryingValue": [_instant("2026-09-30", "2026-10-28", 5.0, "10-Q")],
    }
    sheet = balance_sheet_snapshot(instants, ASOF_AFTER_Q1)
    assert sheet["ok"] is True
    assert sheet["net_ppe"] == 70.0
    assert sheet["ppe_tag"].endswith("AfterAccumulatedDepreciationAndAmortization")
    assert sheet["debt"] == 0.0
    assert sheet["debt_how"] == "no_debt_tag_assumed_zero"


def test_weighted_average_shares_used_when_instant_count_is_absent():
    rows = [
        _oi("2025-07-01", "2026-06-30", "2026-07-29", 7_400_000_000, "10-K"),
        _oi("2026-07-01", "2026-09-30", "2026-10-28", 7_420_000_000, "10-Q"),
    ]
    early = weighted_average_basic_shares(rows, ASOF_BEFORE_Q1)
    late = weighted_average_basic_shares(rows, ASOF_AFTER_Q1)
    assert early["shares"] == 7_400_000_000
    assert early["source"] == "weighted_average_basic"
    assert late["shares"] == 7_420_000_000
    assert late["end"] == "2026-09-30"


def test_snapshot_does_not_read_october_numbers_in_september():
    slim = {
        "name": "MICROSOFT CORP",
        "operating_income": OPERATING_INCOME,
        "instants": {
            "AssetsCurrent": [_instant("2026-06-30", "2026-07-29", 207_710_000_000)],
            "LiabilitiesCurrent": [_instant("2026-06-30", "2026-07-29", 168_825_000_000)],
            "PropertyPlantAndEquipmentNet": [_instant("2026-06-30", "2026-07-29", 313_076_000_000)],
            "CashAndCashEquivalentsAtCarryingValue": [_instant("2026-06-30", "2026-07-29", 20_935_000_000)],
            "LongTermDebt": [_instant("2026-06-30", "2026-07-29", 40_294_000_000)],
            "StockholdersEquity": [_instant("2026-06-30", "2026-07-29", 442_387_000_000)],
        },
        "shares_dei": [_instant("2026-07-23", "2026-07-29", 7_425_545_491)],
        "shares_gaap": [],
    }
    snap = snapshot_from_slim(slim, ASOF_BEFORE_Q1)
    assert snap["income"]["value"] == 155_237_000_000
    assert snap["shares"]["shares"] == 7_425_545_491
    assert snap["sheet"]["net_ppe"] == 313_076_000_000

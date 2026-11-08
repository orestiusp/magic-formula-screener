"""Point-in-time fundamentals from SEC companyfacts.

Only facts with filed <= as-of and period end <= as-of are visible.
Later restatements are used only after their own filed date.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A"}
STALE_DAYS = 140

CASH_TAGS = (
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    "Cash",
)
DEBT_TAGS = (
    "LongTermDebt",
    "LongTermDebtCurrent",
    "LongTermDebtNoncurrent",
    "ShortTermBorrowings",
    "CommercialPaper",
    "DebtCurrent",
    "LongTermDebtAndCapitalLeaseObligations",
)
PPE_TAGS = (
    "PropertyPlantAndEquipmentNet",
    "PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization",
)
LEASE_TAGS = (
    "OperatingLeaseLiabilityCurrent",
    "OperatingLeaseLiabilityNoncurrent",
    "OperatingLeaseRightOfUseAsset",
)
BALANCE_TAGS = (
    "AssetsCurrent",
    "LiabilitiesCurrent",
    "StockholdersEquity",
    *PPE_TAGS,
    *CASH_TAGS,
    *DEBT_TAGS,
    *LEASE_TAGS,
    "ShortTermInvestments",
)


def parse_date(value: str) -> date:
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def duration_days(start: str, end: str) -> int:
    return (parse_date(end) - parse_date(start)).days


def _visible(rows: list[dict[str, Any]] | None, asof: date) -> list[dict[str, Any]]:
    """Latest filed version of each period that an investor could have seen."""
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows or []:
        if row.get("form") not in FORMS:
            continue
        filed = row.get("filed")
        end = row.get("end")
        if not filed or not end or row.get("val") is None:
            continue
        if parse_date(filed) > asof or parse_date(end) > asof:
            continue
        key = (row.get("start") or "", end)
        accn = row.get("accn") or ""
        current = best.get(key)
        if current is None or (filed, accn) >= (current["filed"], current["accn"]):
            best[key] = {
                "start": row.get("start") or "",
                "end": end,
                "filed": filed,
                "form": row.get("form"),
                "accn": accn,
                "val": float(row["val"]),
            }
    return list(best.values())


def _flows(rows: list[dict[str, Any]] | None, asof: date) -> list[dict[str, Any]]:
    flows = []
    for row in _visible(rows, asof):
        if not row["start"]:
            continue
        days = duration_days(row["start"], row["end"])
        if days <= 0:
            continue
        flows.append(
            {
                **row,
                "days": days,
                "start_d": parse_date(row["start"]),
                "end_d": parse_date(row["end"]),
            }
        )
    return flows


def _chain_ytd(flows: list[dict[str, Any]], fy_end: date, through: date) -> dict[str, Any] | None:
    """Sum non-overlapping quarters from the day after fy_end through `through`."""
    quarters = [
        row
        for row in flows
        if 70 <= row["days"] <= 120 and fy_end < row["end_d"] <= through and row["start_d"] > fy_end
    ]
    quarters.sort(key=lambda row: row["start_d"])
    if not quarters:
        return None
    cursor = fy_end
    total = 0.0
    filed = quarters[0]["filed"]
    used = 0
    for row in quarters:
        gap = (row["start_d"] - cursor).days
        if gap < 0 or gap > 10:
            return None
        total += row["val"]
        cursor = row["end_d"]
        filed = max(filed, row["filed"])
        used += 1
        if cursor == through:
            return {
                "val": total,
                "start_d": quarters[0]["start_d"],
                "end_d": through,
                "days": (through - quarters[0]["start_d"]).days,
                "filed": filed,
                "quarters": used,
            }
    return None


def ttm_operating_income(rows: list[dict[str, Any]] | None, asof: date) -> dict[str, Any]:
    flows = _flows(rows, asof)
    if not flows:
        return {"ok": False, "reason": "no_operating_income"}

    max_end = max(row["end_d"] for row in flows)
    ending = [row for row in flows if row["end_d"] == max_end]
    latest = min(ending, key=lambda row: row["start_d"])
    stale_days = (asof - latest["end_d"]).days
    if stale_days > STALE_DAYS:
        return {
            "ok": False,
            "reason": "stale_report",
            "period_end": latest["end_d"].isoformat(),
            "filed": latest["filed"],
            "stale_days": stale_days,
        }

    if latest["days"] >= 330:
        return {
            "ok": True,
            "value": latest["val"],
            "method": "annual",
            "period_end": latest["end_d"].isoformat(),
            "period_start": latest["start_d"].isoformat(),
            "filed": latest["filed"],
            "stale_days": stale_days,
        }

    annuals = [
        row
        for row in flows
        if 330 <= row["days"] <= 400 and row["end_d"] < latest["end_d"]
    ]
    annuals.sort(key=lambda row: row["end_d"])
    if not annuals:
        return {"ok": False, "reason": "no_prior_annual", "period_end": latest["end_d"].isoformat()}
    annual = annuals[-1]

    cumulative = latest
    if abs((latest["start_d"] - annual["end_d"]).days - 1) > 10:
        rebuilt = _chain_ytd(flows, annual["end_d"], latest["end_d"])
        if rebuilt is None:
            return {
                "ok": False,
                "reason": "interim_not_cumulative",
                "period_end": latest["end_d"].isoformat(),
            }
        cumulative = rebuilt

    target_end = cumulative["end_d"] - timedelta(days=365)
    priors = [
        row
        for row in flows
        if abs((row["end_d"] - target_end).days) <= 14 and abs(row["days"] - cumulative["days"]) <= 20
    ]
    if not priors:
        prior_annuals = [
            row for row in annuals if row["end_d"] < annual["end_d"] and abs((annual["start_d"] - row["end_d"]).days - 1) <= 10
        ]
        if prior_annuals:
            rebuilt_prior = _chain_ytd(flows, prior_annuals[-1]["end_d"], cumulative["end_d"] - timedelta(days=365))
            # The chain target above uses a calendar shift that may miss a 52-week end.
            # Try the prior fiscal year's actual quarter ends within 14 days of target_end.
            if rebuilt_prior is None:
                near = [
                    row["end_d"]
                    for row in flows
                    if abs((row["end_d"] - target_end).days) <= 14 and row["end_d"] > prior_annuals[-1]["end_d"]
                ]
                if near:
                    rebuilt_prior = _chain_ytd(flows, prior_annuals[-1]["end_d"], max(near))
            if rebuilt_prior is not None and abs(rebuilt_prior["days"] - cumulative["days"]) <= 20:
                priors = [rebuilt_prior]
    if not priors:
        return {
            "ok": False,
            "reason": "no_prior_ytd",
            "period_end": cumulative["end_d"].isoformat(),
            "filed": cumulative["filed"],
        }
    prior = min(priors, key=lambda row: (abs((row["end_d"] - target_end).days), abs(row["days"] - cumulative["days"])))
    value = cumulative["val"] + annual["val"] - prior["val"]
    return {
        "ok": True,
        "value": value,
        "method": "ytd_bridge",
        "period_end": cumulative["end_d"].isoformat(),
        "period_start": (prior["start_d"]).isoformat(),
        "filed": max(cumulative["filed"], annual["filed"]),
        "stale_days": stale_days,
        "annual_end": annual["end_d"].isoformat(),
        "annual_filed": annual["filed"],
        "annual_value": annual["val"],
        "ytd_value": cumulative["val"],
        "prior_ytd_value": prior["val"],
    }


def _latest_on_or_before(rows: list[dict[str, Any]] | None, asof: date) -> dict[str, Any] | None:
    visible = [row for row in _visible(rows, asof) if not row["start"]]
    if not visible:
        # Some share facts are instants but a duration-less row already has start "".
        visible = _visible(rows, asof)
        visible = [row for row in visible if row["start"] in ("", None)]
    if not visible:
        return None
    return max(visible, key=lambda row: (row["end"], row["filed"], row["accn"]))


def _value_on_end(rows: list[dict[str, Any]] | None, asof: date, end: str) -> tuple[float | None, str | None]:
    matches = [row for row in _visible(rows, asof) if row["end"] == end and row["start"] in ("", None)]
    if not matches:
        return None, None
    chosen = max(matches, key=lambda row: (row["filed"], row["accn"]))
    return chosen["val"], chosen["filed"]


def interest_bearing_debt(values: dict[str, float | None]) -> tuple[float | None, str]:
    long_term = values.get("LongTermDebt")
    current = values.get("LongTermDebtCurrent")
    noncurrent = values.get("LongTermDebtNoncurrent")
    short_term = values.get("ShortTermBorrowings")
    paper = values.get("CommercialPaper")
    if long_term is not None:
        if (
            current is not None
            and noncurrent is not None
            and abs(long_term - noncurrent) <= 1.0
            and current > 0
            and abs(long_term - (noncurrent + current)) > 1.0
        ):
            return long_term + current, "LongTermDebt_plus_current_portion"
        return long_term, "LongTermDebt"
    if noncurrent is not None or current is not None:
        debt = (noncurrent or 0.0) + (current or 0.0)
        how = "noncurrent_plus_current"
        if short_term is not None:
            return debt + short_term, how + "_plus_short_term_borrowings"
        if paper is not None:
            return debt + paper, how + "_plus_commercial_paper"
        return debt, how
    if short_term is not None or paper is not None:
        return (short_term or 0.0) + (paper or 0.0), "short_term_only"
    if values.get("LongTermDebtAndCapitalLeaseObligations") is not None:
        return values["LongTermDebtAndCapitalLeaseObligations"], "LongTermDebtAndCapitalLeaseObligations"
    if values.get("DebtCurrent") is not None:
        return values["DebtCurrent"], "DebtCurrent"
    return 0.0, "no_debt_tag_assumed_zero"


def balance_sheet_snapshot(instants: dict[str, list[dict[str, Any]]], asof: date) -> dict[str, Any]:
    anchor = _latest_on_or_before(instants.get("AssetsCurrent"), asof)
    if anchor is None:
        return {"ok": False, "reason": "no_current_assets"}
    end = anchor["end"]
    values: dict[str, float | None] = {}
    filed: dict[str, str | None] = {}
    for tag in BALANCE_TAGS:
        value, filed_on = _value_on_end(instants.get(tag), asof, end)
        values[tag] = value
        filed[tag] = filed_on
    assets = values.get("AssetsCurrent")
    liabilities = values.get("LiabilitiesCurrent")
    ppe = None
    ppe_tag = None
    for tag in PPE_TAGS:
        if values.get(tag) is not None:
            ppe = values[tag]
            ppe_tag = tag
            break
    if assets is None or liabilities is None:
        return {"ok": False, "reason": "incomplete_working_capital", "period_end": end}
    if ppe is None:
        return {"ok": False, "reason": "no_net_ppe", "period_end": end}
    cash = None
    cash_tag = None
    for tag in CASH_TAGS:
        if values.get(tag) is not None:
            cash = values[tag]
            cash_tag = tag
            break
    debt, debt_how = interest_bearing_debt(values)
    if cash is None:
        return {"ok": False, "reason": "no_cash", "period_end": end}
    if debt is None:
        return {"ok": False, "reason": "no_debt_tag", "period_end": end}
    lease_noncurrent = values.get("OperatingLeaseLiabilityNoncurrent") or 0.0
    lease_current = values.get("OperatingLeaseLiabilityCurrent") or 0.0
    equity = values.get("StockholdersEquity")
    current_ratio = (assets / liabilities) if liabilities > 0 else None
    debt_equity = (debt / equity) if equity is not None and equity > 0 else None
    return {
        "ok": True,
        "period_end": end,
        "filed": anchor["filed"],
        "current_assets": assets,
        "current_liabilities": liabilities,
        "net_working_capital": assets - liabilities,
        "net_ppe": ppe,
        "ppe_tag": ppe_tag,
        "rou_asset": values.get("OperatingLeaseRightOfUseAsset"),
        "cash": cash,
        "cash_tag": cash_tag,
        "short_term_investments": values.get("ShortTermInvestments"),
        "debt": debt,
        "debt_how": debt_how,
        "operating_lease_liability": lease_noncurrent + lease_current,
        "operating_lease_liability_partial": values.get("OperatingLeaseLiabilityCurrent") is None
        and values.get("OperatingLeaseLiabilityNoncurrent") is not None,
        "equity": equity,
        "current_ratio": current_ratio,
        "debt_equity": debt_equity,
        "tag_filed": {key: value for key, value in filed.items() if value},
    }


def shares_outstanding(rows: list[dict[str, Any]] | None, asof: date) -> dict[str, Any] | None:
    chosen = _latest_on_or_before(rows, asof)
    if chosen is None:
        return None
    return {
        "shares": chosen["val"],
        "end": chosen["end"],
        "filed": chosen["filed"],
        "form": chosen["form"],
        "source": "instant",
    }


def weighted_average_basic_shares(rows: list[dict[str, Any]] | None, asof: date) -> dict[str, Any] | None:
    """Fallback when the cover page does not report shares outstanding."""
    flows = _flows(rows, asof)
    flows = [row for row in flows if 70 <= row["days"] <= 400]
    if not flows:
        return None
    max_end = max(row["end_d"] for row in flows)
    ending = [row for row in flows if row["end_d"] == max_end]
    chosen = min(ending, key=lambda row: row["days"])
    return {
        "shares": chosen["val"],
        "end": chosen["end"],
        "filed": chosen["filed"],
        "form": chosen["form"],
        "source": "weighted_average_basic",
    }


def slim_companyfacts(payload: dict[str, Any]) -> dict[str, Any]:
    facts = payload.get("facts", {})
    gaap = facts.get("us-gaap", {})
    dei = facts.get("dei", {})

    def usd(tag: str) -> list[dict[str, Any]]:
        units = gaap.get(tag, {}).get("units", {}).get("USD", [])
        return units

    def shares(container: dict[str, Any], tag: str) -> list[dict[str, Any]]:
        node = container.get(tag, {}).get("units", {})
        return node.get("shares", [])

    def usd_shares(container: dict[str, Any], tag: str) -> list[dict[str, Any]]:
        node = container.get(tag, {}).get("units", {})
        return node.get("shares", []) or node.get("USD", [])

    instants = {tag: usd(tag) for tag in BALANCE_TAGS}
    return {
        "cik": payload.get("cik"),
        "name": payload.get("entityName"),
        "operating_income": usd("OperatingIncomeLoss"),
        "instants": instants,
        "shares_dei": shares(dei, "EntityCommonStockSharesOutstanding"),
        "shares_gaap": shares(gaap, "CommonStockSharesOutstanding"),
        "shares_basic_average": usd_shares(gaap, "WeightedAverageNumberOfSharesOutstandingBasic"),
    }


def snapshot_from_slim(slim: dict[str, Any], asof: date) -> dict[str, Any]:
    income = ttm_operating_income(slim.get("operating_income"), asof)
    sheet = balance_sheet_snapshot(slim.get("instants") or {}, asof)
    shares = (
        shares_outstanding(slim.get("shares_dei"), asof)
        or shares_outstanding(slim.get("shares_gaap"), asof)
        or weighted_average_basic_shares(slim.get("shares_basic_average"), asof)
    )
    return {"income": income, "sheet": sheet, "shares": shares, "entity": slim.get("name")}

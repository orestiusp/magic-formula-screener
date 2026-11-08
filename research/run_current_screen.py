#!/usr/bin/env python3
"""Run the unmodified screener and check its arithmetic against its own columns.

The S&P 500 file is reused when research/artifacts/current_sp500.csv or
/tmp/mf-cache/sp500.csv already exists, because a second full Yahoo pull is
often rate-limited. Set REFRESH_SP500=1 to force a new pull.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "research" / "artifacts"
ART.mkdir(parents=True, exist_ok=True)
PY = os.environ.get("MF_PYTHON", sys.executable)
USER_TICKERS = ["MSFT", "AMZN", "GOOG", "META", "NFLX", "XOM", "LMT", "MU", "SNPS", "NKE"]


def run_user_set() -> Path:
    destination = ART / "current_user_set.csv"
    log_path = ART / "current_user_set.log"
    cmd = [
        PY,
        str(ROOT / "scripts" / "fetch_yfinance.py"),
        "--universe",
        "custom",
        "--tickers",
        ",".join(USER_TICKERS),
        "--output",
        str(destination),
        "--top",
        "10",
        "--min-market-cap",
        "300000000",
    ]
    completed = subprocess.run(cmd, text=True, capture_output=True)
    log_path.write_text(completed.stdout + "\n" + completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise SystemExit(f"user-set screener failed\n{completed.stderr[-2000:]}")
    return destination


def ensure_sp500() -> Path:
    destination = ART / "current_sp500.csv"
    cached = Path("/tmp/mf-cache/sp500.csv")
    if os.environ.get("REFRESH_SP500") == "1" or (not destination.exists() and not cached.exists()):
        log_path = ART / "current_sp500.log"
        cmd = [
            PY,
            str(ROOT / "scripts" / "fetch_yfinance.py"),
            "--universe",
            "sp500",
            "--output",
            str(destination),
            "--top",
            "30",
            "--min-market-cap",
            "300000000",
        ]
        completed = subprocess.run(cmd, text=True, capture_output=True)
        log_path.write_text(completed.stdout + "\n" + completed.stderr, encoding="utf-8")
        if completed.returncode != 0:
            raise SystemExit(f"sp500 screener failed\n{completed.stderr[-2000:]}")
        return destination
    source = destination if destination.exists() else cached
    if source != destination:
        shutil.copy(source, destination)
    log_source = Path("/tmp/mf-cache/sp500.log")
    if log_source.exists():
        shutil.copy(log_source, ART / "current_sp500.log")
    return destination


def assert_formula(frame: pd.DataFrame, label: str) -> dict:
    ey = frame["ebit"] / frame["enterprise_value"]
    tangible = frame["net_working_capital"] + frame["net_ppe"]
    roc_raw = frame["ebit"] / tangible
    roc_capped = roc_raw.clip(upper=5.0)
    ey_err = (frame["earnings_yield"] - ey).abs().max()
    roc_err = (frame["return_on_capital"] - roc_capped).abs().max()
    if ey_err > 1e-9 or roc_err > 1e-9:
        raise SystemExit(f"{label} formula mismatch ey={ey_err} roc={roc_err}")
    frame = frame.copy()
    frame["mf_score"] = frame["ey_rank"] + frame["roc_rank"]
    score_counts = frame.groupby("mf_score").size()
    return {
        "rows": int(len(frame)),
        "max_abs_ey_error": float(ey_err),
        "max_abs_roc_error": float(roc_err),
        "roc_capped_names": int((roc_raw > 5.0 + 1e-9).sum()),
        "years_listed_populated": int(frame["years_listed"].notna().sum()),
        "tied_score_groups": int((score_counts > 1).sum()),
        "names_in_tied_scores": int(score_counts[score_counts > 1].sum()),
        "duplicate_company_names": int(frame["name"].duplicated().sum()),
    }


def field_audit() -> list[dict]:
    sys.path.insert(0, str(ROOT))
    from research.tests.conftest import load_script

    screener = load_script("fetch_yfinance.py", "fetch_yfinance_audit")
    rows = []
    for ticker in USER_TICKERS:
        fetched = screener.fetch_stock_data(ticker)
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        quarterly_is = stock.quarterly_financials
        quarterly_bs = stock.quarterly_balance_sheet
        ebit_dates = []
        operating_ttm = None
        columns_descending = None
        bs_total_debt = None
        bs_date = None
        if quarterly_is is not None and not quarterly_is.empty:
            columns = list(quarterly_is.columns)
            columns_descending = columns == sorted(columns, reverse=True)
            ebit_dates = [str(col.date()) for col in columns[:4]]
            if "Operating Income" in quarterly_is.index and len(columns) >= 4:
                operating_ttm = float(quarterly_is.loc["Operating Income"].head(4).sum())
        if quarterly_bs is not None and not quarterly_bs.empty:
            bs_date = str(quarterly_bs.columns[0].date())
            latest = quarterly_bs.iloc[:, 0]
            if "Total Debt" in quarterly_bs.index:
                bs_total_debt = float(latest.get("Total Debt"))
        tangible = None
        roc_raw = None
        if fetched.get("net_working_capital") is not None and fetched.get("net_ppe") is not None:
            tangible = float(fetched["net_working_capital"]) + float(fetched["net_ppe"])
            if tangible != 0 and fetched.get("ebit") is not None:
                roc_raw = float(fetched["ebit"]) / tangible
        ev = fetched.get("enterprise_value")
        market_cap = info.get("marketCap")
        total_debt = info.get("totalDebt")
        total_cash = info.get("totalCash")
        ev_identity = None
        if None not in (market_cap, total_debt, total_cash, ev):
            ev_identity = float(market_cap) + float(total_debt) - float(total_cash) - float(ev)
        reason = "passed"
        if not fetched.get("data_complete"):
            reason = "incomplete"
        elif not (fetched.get("ebit") is not None and fetched["ebit"] > 0):
            reason = "nonpositive_ebit"
        elif fetched.get("market_cap") is None or fetched["market_cap"] < 300_000_000:
            reason = "market_cap"
        elif fetched.get("sector") in screener.EXCLUDED_SECTORS:
            reason = "sector"
        elif any(excl.lower() in str(fetched.get("industry", "")).lower() for excl in screener.EXCLUDED_INDUSTRIES):
            reason = "industry"
        elif fetched.get("debt_equity") is not None and fetched["debt_equity"] >= 2.0:
            reason = "debt_equity"
        elif fetched.get("current_ratio") is not None and fetched["current_ratio"] <= 1.0:
            reason = "current_ratio"
        elif fetched.get("years_listed") is not None and fetched["years_listed"] <= 1.0:
            reason = "years_listed"
        elif tangible is None or tangible <= 0:
            reason = "tangible_capital"
        rows.append(
            {
                "ticker": ticker,
                "screen_result": reason,
                "sector": fetched.get("sector"),
                "industry": fetched.get("industry"),
                "price": fetched.get("price"),
                "market_cap": fetched.get("market_cap"),
                "enterprise_value": ev,
                "yahoo_ev_minus_mkt_debt_cash": ev_identity,
                "ebit_ttm": fetched.get("ebit"),
                "ebit_quarter_ends_newest_first": "|".join(ebit_dates),
                "income_statement_columns_descending": columns_descending,
                "operating_income_ttm": operating_ttm,
                "ebit_minus_operating_income": None
                if operating_ttm is None or fetched.get("ebit") is None
                else float(fetched["ebit"]) - operating_ttm,
                "info_total_debt": total_debt,
                "balance_sheet_total_debt": bs_total_debt,
                "balance_sheet_date": bs_date,
                "info_total_cash": total_cash,
                "net_working_capital": fetched.get("net_working_capital"),
                "net_ppe": fetched.get("net_ppe"),
                "tangible_capital": tangible,
                "roc_raw": roc_raw,
                "roc_capped": None if roc_raw is None else min(roc_raw, 5.0),
                "debt_equity": fetched.get("debt_equity"),
                "current_ratio": fetched.get("current_ratio"),
                "years_listed": fetched.get("years_listed"),
                "total_equity": fetched.get("total_equity"),
            }
        )
    return rows


def main() -> None:
    retrieved = datetime.now(timezone.utc).isoformat()
    user_path = run_user_set()
    sp500_path = ensure_sp500()
    user = pd.read_csv(user_path)
    sp500 = pd.read_csv(sp500_path)
    user_check = assert_formula(user, "user set")
    sp500_check = assert_formula(sp500, "sp500")
    fields = field_audit()
    pd.DataFrame(fields).to_csv(ART / "current_field_audit.csv", index=False)
    wanted = {}
    for ticker in USER_TICKERS:
        hit = sp500[sp500["ticker"] == ticker]
        if hit.empty:
            wanted[ticker] = None
        else:
            row = hit.iloc[0]
            wanted[ticker] = {
                "mf_rank": int(row["mf_rank"]),
                "universe": int(len(sp500)),
                "earnings_yield": float(row["earnings_yield"]),
                "return_on_capital": float(row["return_on_capital"]),
                "ey_rank": int(row["ey_rank"]),
                "roc_rank": int(row["roc_rank"]),
                "mf_score": int(row["ey_rank"] + row["roc_rank"]),
            }
    summary = {
        "retrieved_at_utc": retrieved,
        "yfinance_version": yf.__version__,
        "user_set_command": "python scripts/fetch_yfinance.py --universe custom --tickers MSFT,AMZN,GOOG,META,NFLX,XOM,LMT,MU,SNPS,NKE --top 10 --min-market-cap 300000000",
        "sp500_command": "python scripts/fetch_yfinance.py --universe sp500 --top 30 --min-market-cap 300000000",
        "user_set": user_check,
        "sp500": sp500_check,
        "sp500_ranks_for_comparison_names": wanted,
        "field_audit": fields,
        "sources": {
            "constituents": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            "prices_and_financials": "Yahoo Finance via yfinance",
        },
    }
    (ART / "current_screen_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("retrieved_at_utc", "user_set", "sp500", "sp500_ranks_for_comparison_names")}, indent=2))


if __name__ == "__main__":
    main()

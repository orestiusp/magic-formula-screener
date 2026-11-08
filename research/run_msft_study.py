#!/usr/bin/env python3
"""Point-in-time Magic Formula case study. Rules: research/PROTOCOL.md.

This does not modify or call the screener's ranker on historical data.
The screener cannot see filing dates. Outputs land in research/artifacts/.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.classic_formula import REPO_ROC_CAP, apply_repo_ratio_filters, rank_magic_formula
from research.pit_fundamentals import slim_companyfacts, snapshot_from_slim
from research.tests.conftest import load_script

ART = ROOT / "research" / "artifacts"
CACHE = ROOT / "research" / "cache"
SEC_DIR = CACHE / "sec"
SLIM_DIR = CACHE / "slim"
ART.mkdir(parents=True, exist_ok=True)
SEC_DIR.mkdir(parents=True, exist_ok=True)
SLIM_DIR.mkdir(parents=True, exist_ok=True)

UA = "MagicFormulaAudit research@example.com"
USER_TICKERS = ["MSFT", "AMZN", "GOOG", "META", "NFLX", "XOM", "LMT", "MU", "SNPS", "NKE"]
FORMATION_YEARS = list(range(2016, 2027))
COST_BPS = 0.001


def fetch(url: str, destination: Path | None = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read()
    if destination is not None:
        destination.write_bytes(payload)
    return payload


def load_universe() -> pd.DataFrame:
    screener = load_script("fetch_yfinance.py", "fetch_yfinance_universe")
    tickers, sectors = screener.get_sp500_tickers()
    if len(tickers) < 400:
        raise SystemExit(f"Wikipedia S&P 500 list returned {len(tickers)} tickers")
    frame = pd.DataFrame({"ticker": tickers, "gics_sector": [sectors.get(t, "") for t in tickers]})
    frame = frame[~frame["gics_sector"].isin(screener.EXCLUDED_SECTORS)].copy()
    return frame.reset_index(drop=True)


def load_cik_map() -> dict[str, int]:
    path = CACHE / "company_tickers.json"
    if not path.exists():
        fetch("https://www.sec.gov/files/company_tickers.json", path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    mapping = {}
    for item in payload.values():
        mapping[str(item["ticker"]).upper()] = int(item["cik_str"])
    return mapping


def assign_ciks(universe: pd.DataFrame, cik_map: dict[str, int]) -> pd.DataFrame:
    rows = []
    for _, row in universe.iterrows():
        ticker = row["ticker"].upper()
        cik = cik_map.get(ticker) or cik_map.get(ticker.replace("-", ".")) or cik_map.get(ticker.replace(".", "-"))
        rows.append({**row.to_dict(), "cik": cik})
    frame = pd.DataFrame(rows)
    preferred = set(USER_TICKERS)
    chosen = []
    seen = set()
    # Prefer a user-set share class when two classes share a CIK.
    ordered = pd.concat(
        [frame[frame["ticker"].isin(preferred)], frame[~frame["ticker"].isin(preferred)]],
        ignore_index=True,
    )
    for _, row in ordered.iterrows():
        if pd.isna(row["cik"]):
            chosen.append(row)
            continue
        cik = int(row["cik"])
        if cik in seen:
            continue
        seen.add(cik)
        chosen.append(row)
    return pd.DataFrame(chosen).reset_index(drop=True)


def download_facts(ciks: list[int]) -> None:
    missing = [cik for cik in ciks if not (SEC_DIR / f"CIK{cik:010d}.json").exists()]

    def one(cik: int) -> None:
        destination = SEC_DIR / f"CIK{cik:010d}.json"
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
        for attempt in range(4):
            try:
                fetch(url, destination)
                return
            except Exception:
                time.sleep(1.5 * (attempt + 1))
        if not destination.exists():
            destination.write_text("{}", encoding="utf-8")

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(one, cik) for cik in missing]
        for index, future in enumerate(as_completed(futures), start=1):
            future.result()
            if index % 25 == 0 or index == len(futures):
                print(f"  SEC downloads {index}/{len(futures)}", flush=True)


def load_slim(cik: int) -> dict:
    path = SLIM_DIR / f"{cik}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    raw_path = SEC_DIR / f"CIK{cik:010d}.json"
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    slim = slim_companyfacts(payload) if payload else {"cik": cik, "operating_income": [], "instants": {}, "shares_dei": [], "shares_gaap": []}
    path.write_text(json.dumps(slim), encoding="utf-8")
    return slim


def download_prices(tickers: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.Series]]:
    close_frames = []
    adj_frames = []
    splits: dict[str, pd.Series] = {}
    chunk = 40
    for start in range(0, len(tickers), chunk):
        batch = tickers[start : start + chunk]
        print(f"  prices {start + len(batch)}/{len(tickers)}", flush=True)
        data = yf.download(
            batch,
            start="2014-01-01",
            end="2026-11-09",
            auto_adjust=False,
            actions=True,
            group_by="ticker",
            threads=True,
            progress=False,
        )
        for ticker in batch:
            if isinstance(data.columns, pd.MultiIndex):
                if ticker not in data.columns.get_level_values(0):
                    continue
                frame = data[ticker]
            else:
                frame = data
            if "Close" not in frame.columns:
                continue
            close_frames.append(frame["Close"].rename(ticker))
            if "Adj Close" in frame.columns:
                adj_frames.append(frame["Adj Close"].rename(ticker))
            if "Stock Splits" in frame.columns:
                series = frame["Stock Splits"].dropna()
                series = series[series > 0]
                splits[ticker] = series
        time.sleep(1.0)
    close = pd.concat(close_frames, axis=1).sort_index() if close_frames else pd.DataFrame()
    adj = pd.concat(adj_frames, axis=1).sort_index() if adj_frames else pd.DataFrame()
    close.index = _naive_index(close.index)
    adj.index = _naive_index(adj.index)
    return close, adj, splits


def _naive_index(index: pd.Index) -> pd.DatetimeIndex:
    converted = pd.to_datetime(index)
    if getattr(converted, "tz", None) is not None:
        converted = converted.tz_convert("America/New_York").tz_localize(None)
    return pd.DatetimeIndex(converted.normalize())


def price_on(panel: pd.DataFrame, ticker: str, day: pd.Timestamp, window_days: int = 5) -> float | None:
    if ticker not in panel.columns:
        return None
    series = panel[ticker].dropna()
    prior = series.loc[:day]
    if prior.empty:
        return None
    if (day - prior.index[-1]).days > window_days:
        return None
    value = float(prior.iloc[-1])
    if value <= 0:
        return None
    return value


def split_factor(splits: dict[str, pd.Series], ticker: str, after: pd.Timestamp) -> float:
    series = splits.get(ticker)
    if series is None or series.empty:
        return 1.0
    factor = 1.0
    for when, ratio in series.items():
        stamp = pd.Timestamp(when)
        if stamp.tzinfo is not None:
            stamp = stamp.tz_convert("America/New_York").tz_localize(None)
        if stamp.normalize() > after and float(ratio) > 0:
            factor *= float(ratio)
    return factor


def formation_dates(spy: pd.Series) -> list[pd.Timestamp]:
    dates = []
    for year in FORMATION_YEARS:
        target = pd.Timestamp(year, 9, 30)
        prior = spy.dropna().loc[:target]
        if prior.empty:
            continue
        found = prior.index[-1]
        if (target - found).days <= 7:
            dates.append(found)
    return dates


def build_cross_section(universe, slims, asof, close, splits) -> pd.DataFrame:
    rows = []
    asof_date = asof.date()
    for _, company in universe.iterrows():
        ticker = company["ticker"]
        base = {"ticker": ticker, "cik": company["cik"], "gics_sector": company["gics_sector"], "asof": str(asof.date())}
        if pd.isna(company["cik"]):
            rows.append({**base, "eligible": False, "reason": "no_cik"})
            continue
        snap = snapshot_from_slim(slims[int(company["cik"])], asof_date)
        income = snap["income"]
        sheet = snap["sheet"]
        shares = snap["shares"]
        if not income.get("ok"):
            rows.append({**base, "eligible": False, "reason": "income:" + income.get("reason", "bad")})
            continue
        if not sheet.get("ok"):
            rows.append({**base, "eligible": False, "reason": "sheet:" + sheet.get("reason", "bad")})
            continue
        if shares is None:
            rows.append({**base, "eligible": False, "reason": "no_shares"})
            continue
        px = price_on(close, ticker, asof)
        if px is None:
            rows.append({**base, "eligible": False, "reason": "no_price"})
            continue
        factor = split_factor(splits, ticker, pd.Timestamp(shares["end"]))
        shares_adj = float(shares["shares"]) * factor
        market_cap = px * shares_adj
        enterprise_value = market_cap + float(sheet["debt"]) - float(sheet["cash"])
        rows.append(
            {
                **base,
                "eligible": True,
                "reason": "ok",
                "ebit": income["value"],
                "ebit_method": income["method"],
                "ebit_period_end": income["period_end"],
                "ebit_filed": income["filed"],
                "sheet_end": sheet["period_end"],
                "sheet_filed": sheet["filed"],
                "net_working_capital": sheet["net_working_capital"],
                "net_ppe": sheet["net_ppe"],
                "ppe_tag": sheet.get("ppe_tag"),
                "debt": sheet["debt"],
                "debt_how": sheet["debt_how"],
                "cash": sheet["cash"],
                "cash_tag": sheet["cash_tag"],
                "short_term_investments": sheet["short_term_investments"],
                "operating_lease_liability": sheet["operating_lease_liability"],
                "rou_asset": sheet["rou_asset"],
                "equity": sheet["equity"],
                "debt_equity": sheet["debt_equity"],
                "current_ratio": sheet["current_ratio"],
                "shares_reported": shares["shares"],
                "shares_source": shares.get("source"),
                "shares_end": shares["end"],
                "shares_filed": shares["filed"],
                "split_factor": factor,
                "price": px,
                "market_cap": market_cap,
                "enterprise_value": enterprise_value,
            }
        )
    return pd.DataFrame(rows)


def rank_variants(cross: pd.DataFrame) -> dict[str, pd.DataFrame]:
    usable = cross[cross["eligible"] == True].copy()  # noqa: E712
    classic = rank_magic_formula(usable, roc_cap=None)
    repo_input = apply_repo_ratio_filters(usable)
    repo = rank_magic_formula(repo_input, roc_cap=REPO_ROC_CAP)
    return {"classic": classic, "repo_rules": repo}


def lookup_rank(ranked: pd.DataFrame, ticker: str) -> dict:
    if ranked.empty or ticker not in set(ranked["ticker"]):
        return {"in_ranked_universe": False}
    row = ranked.loc[ranked["ticker"] == ticker].iloc[0]
    return {
        "in_ranked_universe": True,
        "mf_rank": int(row["mf_rank"]),
        "mf_score": int(row["mf_score"]),
        "ey_rank": int(row["ey_rank"]),
        "roc_rank": int(row["roc_rank"]),
        "earnings_yield": float(row["earnings_yield"]),
        "return_on_capital": float(row["return_on_capital"]),
        "universe": int(len(ranked)),
    }


def portfolio_weights(ranked: pd.DataFrame, limit: int = 30) -> dict[str, float]:
    if ranked.empty:
        return {}
    names = list(ranked["ticker"].head(limit))
    if not names:
        return {}
    weight = 1.0 / len(names)
    return {ticker: weight for ticker in names}


def period_return(weights: dict[str, float], adj: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp):
    usable = {}
    missing = []
    for ticker, weight in weights.items():
        p0 = price_on(adj, ticker, start)
        p1 = price_on(adj, ticker, end)
        if p0 is None or p1 is None:
            missing.append(ticker)
            continue
        usable[ticker] = (weight, p1 / p0 - 1.0)
    if not usable:
        return 0.0, missing, {}
    weight_sum = sum(weight for weight, _ in usable.values())
    gross = sum((weight / weight_sum) * ret for weight, ret in usable.values())
    grown = {ticker: weight * (1.0 + ret) for ticker, (weight, ret) in usable.items()}
    grown_sum = sum(grown.values())
    drifted = {ticker: value / grown_sum for ticker, value in grown.items()}
    return gross, missing, drifted


def simulate(name: str, weight_schedule: list[tuple[pd.Timestamp, dict[str, float]]], adj: pd.DataFrame, cost: float):
    """Mark wealth at each formation date. Do not trade into the final date."""
    wealth = 1.0
    records = []
    drifted: dict[str, float] = {}
    for index in range(len(weight_schedule) - 1):
        day, target = weight_schedule[index]
        nxt = weight_schedule[index + 1][0]
        keys = set(drifted) | set(target)
        turnover = sum(abs(target.get(ticker, 0.0) - drifted.get(ticker, 0.0)) for ticker in keys)
        wealth *= 1.0 - turnover * cost
        gross, missing, drifted = period_return(target, adj, day, nxt)
        wealth *= 1.0 + gross
        records.append(
            {
                "strategy": name,
                "cost_bps": cost * 10000,
                "date": str(nxt.date()),
                "period_start": str(day.date()),
                "wealth": wealth,
                "turnover": turnover,
                "gross_return": gross,
                "missing_prices": "|".join(missing),
                "holdings": len(target),
            }
        )
    first = weight_schedule[0][0]
    records.insert(
        0,
        {
            "strategy": name,
            "cost_bps": cost * 10000,
            "date": str(first.date()),
            "period_start": "",
            "wealth": 1.0,
            "turnover": 0.0,
            "gross_return": 0.0,
            "missing_prices": "",
            "holdings": len(weight_schedule[0][1]),
        },
    )
    return records


def cagr(wealth: float, days: int) -> float | None:
    if wealth <= 0 or days <= 0:
        return None
    return wealth ** (365.25 / days) - 1.0


def max_drawdown(values: list[float]) -> float | None:
    peak = None
    worst = 0.0
    for value in values:
        peak = value if peak is None else max(peak, value)
        if peak:
            worst = min(worst, value / peak - 1.0)
    return worst


def sanity_check_market_caps(detail: pd.DataFrame) -> dict:
    checks = {}
    for ticker, low, high in (("MSFT", 200e9, 6e12), ("AMZN", 100e9, 6e12)):
        subset = detail[(detail["ticker"] == ticker) & (detail["eligible"] == True)]  # noqa: E712
        if subset.empty:
            checks[ticker] = {"ok": False, "reason": "never_eligible"}
            continue
        sample = subset.iloc[len(subset) // 2]
        ok = low < float(sample["market_cap"]) < high
        checks[ticker] = {
            "ok": bool(ok),
            "asof": sample["asof"],
            "market_cap": float(sample["market_cap"]),
            "price": float(sample["price"]),
            "shares_reported": float(sample["shares_reported"]),
            "split_factor": float(sample["split_factor"]),
        }
        if not ok:
            raise SystemExit(f"Market-cap sanity check failed for {ticker}: {checks[ticker]}")
    return checks


def plot_wealth(wealth: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    labels = {
        "msft_gross": "MSFT buy/hold",
        "spy_gross": "SPY total return",
        "classic_top30_net": "Classic top 30, 10 bps",
        "universe_ew_net": "Eligible universe equal weight, 10 bps",
    }
    for key, label in labels.items():
        subset = wealth[wealth["strategy"] == key]
        if subset.empty:
            continue
        ax.plot(pd.to_datetime(subset["date"]), subset["wealth"], label=label, linewidth=1.8)
    ax.set_ylabel("Growth of $1")
    ax.set_title("September cohort, today's S&P 500 survivors only\nNot evidence the Magic Formula outperforms")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_ranks(ranks: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    subset = ranks[(ranks["variant"] == "classic") & (ranks["ticker"] == "MSFT") & ranks["mf_rank"].notna()]
    if not subset.empty:
        ax.plot(pd.to_datetime(subset["asof"]), subset["mf_rank"], marker="o", label="MSFT classic rank")
        ax.plot(pd.to_datetime(subset["asof"]), subset["universe"], marker=".", linestyle="--", label="Names ranked")
    ax.invert_yaxis()
    ax.set_ylabel("Rank (1 is best)")
    ax.set_title("MSFT rank inside today's non-financial S&P 500 list")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main() -> None:
    started = datetime.now(timezone.utc)
    print("Loading today's S&P 500 list", flush=True)
    universe = assign_ciks(load_universe(), load_cik_map())
    if os.environ.get("PILOT") == "1":
        universe = universe[universe["ticker"].isin(USER_TICKERS)].reset_index(drop=True)
        print("PILOT universe:", list(universe["ticker"]), flush=True)
    universe.to_csv(ART / "universe_today.csv", index=False)
    ciks = [int(cik) for cik in universe["cik"].dropna().unique()]
    print(f"Universe after sector filter and CIK dedupe: {len(universe)} ({len(ciks)} CIKs)", flush=True)
    download_facts(ciks)
    slims = {cik: load_slim(cik) for cik in ciks}
    tickers = list(universe["ticker"]) + ["SPY"]
    print("Downloading prices", flush=True)
    close, adj, splits = download_prices(tickers)
    if "SPY" not in close.columns or close["SPY"].dropna().empty:
        raise SystemExit("SPY prices missing; cannot set the calendar or the benchmark")
    dates = formation_dates(close["SPY"])
    print("Formation dates:", [str(d.date()) for d in dates], flush=True)
    if len(dates) < 2:
        raise SystemExit("Not enough September formation dates in the price history")

    cross_rows = []
    rank_rows = []
    schedules = {"classic": [], "repo_rules": [], "universe_ew": []}
    for asof in dates:
        print(f"Cross section {asof.date()}", flush=True)
        cross = build_cross_section(universe, slims, asof, close, splits)
        cross_rows.append(cross)
        variants = rank_variants(cross)
        schedules["classic"].append((asof, portfolio_weights(variants["classic"], 30)))
        schedules["repo_rules"].append((asof, portfolio_weights(variants["repo_rules"], 30)))
        eligible = cross[cross["eligible"] == True].copy()  # noqa: E712
        # Equal-weight benchmark uses classic eligibility, including names the ratio filters would drop.
        classic_names = set(variants["classic"]["ticker"]) if not variants["classic"].empty else set()
        ew = {ticker: 1.0 / len(classic_names) for ticker in sorted(classic_names)} if classic_names else {}
        schedules["universe_ew"].append((asof, ew))
        for variant, ranked in variants.items():
            for ticker in USER_TICKERS:
                info = lookup_rank(ranked, ticker)
                reason = "not_in_today_universe"
                if ticker in set(cross["ticker"]):
                    reason = str(cross.loc[cross["ticker"] == ticker, "reason"].iloc[0])
                if reason == "ok" and not info["in_ranked_universe"]:
                    reason = "failed_formula_constraints"
                rank_rows.append({"asof": str(asof.date()), "variant": variant, "ticker": ticker, "eligibility_reason": reason, **info})
        print(
            f"  eligible {int(cross['eligible'].sum())}/{len(cross)} classic {len(variants['classic'])} repo {len(variants['repo_rules'])}",
            flush=True,
        )

    detail = pd.concat(cross_rows, ignore_index=True)
    checks = sanity_check_market_caps(detail)
    detail_path_cols = [
        "asof", "ticker", "eligible", "reason", "ebit", "ebit_method", "ebit_period_end", "ebit_filed",
        "sheet_end", "sheet_filed", "net_working_capital", "net_ppe", "ppe_tag", "debt", "debt_how", "cash",
        "short_term_investments", "operating_lease_liability", "rou_asset", "equity", "debt_equity",
        "current_ratio", "shares_reported", "shares_source", "shares_end", "shares_filed", "split_factor", "price",
        "market_cap", "enterprise_value",
    ]
    msft_detail = detail[detail["ticker"] == "MSFT"]
    keep = [col for col in detail_path_cols if col in msft_detail.columns]
    msft_detail[keep].to_csv(ART / "msft_pit_detail.csv", index=False)
    user_detail = detail[detail["ticker"].isin(USER_TICKERS)]
    user_detail[keep].to_csv(ART / "user_set_pit_detail.csv", index=False)
    ranks = pd.DataFrame(rank_rows)
    ranks.to_csv(ART / "user_set_ranks.csv", index=False)

    reason_counts = (
        detail[~detail["eligible"]].groupby(["asof", "reason"]).size().reset_index(name="names")
    )
    reason_counts.to_csv(ART / "ineligible_reasons.csv", index=False)
    coverage = detail.groupby("asof")["eligible"].agg(eligible="sum", listed="count").reset_index()
    coverage.to_csv(ART / "coverage.csv", index=False)

    wealth_rows = []
    for cost, suffix in ((0.0, "gross"), (COST_BPS, "net")):
        for name in ("classic_top30", "repo_rules_top30", "universe_ew"):
            key = {"classic_top30": "classic", "repo_rules_top30": "repo_rules", "universe_ew": "universe_ew"}[name]
            records = simulate(f"{name}_{suffix}", schedules[key], adj, cost)
            wealth_rows.extend(records)
        for ticker, label in (("MSFT", "msft"), ("SPY", "spy")):
            schedule = [(day, {ticker: 1.0}) for day, _ in schedules["classic"]]
            wealth_rows.extend(simulate(f"{label}_{suffix}", schedule, adj, cost))
    wealth = pd.DataFrame(wealth_rows)
    wealth.to_csv(ART / "cumulative_wealth.csv", index=False)

    start = dates[0]
    end = dates[-1]
    span_days = int((end - start).days)
    headlines = []
    for strategy, subset in wealth.groupby("strategy"):
        ordered = subset.sort_values("date")
        final = float(ordered.iloc[-1]["wealth"])
        headlines.append(
            {
                "strategy": strategy,
                "start": str(start.date()),
                "end": str(end.date()),
                "days": span_days,
                "final_wealth": final,
                "total_return": final - 1.0,
                "cagr": cagr(final, span_days),
                "rebalance_date_max_drawdown": max_drawdown(list(ordered["wealth"])),
                "mean_holdings": float(ordered["holdings"].dropna().mean()) if "holdings" in ordered else None,
                "periods_with_missing_prices": int((ordered["missing_prices"].fillna("") != "").sum())
                if "missing_prices" in ordered
                else 0,
            }
        )
    headline_frame = pd.DataFrame(headlines).sort_values("strategy")
    headline_frame.to_csv(ART / "return_summary.csv", index=False)
    plot_wealth(wealth, ART / "cumulative_wealth.png")
    plot_ranks(ranks, ART / "msft_rank.png")

    summary = {
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": "research/PROTOCOL.md",
        "yfinance_version": yf.__version__,
        "universe_rows": int(len(universe)),
        "ciks": len(ciks),
        "formation_dates": [str(day.date()) for day in dates],
        "market_cap_sanity": checks,
        "coverage": coverage.to_dict(orient="records"),
        "debt_how_counts": detail.loc[detail["eligible"] == True, "debt_how"].value_counts().to_dict() if "debt_how" in detail else {},
        "ppe_tag_counts": detail.loc[detail["eligible"] == True, "ppe_tag"].value_counts().to_dict() if "ppe_tag" in detail else {},
        "returns": headline_frame.to_dict(orient="records"),
        "msft_classic_ranks": ranks[(ranks.variant == "classic") & (ranks.ticker == "MSFT")].to_dict(orient="records"),
        "sources": {
            "constituents": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            "sec_tickers": "https://www.sec.gov/files/company_tickers.json",
            "sec_companyfacts": "https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json",
            "prices": "Yahoo Finance via yfinance, auto_adjust=False; Close for enterprise value, Adj Close for total return",
        },
        "bias": "Today's S&P 500 membership. No delisting return. Not a CRSP/Compustat backtest.",
    }
    (ART / "study_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(headline_frame.to_string(index=False))
    print("MSFT classic ranks:")
    print(ranks[(ranks.variant == "classic") & (ranks.ticker == "MSFT")].to_string(index=False))


if __name__ == "__main__":
    main()

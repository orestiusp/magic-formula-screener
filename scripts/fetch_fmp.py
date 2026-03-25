#!/usr/bin/env python3
"""
Magic Formula Screener — Financial Modeling Prep Data Fetcher (Tier 2)

Fallback data source using the FMP API. More reliable than yfinance but
requires a free API key (250 requests/day on free tier).

Sign up: https://financialmodelingprep.com/developer/docs/

Usage:
    python fetch_fmp.py --universe sp500 --api-key YOUR_KEY --output /tmp/mf_raw_data.csv
    python fetch_fmp.py --universe custom --tickers AAPL,MSFT --api-key YOUR_KEY --output /tmp/mf_raw_data.csv

Requires: pip install requests pandas --break-system-packages
"""

import argparse
import sys
import time
import warnings

warnings.filterwarnings("ignore")

try:
    import requests
    import pandas as pd
except ImportError:
    print("ERROR: Missing dependencies. Run: pip install requests pandas --break-system-packages")
    sys.exit(1)


BASE_URL = "https://financialmodelingprep.com/api/v3"

EXCLUDED_SECTORS = {
    "Financial Services", "Financials", "Utilities", "Real Estate",
}

EXCLUDED_INDUSTRIES = {
    "insurance", "banks", "asset management", "capital markets",
    "diversified financial", "consumer finance", "mortgage",
    "thrifts", "reinsurance", "reit", "real estate services",
    "utilities", "regulated electric", "regulated gas",
    "independent power", "renewable",
}


def fmp_get(endpoint: str, api_key: str, params: dict = None) -> dict:
    """Make an FMP API request."""
    params = params or {}
    params["apikey"] = api_key
    url = f"{BASE_URL}/{endpoint}"
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code == 429:
        print("WARNING: FMP rate limit hit. Waiting 60 seconds...")
        time.sleep(60)
        resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_sp500_tickers(api_key: str) -> list:
    """Get S&P 500 constituents from FMP."""
    data = fmp_get("sp500_constituent", api_key)
    return [item["symbol"] for item in data]


def get_sp400_tickers(api_key: str) -> list:
    """Get S&P 400 MidCap constituents — FMP doesn't have a direct endpoint,
    fall back to Wikipedia."""
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_400_companies")
        return tables[0]["Symbol"].str.replace(".", "-", regex=False).tolist()
    except Exception:
        print("WARNING: Could not fetch S&P 400 list.")
        return []


def get_nifty500_tickers() -> list:
    """Fetch Nifty 500 tickers. FMP uses .NS suffix for NSE stocks."""
    # Try NSE archives first
    try:
        import urllib.request
        from io import StringIO
        url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        response = urllib.request.urlopen(req, timeout=15)
        csv_data = response.read().decode("utf-8")
        df = pd.read_csv(StringIO(csv_data))
        symbol_col = [c for c in df.columns if "symbol" in c.lower()][0]
        tickers = [f"{s.strip()}.NS" for s in df[symbol_col].dropna().astype(str).tolist() if s.strip()]
        if len(tickers) > 100:
            print(f"  Fetched {len(tickers)} Nifty 500 tickers from NSE archives")
            return tickers
    except Exception as e:
        print(f"  NSE archives failed: {e}")

    # Fallback: Wikipedia
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/NIFTY_500")
        for table in tables:
            cols_lower = [str(c).lower() for c in table.columns]
            for col_name in ["symbol", "ticker", "nse symbol"]:
                if col_name in cols_lower:
                    idx = cols_lower.index(col_name)
                    real_col = table.columns[idx]
                    symbols = table[real_col].dropna().astype(str).tolist()
                    tickers = [f"{s.strip()}.NS" for s in symbols if s.strip() and s.strip() != "nan"]
                    if len(tickers) > 100:
                        print(f"  Fetched {len(tickers)} Nifty 500 tickers from Wikipedia")
                        return tickers
    except Exception as e:
        print(f"  Wikipedia failed: {e}")

    # Minimal fallback
    print("  WARNING: Using Nifty 50 fallback")
    return [f"{s}.NS" for s in [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC",
        "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT",
        "MARUTI", "HCLTECH", "SUNPHARMA", "TITAN", "BAJFINANCE", "WIPRO",
        "ULTRACEMCO", "ONGC", "NTPC", "TATAMOTORS", "POWERGRID", "M&M",
        "JSWSTEEL", "TATASTEEL", "ADANIENT", "ADANIPORTS", "TECHM",
        "INDUSINDBK", "COALINDIA", "HINDALCO", "BAJAJFINSV", "GRASIM",
        "NESTLEIND", "CIPLA", "DRREDDY", "APOLLOHOSP", "DIVISLAB",
        "BPCL", "EICHERMOT", "BRITANNIA", "HEROMOTOCO", "TATACONSUM",
        "SBILIFE", "HDFCLIFE", "BAJAJ-AUTO", "LTIM", "WIPRO",
    ]]


# --- Market Configuration ---

MARKET_CONFIG = {
    "us": {
        "currency": "USD",
        "currency_symbol": "$",
        "min_market_cap": 300_000_000,
        "cap_display_unit": 1e9,
        "cap_display_suffix": "B",
    },
    "india": {
        "currency": "INR",
        "currency_symbol": "₹",
        "min_market_cap": 25_000_000_000,
        "cap_display_unit": 1e7,
        "cap_display_suffix": "Cr",
    },
}


def detect_market(universe: str) -> str:
    if universe in ("nifty500",):
        return "india"
    return "us"


def fetch_stock_data(ticker: str, api_key: str) -> dict:
    """Fetch all required fields for a single ticker from FMP."""
    try:
        # Key metrics (has most of what we need in one call)
        metrics = fmp_get(f"key-metrics-ttm/{ticker}", api_key)
        profile = fmp_get(f"profile/{ticker}", api_key)
        ratios = fmp_get(f"ratios-ttm/{ticker}", api_key)

        # Income statement for EBIT
        income = fmp_get(f"income-statement/{ticker}", api_key, {"limit": 1})

        # Balance sheet for current assets/liabilities, PPE
        balance = fmp_get(f"balance-sheet-statement/{ticker}", api_key, {"limit": 1})

        p = profile[0] if profile else {}
        m = metrics[0] if metrics else {}
        r = ratios[0] if ratios else {}
        inc = income[0] if income else {}
        bs = balance[0] if balance else {}

        ebit = inc.get("operatingIncome") or inc.get("ebitda")  # operatingIncome ≈ EBIT
        enterprise_value = m.get("enterpriseValueTTM") or p.get("enterpriseValue") or m.get("enterpriseValue")
        current_assets = bs.get("totalCurrentAssets")
        current_liabilities = bs.get("totalCurrentLiabilities")
        net_ppe = bs.get("propertyPlantEquipmentNet")
        total_debt = bs.get("totalDebt") or bs.get("longTermDebt", 0) + bs.get("shortTermDebt", 0)
        total_equity = bs.get("totalStockholdersEquity")
        market_cap = p.get("mktCap")
        sector = p.get("sector", "Unknown")
        industry = p.get("industry", "Unknown")
        price = p.get("price")
        ipo_date = p.get("ipoDate")

        # Derived
        net_working_capital = (current_assets - current_liabilities) if (current_assets and current_liabilities) else None
        debt_equity = (total_debt / total_equity) if (total_debt and total_equity and total_equity > 0) else None
        current_ratio = (current_assets / current_liabilities) if (current_assets and current_liabilities and current_liabilities > 0) else None

        years_listed = None
        if ipo_date:
            from datetime import datetime
            try:
                ipo = datetime.strptime(ipo_date, "%Y-%m-%d")
                years_listed = (datetime.now() - ipo).days / 365.25
            except ValueError:
                pass

        return {
            "ticker": ticker,
            "name": p.get("companyName", ticker),
            "sector": sector,
            "industry": industry,
            "price": price,
            "market_cap": market_cap,
            "enterprise_value": enterprise_value,
            "ebit": ebit,
            "current_assets": current_assets,
            "current_liabilities": current_liabilities,
            "net_working_capital": net_working_capital,
            "net_ppe": net_ppe,
            "total_debt": total_debt,
            "total_equity": total_equity,
            "debt_equity": debt_equity,
            "current_ratio": current_ratio,
            "years_listed": years_listed,
            "data_complete": all(v is not None for v in [ebit, enterprise_value, current_assets, current_liabilities, net_ppe, market_cap, price]),
        }

    except Exception as e:
        return {
            "ticker": ticker,
            "name": ticker,
            "error": str(e),
            "data_complete": False,
        }


def apply_filters(df: pd.DataFrame, min_market_cap: float = 300_000_000) -> pd.DataFrame:
    """Apply enhanced Greenblatt filters. Same logic as yfinance version."""
    original_count = len(df)

    df = df[df["data_complete"] == True].copy()
    print(f"  After data completeness: {len(df)} (removed {original_count - len(df)})")

    before = len(df)
    df = df[df["ebit"] > 0]
    print(f"  After positive EBIT: {len(df)} (removed {before - len(df)})")

    before = len(df)
    df = df[df["market_cap"] >= min_market_cap]
    print(f"  After market cap >${min_market_cap/1e6:.0f}M: {len(df)} (removed {before - len(df)})")

    before = len(df)
    df = df[~df["sector"].isin(EXCLUDED_SECTORS)]
    print(f"  After sector exclusion: {len(df)} (removed {before - len(df)})")

    before = len(df)
    df = df[~df["industry"].apply(lambda x: any(excl in str(x).lower() for excl in EXCLUDED_INDUSTRIES))]
    print(f"  After industry exclusion: {len(df)} (removed {before - len(df)})")

    before = len(df)
    df = df[(df["debt_equity"].isna()) | (df["debt_equity"] < 2.0)]
    print(f"  After D/E <2.0x: {len(df)} (removed {before - len(df)})")

    before = len(df)
    df = df[(df["current_ratio"].isna()) | (df["current_ratio"] > 1.0)]
    print(f"  After current ratio >1.0x: {len(df)} (removed {before - len(df)})")

    before = len(df)
    df = df[(df["years_listed"].isna()) | (df["years_listed"] > 1.0)]
    print(f"  After >1 year listed: {len(df)} (removed {before - len(df)})")

    return df


def calculate_magic_formula(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate MF rankings. Same logic as yfinance version."""
    df["earnings_yield"] = df["ebit"] / df["enterprise_value"]

    tangible_capital = df["net_working_capital"] + df["net_ppe"]
    df["tangible_capital"] = tangible_capital
    df = df[tangible_capital > 0].copy()

    df["return_on_capital"] = df["ebit"] / df["tangible_capital"]
    df["return_on_capital"] = df["return_on_capital"].clip(upper=5.0)

    df["ey_rank"] = df["earnings_yield"].rank(ascending=False, method="min").astype(int)
    df["roc_rank"] = df["return_on_capital"].rank(ascending=False, method="min").astype(int)

    df["mf_rank_raw"] = df["ey_rank"] + df["roc_rank"]
    df = df.sort_values("mf_rank_raw")
    df["mf_rank"] = range(1, len(df) + 1)

    return df


def main():
    parser = argparse.ArgumentParser(description="Magic Formula Screener — FMP data fetcher")
    parser.add_argument("--universe", choices=["sp500", "sp400", "sp500+sp400", "nifty500", "custom"], default="sp500")
    parser.add_argument("--tickers", type=str, default="")
    parser.add_argument("--api-key", type=str, default=None, help="FMP API key (or set FMP_API_KEY env var)")
    parser.add_argument("--output", type=str, default="/tmp/mf_raw_data.csv")
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--min-market-cap", type=float, default=300_000_000)
    args = parser.parse_args()

    # Resolve API key: command line > environment variable
    import os
    api_key = args.api_key or os.environ.get("FMP_API_KEY")
    if not api_key:
        print("ERROR: No FMP API key provided.")
        print("Either pass --api-key YOUR_KEY or set the FMP_API_KEY environment variable.")
        print("Sign up for a free key at: https://financialmodelingprep.com/developer/docs/")
        sys.exit(1)
    args.api_key = api_key

    market = detect_market(args.universe)
    mkt_cfg = MARKET_CONFIG[market]

    if args.min_market_cap == 300_000_000 and market == "india":
        args.min_market_cap = mkt_cfg["min_market_cap"]

    print(f"=== Magic Formula Screener — Financial Modeling Prep ===")
    print(f"Market: {market.upper()} | Currency: {mkt_cfg['currency']} | Min Market Cap: {mkt_cfg['currency_symbol']}{args.min_market_cap/mkt_cfg['cap_display_unit']:.0f}{mkt_cfg['cap_display_suffix']}\n")

    # --- Get tickers ---
    all_tickers = []
    if args.universe in ("sp500", "sp500+sp400"):
        tickers = get_sp500_tickers(args.api_key)
        all_tickers.extend(tickers)
        print(f"S&P 500: {len(tickers)} tickers")

    if args.universe in ("sp400", "sp500+sp400"):
        tickers = get_sp400_tickers(args.api_key)
        all_tickers.extend(tickers)
        print(f"S&P 400: {len(tickers)} tickers")

    if args.universe == "nifty500":
        tickers = get_nifty500_tickers()
        all_tickers.extend(tickers)
        print(f"Nifty 500: {len(tickers)} tickers")

    if args.universe == "custom":
        all_tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
        print(f"Custom: {len(all_tickers)} tickers")

    # --- Check API budget ---
    # FMP free tier: 250 requests/day
    # Each stock needs ~4 API calls (profile, key-metrics, income, balance)
    api_calls_needed = len(all_tickers) * 4
    print(f"\nEstimated API calls needed: {api_calls_needed}")
    if api_calls_needed > 250:
        print(f"WARNING: Free tier limit is 250 calls/day. You need {api_calls_needed}.")
        print(f"Limiting to first {250 // 4} tickers. Upgrade to premium for full universe.")
        all_tickers = all_tickers[:250 // 4]

    # --- Fetch ---
    print(f"\nFetching data for {len(all_tickers)} tickers...\n")

    results = []
    errors = []
    for i, ticker in enumerate(all_tickers):
        if (i + 1) % 25 == 0 or i == 0:
            print(f"  Progress: {i+1}/{len(all_tickers)}")

        data = fetch_stock_data(ticker, args.api_key)
        if data.get("error"):
            errors.append(f"{ticker}: {data['error']}")
        results.append(data)

        # Rate limiting: ~4 calls per ticker, keep under 300/min
        time.sleep(0.5)

    df = pd.DataFrame(results)
    complete = df["data_complete"].sum()
    print(f"\nFetch complete: {complete}/{len(df)} with full data ({len(errors)} errors)")

    # --- Filter and rank ---
    print(f"\nApplying filters:")
    df_filtered = apply_filters(df, min_market_cap=args.min_market_cap)

    if len(df_filtered) == 0:
        print("ERROR: No stocks passed filters.")
        sys.exit(1)

    print(f"\nCalculating Magic Formula rankings...")
    df_ranked = calculate_magic_formula(df_filtered)

    # --- Output ---
    print(f"\n{'='*80}")
    print(f"TOP {min(args.top, len(df_ranked))} MAGIC FORMULA STOCKS")
    print(f"{'='*80}\n")

    top = df_ranked.head(args.top)
    cur = mkt_cfg["currency_symbol"]
    cap_unit = mkt_cfg["cap_display_unit"]
    cap_suffix = mkt_cfg["cap_display_suffix"]

    for _, row in top.iterrows():
        mc_display = row["market_cap"] / cap_unit if row["market_cap"] else 0
        ey_pct = row["earnings_yield"] * 100 if row["earnings_yield"] else 0
        roc_pct = row["return_on_capital"] * 100 if row["return_on_capital"] else 0
        de = row["debt_equity"] if pd.notna(row["debt_equity"]) else 0
        cr = row["current_ratio"] if pd.notna(row["current_ratio"]) else 0

        print(f"  #{row['mf_rank']:>3}  {row['ticker']:<15}  {row['name'][:25]:<25}  "
              f"EY: {ey_pct:>6.1f}%  ROC: {roc_pct:>6.1f}%  "
              f"D/E: {de:>4.1f}  CR: {cr:>4.1f}  "
              f"MktCap: {cur}{mc_display:>8.1f}{cap_suffix}  {cur}{row['price']:>8.2f}")

    output_cols = ["mf_rank", "ticker", "name", "sector", "industry", "price",
                   "market_cap", "enterprise_value", "ebit",
                   "earnings_yield", "return_on_capital",
                   "ey_rank", "roc_rank",
                   "debt_equity", "current_ratio",
                   "current_assets", "current_liabilities", "net_working_capital",
                   "net_ppe", "total_debt", "total_equity", "years_listed"]
    available_cols = [c for c in output_cols if c in df_ranked.columns]
    df_ranked[available_cols].to_csv(args.output, index=False)
    print(f"\nFull results saved to: {args.output}")

    # --- Summary ---
    print(f"\n--- Summary (Top {min(args.top, len(top))}) ---")
    print(f"  Market:                   {market.upper()} ({mkt_cfg['currency']})")
    print(f"  Median Earnings Yield:    {top['earnings_yield'].median()*100:.1f}%")
    print(f"  Median Return on Capital: {top['return_on_capital'].median()*100:.1f}%")
    print(f"  Median D/E:               {top['debt_equity'].median():.2f}x")
    print(f"  Median Market Cap:        {cur}{top['market_cap'].median()/cap_unit:.1f}{cap_suffix}")
    print(f"\n  Sectors:")
    for sector, count in top["sector"].value_counts().items():
        print(f"    {sector}: {count}")


if __name__ == "__main__":
    main()

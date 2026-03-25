#!/usr/bin/env python3
"""
Magic Formula Screener — yfinance Data Fetcher (Tier 1)

Fetches all 11 required fields for a given stock universe using yfinance.
Outputs a clean CSV ready for ranking.

Usage:
    python fetch_yfinance.py --universe sp500 --output /tmp/mf_raw_data.csv
    python fetch_yfinance.py --universe sp400 --output /tmp/mf_raw_data.csv
    python fetch_yfinance.py --universe nifty500 --output /tmp/mf_raw_data.csv
    python fetch_yfinance.py --universe custom --tickers AAPL,MSFT,GOOG --output /tmp/mf_raw_data.csv
    python fetch_yfinance.py --universe custom --tickers RELIANCE.NS,TCS.NS --output /tmp/mf_raw_data.csv

Requires: pip install yfinance pandas --break-system-packages
"""

import argparse
import sys
import time
import warnings
from io import StringIO

warnings.filterwarnings("ignore")

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("ERROR: Missing dependencies. Run: pip install yfinance pandas --break-system-packages")
    sys.exit(1)


# --- Universe Definitions ---

def _fetch_html(url: str) -> str:
    """Fetch HTML with a browser User-Agent to avoid 403 errors."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")


def get_sp500_tickers():
    """Fetch current S&P 500 tickers from Wikipedia."""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        html = _fetch_html(url)
        tables = pd.read_html(StringIO(html))
        df = tables[0]
        # Column is usually 'Symbol' — clean up any dots (BRK.B -> BRK-B for yfinance)
        tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        sectors = dict(zip(df["Symbol"].str.replace(".", "-", regex=False), df["GICS Sector"]))
        return tickers, sectors
    except Exception as e:
        print(f"WARNING: Could not fetch S&P 500 list from Wikipedia: {e}")
        print("Falling back to a static list would be needed here.")
        return [], {}


def get_sp400_tickers():
    """Fetch S&P 400 MidCap tickers from Wikipedia."""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"
        html = _fetch_html(url)
        tables = pd.read_html(StringIO(html))
        df = tables[0]
        tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        sectors = dict(zip(df["Symbol"].str.replace(".", "-", regex=False), df["GICS Sector"]))
        return tickers, sectors
    except Exception as e:
        print(f"WARNING: Could not fetch S&P 400 list: {e}")
        return [], {}


def get_nifty500_tickers():
    """Fetch Nifty 500 tickers from NSE India.

    Tries multiple sources since NSE's website sometimes blocks automated requests.
    yfinance uses .NS suffix for NSE tickers.
    """
    # Source 1: Wikipedia
    try:
        url = "https://en.wikipedia.org/wiki/NIFTY_500"
        html = _fetch_html(url)
        tables = pd.read_html(StringIO(html))
        # Find the table with ticker/symbol column
        for table in tables:
            cols_lower = [str(c).lower() for c in table.columns]
            for col_name in ["symbol", "ticker", "nse symbol", "nse code"]:
                if col_name in cols_lower:
                    idx = cols_lower.index(col_name)
                    real_col = table.columns[idx]
                    symbols = table[real_col].dropna().astype(str).tolist()
                    # Add .NS suffix for yfinance
                    tickers = [f"{s.strip()}.NS" for s in symbols if s.strip() and s.strip() != "nan"]
                    if len(tickers) > 100:  # Sanity check
                        sectors = {}  # Wikipedia may not have sector info for Nifty
                        print(f"  Fetched {len(tickers)} Nifty 500 tickers from Wikipedia")
                        return tickers, sectors
    except Exception as e:
        print(f"  Wikipedia fetch failed: {e}")

    # Source 2: Try NSE India CSV endpoint
    try:
        import urllib.request
        url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        response = urllib.request.urlopen(req, timeout=15)
        csv_data = response.read().decode("utf-8")
        df = pd.read_csv(StringIO(csv_data))
        # NSE CSV typically has 'Symbol' and 'Industry' columns
        symbol_col = [c for c in df.columns if "symbol" in c.lower()][0]
        symbols = df[symbol_col].dropna().astype(str).tolist()
        tickers = [f"{s.strip()}.NS" for s in symbols if s.strip()]
        sectors = {}
        industry_col = [c for c in df.columns if "industry" in c.lower()]
        if industry_col:
            sectors = dict(zip(tickers, df[industry_col[0]].astype(str).tolist()))
        if len(tickers) > 100:
            print(f"  Fetched {len(tickers)} Nifty 500 tickers from NSE archives")
            return tickers, sectors
    except Exception as e:
        print(f"  NSE archives fetch failed: {e}")

    # Source 3: Hardcoded top 50 Nifty stocks as minimal fallback
    print("  WARNING: Could not fetch full Nifty 500 list. Using Nifty 50 fallback.")
    nifty50 = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
        "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
        "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "HCLTECH.NS",
        "SUNPHARMA.NS", "TITAN.NS", "BAJFINANCE.NS", "WIPRO.NS", "ULTRACEMCO.NS",
        "ONGC.NS", "NTPC.NS", "TATAMOTORS.NS", "POWERGRID.NS", "M&M.NS",
        "JSWSTEEL.NS", "TATASTEEL.NS", "ADANIENT.NS", "ADANIPORTS.NS", "TECHM.NS",
        "INDUSINDBK.NS", "COALINDIA.NS", "HINDALCO.NS", "BAJAJFINSV.NS", "GRASIM.NS",
        "NESTLEIND.NS", "CIPLA.NS", "DRREDDY.NS", "APOLLOHOSP.NS", "DIVISLAB.NS",
        "BPCL.NS", "EICHERMOT.NS", "BRITANNIA.NS", "HEROMOTOCO.NS", "TATACONSUM.NS",
        "SBILIFE.NS", "HDFCLIFE.NS", "BAJAJ-AUTO.NS", "LTIM.NS", "WIPRO.NS",
    ]
    return nifty50, {}


# --- Market Configuration ---

MARKET_CONFIG = {
    "us": {
        "currency": "USD",
        "currency_symbol": "$",
        "min_market_cap": 300_000_000,  # $300M
        "cap_display_unit": 1e9,  # Display in $B
        "cap_display_suffix": "B",
    },
    "india": {
        "currency": "INR",
        "currency_symbol": "₹",
        "min_market_cap": 25_000_000_000,  # ₹2,500 Cr = ₹25B
        "cap_display_unit": 1e7,  # Display in ₹ Crores (1 Cr = 10M)
        "cap_display_suffix": "Cr",
    },
}


def detect_market(universe: str) -> str:
    """Determine which market config to use based on the universe."""
    if universe in ("nifty500",):
        return "india"
    return "us"


# --- Excluded Sectors ---

EXCLUDED_SECTORS = {
    "Financial Services", "Financials",  # yfinance uses "Financial Services"
    "Utilities",
    "Real Estate",  # REITs
}

# More granular exclusions for edge cases
EXCLUDED_INDUSTRIES = {
    "Insurance", "Banks", "Asset Management", "Capital Markets",
    "Diversified Financial Services", "Consumer Finance",
    "Mortgage Finance", "Thrifts & Mortgage Finance",
    "Insurance Brokers", "Reinsurance",
    "Utilities—Regulated Electric", "Utilities—Regulated Gas",
    "Utilities—Diversified", "Utilities—Independent Power Producers",
    "Utilities—Renewable", "Utilities—Regulated Water",
    "REIT", "Real Estate Services",
}


def fetch_stock_data(ticker: str) -> dict:
    """Fetch all 11 required fields for a single ticker."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Get financials from the most recent annual/quarterly data
        financials = stock.financials  # annual income statement
        balance = stock.balance_sheet  # annual balance sheet
        quarterly_financials = stock.quarterly_financials
        quarterly_balance = stock.quarterly_balance_sheet

        # --- Field 1: EBIT (TTM) ---
        ebit = None
        # Try quarterly TTM first (sum of last 4 quarters)
        if quarterly_financials is not None and not quarterly_financials.empty:
            if "EBIT" in quarterly_financials.index:
                last_4 = quarterly_financials.loc["EBIT"].head(4).dropna()
                if len(last_4) >= 4:
                    ebit = last_4.sum()
        # Fall back to annual
        if ebit is None and financials is not None and not financials.empty:
            if "EBIT" in financials.index:
                ebit = financials.loc["EBIT"].dropna().iloc[0] if not financials.loc["EBIT"].dropna().empty else None

        # --- Field 2: Enterprise Value ---
        enterprise_value = info.get("enterpriseValue")

        # --- Fields 3 & 4: Current Assets and Current Liabilities ---
        current_assets = None
        current_liabilities = None

        bs = quarterly_balance if (quarterly_balance is not None and not quarterly_balance.empty) else balance
        if bs is not None and not bs.empty:
            latest = bs.iloc[:, 0]  # most recent period
            current_assets = latest.get("Current Assets") or latest.get("Total Current Assets")
            current_liabilities = latest.get("Current Liabilities") or latest.get("Total Current Liabilities")

        # --- Field 5: Net PP&E ---
        net_ppe = None
        if bs is not None and not bs.empty:
            latest = bs.iloc[:, 0]
            net_ppe = latest.get("Net PPE") or latest.get("Property Plant Equipment Net")

        # --- Fields 6 & 7: Total Debt and Total Equity ---
        total_debt = info.get("totalDebt")
        total_equity = None
        if bs is not None and not bs.empty:
            latest = bs.iloc[:, 0]
            total_equity = latest.get("Stockholders Equity") or latest.get("Total Stockholder Equity")

        # --- Field 8: Market Cap ---
        market_cap = info.get("marketCap")

        # --- Field 9: Sector / Industry ---
        sector = info.get("sector", "Unknown")
        industry = info.get("industry", "Unknown")

        # --- Field 10: Current Price ---
        price = info.get("currentPrice") or info.get("regularMarketPrice")

        # --- Field 11: IPO date proxy (use first trade date or fallback) ---
        first_trade = info.get("firstTradeDateEpochUtc")
        years_listed = None
        if first_trade:
            import datetime
            first_date = datetime.datetime.fromtimestamp(first_trade)
            years_listed = (datetime.datetime.now() - first_date).days / 365.25

        # --- Derived fields ---
        debt_equity = None
        if total_debt is not None and total_equity is not None and total_equity > 0:
            debt_equity = total_debt / total_equity

        current_ratio = None
        if current_assets is not None and current_liabilities is not None and current_liabilities > 0:
            current_ratio = current_assets / current_liabilities

        net_working_capital = None
        if current_assets is not None and current_liabilities is not None:
            net_working_capital = current_assets - current_liabilities

        # Company name
        name = info.get("shortName") or info.get("longName") or ticker

        return {
            "ticker": ticker,
            "name": name,
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
    """Apply enhanced Greenblatt filters."""
    original_count = len(df)

    # Must have complete data
    df = df[df["data_complete"] == True].copy()
    print(f"  After data completeness filter: {len(df)} stocks (removed {original_count - len(df)})")

    # Positive EBIT
    before = len(df)
    df = df[df["ebit"] > 0]
    print(f"  After positive EBIT filter: {len(df)} stocks (removed {before - len(df)})")

    # Market cap minimum
    before = len(df)
    df = df[df["market_cap"] >= min_market_cap]
    print(f"  After market cap >${min_market_cap/1e6:.0f}M filter: {len(df)} stocks (removed {before - len(df)})")

    # Sector exclusions — strict, no exceptions
    before = len(df)
    df = df[~df["sector"].isin(EXCLUDED_SECTORS)]
    print(f"  After sector exclusion filter: {len(df)} stocks (removed {before - len(df)})")

    # Industry-level exclusions (catches edge cases like insurance within other sectors)
    before = len(df)
    df = df[~df["industry"].apply(lambda x: any(excl.lower() in str(x).lower() for excl in EXCLUDED_INDUSTRIES))]
    print(f"  After industry exclusion filter: {len(df)} stocks (removed {before - len(df)})")

    # Debt/Equity < 2.0x
    before = len(df)
    df = df[(df["debt_equity"].isna()) | (df["debt_equity"] < 2.0)]
    print(f"  After D/E <2.0x filter: {len(df)} stocks (removed {before - len(df)})")

    # Current ratio > 1.0x
    before = len(df)
    df = df[(df["current_ratio"].isna()) | (df["current_ratio"] > 1.0)]
    print(f"  After current ratio >1.0x filter: {len(df)} stocks (removed {before - len(df)})")

    # Listed > 1 year
    before = len(df)
    df = df[(df["years_listed"].isna()) | (df["years_listed"] > 1.0)]
    print(f"  After >1 year listed filter: {len(df)} stocks (removed {before - len(df)})")

    return df


def calculate_magic_formula(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate earnings yield, return on capital, and combined MF rank."""
    # Earnings Yield = EBIT / Enterprise Value
    df["earnings_yield"] = df["ebit"] / df["enterprise_value"]

    # Return on Capital = EBIT / (Net Working Capital + Net PPE)
    # Handle edge case where NWC + PPE <= 0 (exclude these)
    tangible_capital = df["net_working_capital"] + df["net_ppe"]
    df["tangible_capital"] = tangible_capital
    df = df[tangible_capital > 0].copy()

    df["return_on_capital"] = df["ebit"] / df["tangible_capital"]

    # Cap ROC at 500% to avoid distortions from tiny capital bases
    df["return_on_capital"] = df["return_on_capital"].clip(upper=5.0)

    # Rank by earnings yield (highest = rank 1)
    df["ey_rank"] = df["earnings_yield"].rank(ascending=False, method="min").astype(int)

    # Rank by return on capital (highest = rank 1)
    df["roc_rank"] = df["return_on_capital"].rank(ascending=False, method="min").astype(int)

    # Combined Magic Formula rank (lowest = best)
    df["mf_rank_raw"] = df["ey_rank"] + df["roc_rank"]
    df = df.sort_values("mf_rank_raw")
    df["mf_rank"] = range(1, len(df) + 1)

    return df


def main():
    parser = argparse.ArgumentParser(description="Magic Formula Stock Screener — yfinance data fetcher")
    parser.add_argument("--universe", choices=["sp500", "sp400", "sp500+sp400", "nifty500", "custom"], default="sp500")
    parser.add_argument("--tickers", type=str, default="", help="Comma-separated tickers for custom universe")
    parser.add_argument("--output", type=str, default="/tmp/mf_raw_data.csv")
    parser.add_argument("--top", type=int, default=30, help="Number of top stocks to highlight")
    parser.add_argument("--min-market-cap", type=float, default=300_000_000, help="Minimum market cap")
    args = parser.parse_args()

    # --- Determine market ---
    market = detect_market(args.universe)
    mkt_cfg = MARKET_CONFIG[market]

    if args.min_market_cap == 300_000_000 and market == "india":
        # Override default to India equivalent if user didn't specify
        args.min_market_cap = mkt_cfg["min_market_cap"]

    print(f"=== Magic Formula Screener — yfinance ===")
    print(f"Market: {market.upper()} | Currency: {mkt_cfg['currency']} | Min Market Cap: {mkt_cfg['currency_symbol']}{args.min_market_cap/mkt_cfg['cap_display_unit']:.0f}{mkt_cfg['cap_display_suffix']}\n")

    # --- Get ticker list ---
    all_tickers = []
    wiki_sectors = {}

    if args.universe in ("sp500", "sp500+sp400"):
        tickers, sectors = get_sp500_tickers()
        all_tickers.extend(tickers)
        wiki_sectors.update(sectors)
        print(f"S&P 500: {len(tickers)} tickers")

    if args.universe in ("sp400", "sp500+sp400"):
        tickers, sectors = get_sp400_tickers()
        all_tickers.extend(tickers)
        wiki_sectors.update(sectors)
        print(f"S&P 400: {len(tickers)} tickers")

    if args.universe == "nifty500":
        tickers, sectors = get_nifty500_tickers()
        all_tickers.extend(tickers)
        wiki_sectors.update(sectors)
        print(f"Nifty 500: {len(tickers)} tickers")

    if args.universe == "custom":
        all_tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
        print(f"Custom universe: {len(all_tickers)} tickers")

    if not all_tickers:
        print("ERROR: No tickers found.")
        sys.exit(1)

    # --- Pre-filter by sector using Wikipedia data (saves API calls) ---
    if wiki_sectors:
        before = len(all_tickers)
        all_tickers = [t for t in all_tickers if wiki_sectors.get(t, "Unknown") not in EXCLUDED_SECTORS]
        print(f"Pre-filtered by sector: {before} -> {len(all_tickers)} tickers (removed {before - len(all_tickers)} Financials/Utilities/REITs)")

    # --- Fetch data (parallelized) ---
    print(f"\nFetching data for {len(all_tickers)} tickers (using parallel workers)...\n")

    results = []
    errors = []

    from concurrent.futures import ThreadPoolExecutor, as_completed
    completed_count = 0
    total = len(all_tickers)

    def fetch_and_track(ticker):
        return fetch_stock_data(ticker)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_and_track, t): t for t in all_tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            completed_count += 1
            if completed_count % 25 == 0 or completed_count == total:
                print(f"  Progress: {completed_count}/{total} tickers fetched")
            data = future.result()
            if data.get("error"):
                errors.append(f"{ticker}: {data['error']}")
            results.append(data)

    # --- Build DataFrame ---
    df = pd.DataFrame(results)
    complete = df["data_complete"].sum()
    print(f"\nData fetch complete: {complete}/{len(df)} tickers with full data ({len(errors)} errors)")

    if errors and len(errors) <= 20:
        print(f"\nErrors:")
        for e in errors:
            print(f"  {e}")

    # --- Apply filters ---
    print(f"\nApplying enhanced filters:")
    df_filtered = apply_filters(df, min_market_cap=args.min_market_cap)

    if len(df_filtered) == 0:
        print("ERROR: No stocks passed all filters. Check data quality.")
        sys.exit(1)

    # --- Calculate Magic Formula ---
    print(f"\nCalculating Magic Formula rankings...")
    df_ranked = calculate_magic_formula(df_filtered)

    print(f"Final ranked universe: {len(df_ranked)} stocks")
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

    # --- Save full results ---
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

    # --- Summary stats ---
    top_n = df_ranked.head(args.top)
    print(f"\n--- Summary Statistics (Top {min(args.top, len(top_n))}) ---")
    print(f"  Market:                   {market.upper()} ({mkt_cfg['currency']})")
    print(f"  Median Earnings Yield:    {top_n['earnings_yield'].median()*100:.1f}%")
    print(f"  Median Return on Capital: {top_n['return_on_capital'].median()*100:.1f}%")
    print(f"  Median D/E:               {top_n['debt_equity'].median():.2f}x")
    print(f"  Median Market Cap:        {cur}{top_n['market_cap'].median()/cap_unit:.1f}{cap_suffix}")
    print(f"\n  Sector Distribution:")
    for sector, count in top_n["sector"].value_counts().items():
        print(f"    {sector}: {count} ({count/len(top_n)*100:.0f}%)")

    # --- Data quality report ---
    fail_rate = 1 - (complete / len(df))
    if fail_rate > 0.2:
        print(f"\n*** WARNING: {fail_rate*100:.0f}% of tickers had missing data. Consider using FMP API as fallback. ***")


if __name__ == "__main__":
    main()

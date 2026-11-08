# Predeclared case-study rules

These rules were fixed before the historical results were computed. They describe an isolated research exercise. They do not change the screener, and they are not a claim that the Magic Formula outperforms.

## What the published app actually does

The app in `scripts/fetch_yfinance.py` and `scripts/fetch_fmp.py` is a current-data screen, not a backtest. It has no filing dates. Characterization tests in `research/tests/test_original_formula.py` and `research/tests/test_fmp_paths.py` lock that code's behavior, including defects.

The historical study does **not** replay Yahoo's `enterpriseValue`. Yahoo does not provide point-in-time financial statements. The study uses an independent implementation in `research/classic_formula.py` and `research/pit_fundamentals.py`.

## Question

At each rebalance date, using only fundamentals whose SEC `filed` date is on or before that date, was MSFT eligible, where did it rank inside today's S&P 500 operating-company list, and how did a predeclared top-30 portfolio's marked total return compare with MSFT buy-and-hold, SPY, and an equal-weight portfolio of the same eligible universe?

## Universe

- Source: Wikipedia "List of S&P 500 companies", the same page `scripts/fetch_yfinance.py` uses, retrieved on the run date.
- Drop GICS sectors `Financials`, `Utilities`, and `Real Estate` (the app's sector prefilter).
- One row per CIK. If two share classes map to one CIK, keep the ticker in the user comparison set if either class is in it (so `GOOG` is kept over `GOOGL`); otherwise keep the first Wikipedia row.
- This is **today's membership**. It embeds survivorship and index-addition bias. Companies that left the index, failed, or were acquired are absent. The study does not apply a delisting return. It is not a CRSP constituent backtest.
- The ten names MSFT, AMZN, GOOG, META, NFLX, XOM, LMT, MU, SNPS, and NKE are a comparison set. They are not the strategy universe. Ranks among those ten names alone are not Magic Formula ranks.

## Calendar

- Formation dates: last SPY trading day on or before 30 September of each year from 2016 through 2025 (ten holdings).
- Each portfolio is held to the next September formation date. The last holding ends on the September 2026 formation date when that price exists.
- A September 2026 cross-section may be reported as a rank snapshot. It is not an extra return period.
- September was chosen because it falls after the typical filing of both December fiscal-year 10-Qs (June period) and June fiscal-year 10-Ks. It was not chosen after looking at returns.
- Single annual cohort only. The retail Magic Formula is often described as staggered monthly purchases held for a year. That design is not tested here.

## Point-in-time fundamentals

- Source: SEC companyfacts, `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`.
- Ticker map: `https://www.sec.gov/files/company_tickers.json`.
- Forms: `10-K`, `10-K/A`, `10-Q`, `10-Q/A` only. For each `(start, end)` keep the fact with the latest `filed` date that is still on or before the rebalance date, then the higher accession number.
- Earnings proxy: US-GAAP `OperatingIncomeLoss`. This is not Yahoo's `EBIT` line. The current-screen audit reports the gap between those two for the live run.
- Trailing twelve months:
  - If the latest report known on the rebalance date is an annual period (about 330–400 days), use that value. Method `annual`.
  - If the latest report is an interim year-to-date figure that starts at the fiscal-year start, `TTM = YTD + prior annual − prior-year YTD`. Method `ytd_bridge`.
  - If the latest fact is a stub quarter, sum non-overlapping quarters in the fiscal year so far and then use the same bridge.
  - The fourth fiscal quarter is not required as its own fact. It enters through the annual total.
- A report whose period end is more than 140 days before the rebalance date is stale. The name is ineligible. Do not substitute a later restatement or a future quarter.
- Balance sheet: latest instant whose `end` and `filed` are on or before the rebalance date, and every balance-sheet item taken from that same `end` date.
  - Net working capital = `AssetsCurrent − LiabilitiesCurrent` (cash stays inside, matching the app).
  - Net fixed assets = `PropertyPlantAndEquipmentNet` when that tag exists on the balance-sheet date. If it does not, use `PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization`. That second tag is the concept filers adopted when finance-lease assets sit inside PP&E. Operating-lease right-of-use assets are still not added. A ten-name parser check, run before any full-universe return was kept, showed the plain PP&E tag stopping while the finance-lease-inclusive tag continued (Alphabet, Amazon, Meta, Micron). Yahoo's current `Net PPE` for MSFT is larger by the operating-lease right-of-use asset; that difference is reported in the current-screen audit.
  - Interest-bearing debt = `LongTermDebt` when that tag is present on the balance-sheet date (it already includes the current portion for MSFT). Otherwise noncurrent plus current portion, or `DebtCurrent` / `LongTermDebtAndCapitalLeaseObligations` when those are the only debt concepts reported. Operating-lease liabilities are not added. If no debt tag is reported on that date, debt is treated as zero and flagged `no_debt_tag_assumed_zero`. The parser check showed this for unlevered filers; dropping them would have removed companies for having no debt. Cash is not filled with zero.
  - Cash = `CashAndCashEquivalentsAtCarryingValue`, then restricted-cash-inclusive cash, then `Cash`. Missing cash makes the name ineligible.
  - Short-term investments and operating-lease liabilities are stored and not used in the primary enterprise value.
- Enterprise value = split-adjusted close × split-adjusted shares + interest-bearing debt − cash.
- Shares: latest `dei:EntityCommonStockSharesOutstanding` (fallback `CommonStockSharesOutstanding`) with `filed` and `end` on or before the rebalance date, multiplied by Yahoo split ratios dated after the share observation. If neither instant tag exists, use `WeightedAverageNumberOfSharesOutstandingBasic` for the latest period. That average is not the share count on the rebalance date. A first full pass, before these published figures, showed 15 filers with no instant share tag, including Meta. Prices used for enterprise value are split-adjusted closes (`Close` with `auto_adjust=False`), not dividend-adjusted closes.
- Total returns use `Adj Close`, which includes dividends and splits. Cash yield is zero. No taxes.

## Eligibility and ranking

Two variants, both reported. Neither is selected after seeing results.

**Classic**

- EBIT > 0, enterprise value > 0, tangible capital > 0, market cap ≥ $300 million.
- No debt/equity filter, no current-ratio filter, no return-on-capital cap, no years-listed filter.
- Earnings yield = EBIT / enterprise value.
- Return on capital = EBIT / (net working capital + net fixed assets).
- Rank 1 is best (highest). Ties use `method=min`.
- Combined score = earnings-yield rank + return-on-capital rank. Lower is better.
- Tie-break, which the app does **not** define: higher earnings yield, then ticker. Sort is stable (`mergesort`).
- Non-positive enterprise value is dropped. The app does not drop it; a zero enterprise value becomes an infinite yield and can take earnings-yield rank 1. That app behavior is covered by unit tests and is not reproduced in the history.

**Repo rules**

- Same data and the same non-positive enterprise-value guard.
- Also require the app's extra filters: debt/equity < 2.0 when the ratio exists, current ratio > 1.0 when the ratio exists. A missing ratio passes, which is what the app does.
- Cap return on capital at 5.0 (500%) before ranking, which is what the app does.
- No years-listed filter. On the live Yahoo pull, `firstTradeDateEpochUtc` was empty, so the app's listed-more-than-one-year rule did not remove anyone. There is no point-in-time equivalent in this study.

Primary portfolio: top 30 by combined score, equal weight. If fewer than 30 names are eligible, equal-weight those names. If none are eligible, that year earns the cash return of zero.

## Costs and benchmarks

- Gross series: no transaction cost.
- Net series: 10 basis points times the sum of absolute weight changes at each rebalance (entry from cash counts as turnover of 1). No exit cost on the final mark. No spread model beyond that.
- Benchmarks on the same dates: MSFT total return, SPY total return, and the annually rebalanced equal-weight portfolio of every classic-eligible name.
- A name missing a price on either endpoint of a holding period is dropped for that period and the remaining weights are renormalized. The count is reported. This can bias results upward if the missing names were failures. It is not a delisting model.

## What will not be claimed

Beating SPY or MSFT in this file, if it happens, is not evidence the formula works. Losing is not a full proof the formula fails outside this biased universe. No variant other than the two above will be promoted because it looks better.

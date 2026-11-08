# Magic Formula screener audit

Verdict: the app runs, and its ranking arithmetic matches the ratios it prints. It is not a validated Magic Formula backtest, and it is not cleared for reuse. On 8 November 2026 the live S&P 500 screen ranked MSFT 110 of 226. In a separate point-in-time case study, MSFT was eligible at every September rebalance from 2016 through 2026 and its best classic rank was 128 of 242. Neither result is a buy signal. The case study does not show the ranking beating an equal-weight portfolio of the same eligible survivors, and it is not evidence the formula outperforms.

The screener code in `scripts/` was not changed. Tests in `research/tests/test_original_formula.py` and `research/tests/test_fmp_paths.py` lock that code, including the defects below. `research/classic_formula.py` is an independent implementation used only by the case study.

## License and reuse

GitHub reports `license: null` for both `orestiusp/magic-formula-screener` and upstream `haga8905/magic-formula-screener`. There is no `LICENSE` file. The README's "MIT" line is not a license grant. Public code is not a blanket permission to copy it into Atlas.

Dependencies have their own licenses (Next.js 16.2.1 MIT, `csv-parse` 6.2.1 MIT, `xlsx` 0.18.5 Apache-2.0). The SheetJS 0.18.5 package on npm has a published prototype-pollution advisory and no fixed release on the public npm registry. That is a dependency risk, separate from the formula.

Joel Greenblatt's book is copyrighted. The earnings-yield and return-on-capital definitions are a published method and can be reimplemented. That is not permission to copy this repository's scripts, UI, or text.

Recommendation: do not vendor this repo and do not open an upstream pull request. If Atlas later wants the screen, write an independent calculator and treat it as an optional list, not an order rule.

## What was run

Retrieval date for every live pull below: 8 November 2026 (UTC). Python 3.12. Node 22.23.4. yfinance 1.8.0. No FMP key was created and the FMP script was not called against the network.

```bash
python3 -m venv .venv
.venv/bin/pip install -r research/requirements.txt
.venv/bin/python -m pytest research/tests -q          # 24 passed
npm ci && npm run lint                                 # fails: 13 errors, 1 warning
npm run build                                          # succeeds, Next.js 16.2.1
.venv/bin/python research/run_current_screen.py
.venv/bin/python research/run_msft_study.py
```

There was no original test script. `package.json` names the project `temp-scaffold` and marks it `private`. `npm run lint` fails in `ResultsTable.tsx` (component created during render) and `useScreenerJob.ts`. The production build still completes.

Sources:

- Constituents: https://en.wikipedia.org/wiki/List_of_S%26P_500_companies
- SEC ticker map: https://www.sec.gov/files/company_tickers.json (last-modified header on retrieval: 4 November 2026)
- SEC companyfacts: https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json
- Prices and the live screen: Yahoo Finance through yfinance. Close, with `auto_adjust=False`, for enterprise value. Adj Close for total return.

## Live screen

Command, unmodified `scripts/fetch_yfinance.py`:

```bash
python scripts/fetch_yfinance.py --universe sp500 --top 30 --min-market-cap 300000000
python scripts/fetch_yfinance.py --universe custom \
  --tickers MSFT,AMZN,GOOG,META,NFLX,XOM,LMT,MU,SNPS,NKE \
  --top 10 --min-market-cap 300000000
```

Wikipedia returned 503 constituents. The sector prefilter left 366. Yahoo returned complete data for 353. Ten tickers at the end of the alphabet were rate-limited (WMB, WSM, WDAY, WYNN, WDC, ZBRA, YUM, XYL, ZBH, ZTS). Filters then left 226 ranked names. Output: `research/artifacts/current_sp500.csv`. Log: `research/artifacts/current_sp500.log`.

Recomputed from the saved columns, max absolute error was 0 for both `EBIT / enterprise value` and `min(EBIT / (net working capital + net PP&E), 5)`. The printed ratios are the code's ratios.

MSFT in that file: rank 110 of 226, earnings yield 4.509%, return on capital 43.972%, earnings-yield rank 122, return-on-capital rank 91, combined score 213. It would not be in the default top 30.

Other comparison names in the same file:

| Ticker | Result |
| --- | --- |
| MU | rank 5, yield 13.44%, ROC 78.63% |
| NFLX | rank 7, yield 6.88%, ROC printed 500% (raw 532.93%, cap binds) |
| GOOG | rank 24, yield 8.57%, ROC 45.91% |
| GOOGL | rank 25, same business again |
| XOM | rank 103 |
| MSFT | rank 110 |
| NKE | rank 137 |
| META | rank 148 |
| SNPS | rank 155 |
| AMZN | removed, current ratio 0.9888 |
| LMT | removed, debt/equity 2.037 |

The ten-name run is only a code check. Rank 7 of 8 for MSFT in that file is not a market rank. Inside those eight, SNPS and XOM tied on combined score 11, and META, MSFT, and NKE tied on 12. The app assigns consecutive `mf_rank` values after an unstable sort, so ties are ordered by accident. Across the 226-name file, 45 combined scores were tied and those ties covered 103 names.

`years_listed` was empty for all 226 names, and the "> 1 year listed" filter removed zero names. Yahoo returned `firstTradeDateEpochUtc: null` for MSFT. A missing ratio or a missing listing age passes. Negative book equity also fails to produce a debt/equity ratio, and then passes. The UI says those filters remove stocks.

The header printed "Min Market Cap: $0B" because $300 million is formatted in billions with zero decimals. The filter itself used $300 million. The log says 40 names failed debt/equity and 71 failed current ratio. Three more names were dropped because tangible capital was not positive. One name survived the Wikipedia sector prefilter and failed the Yahoo sector check.

Dual share classes are both ranked: GOOG and GOOGL, FOX and FOXA, NWS and NWSA.

No ranked name had enterprise value at or below zero in this pull (minimum about $9.15 billion). The code still does not guard that case. A zero enterprise value becomes an infinite earnings yield and takes earnings-yield rank 1. `research/tests/test_original_formula.py` demonstrates it. Negative enterprise value is kept and produces a negative yield.

## Formula against the code, and against the filing

For a passed row the app does:

- Earnings yield = Yahoo `EBIT` / Yahoo `enterpriseValue`
- Return on capital = Yahoo `EBIT` / (current assets − current liabilities + Yahoo `Net PPE`), then capped at 5.0
- Ranks use `method=min` (rank 1 is best). Combined score is the sum. Lower is better.

That is the shape of Greenblatt's two ratios. The inputs are not the book's inputs.

MSFT on the 8 November pull, quarterly statements through 2026-09-30, columns newest-first for all ten comparison names:

- Trailing four-quarter Yahoo EBIT = 46.823 + 44.886 + 40.118 + 48.982 = $180.809 billion
- Trailing four-quarter Yahoo operating income = $163.191 billion
- Enterprise value $4,009.835 billion; market cap $3,940.413 billion
- Enterprise value equals market cap + `info.totalDebt` − `info.totalCash` within $286,720
- `info.totalDebt` is $133.931 billion. The same payload's balance-sheet "Total Debt" is $57.200 billion
- SEC long-term debt at 2026-09-30, filed 2026-10-28, is $35.481 billion. Noncurrent operating-lease liability is $21.719 billion. Those two sum to the balance-sheet total, not to $133.931 billion
- Net working capital $34.169 billion matches SEC current assets minus current liabilities on that date
- Yahoo net PP&E $377.022 billion is SEC `PropertyPlantAndEquipmentNet` $346.844 billion plus the operating-lease right-of-use asset $30.178 billion
- Debt/equity in the screen is 0.285 using the $133.931 billion debt figure

Alphabet shows the EBIT label problem more sharply. Yahoo's trailing four-quarter EBIT is $290.713 billion and operating income is $156.976 billion. In the quarter ended 2026-06-30, Yahoo EBIT is $140.031 billion and operating income is $40.770 billion. Other income/expense that quarter is $97.831 billion. The screen treats the larger number as EBIT, so investment gains flow into earnings yield. Nike's two lines matched. Microsoft's did not.

The FMP fallback, untested against the network, uses `operatingIncome or ebitda`. A missing or zero operating income is replaced by EBITDA. A zero current-liability balance is treated as missing working capital because the code uses Python truthiness. Those paths are unit-tested with mocks.

Return on capital is capped at 500% before ranking. In this S&P pull only NFLX was capped. Everyone above the cap shares the best return-on-capital rank. The cap is not part of the published formula.

Debt/equity below 2, current ratio above 1, and a one-year listing rule are also extra. The published screen is closer to: positive EBIT, drop financials and utilities, rank the two ratios, buy 20 to 30 names. This app can drop a company the formula would rank, and it can keep a company whose debt or liquidity figure never arrived.

The code assumes the first statement column is the newest and does not sort. On this pull, all ten comparison names were newest-first. A reversed frame would silently sum the wrong quarters.

Quarterly EBIT is used when four quarters exist; otherwise the latest annual figure is used. Enterprise value is a live quote. The balance sheet is the latest quarter. Nothing records the period end or the filing date.

## Historical case study

Rules were written in `research/PROTOCOL.md` before the full-universe returns. Two parser fixes were made after counting gaps and before the published figures: a second PP&E tag when the plain net-PP&E tag stops, and weighted-average basic shares when no instant share count exists (15 filers, including Meta). Debt reported under no debt tag is treated as zero and counted below. The published wealth figures are the run that finished at 2026-11-08T06:48:40Z.

This is one September cohort inside today's S&P 500, after dropping GICS Financials, Utilities, and Real Estate and keeping one share class per CIK (GOOG kept over GOOGL). It is today's membership. Companies that left the index are absent. There is no delisting return. About 71 to 81 percent of the 363 names had a usable point-in-time record in a given year. The largest gap is filers with no US-GAAP `OperatingIncomeLoss` (608 name-years), which includes Nike in every year and the current Exxon Mobil ticker. After the weighted-average share fallback, 25 name-years still had no share count. SEC's ticker map points XOM at CIK 0002115436, ExxonMobil Holdings Corporation, whose companyfacts file has essentially no operating history. The predecessor filer was not substituted.

Earnings are `OperatingIncomeLoss` known by the SEC `filed` date. On 30 September the latest Microsoft report is the 10-K filed in late July, not the 10-Q filed in late October. Enterprise value is split-adjusted close times split-adjusted shares, plus interest-bearing debt, minus cash. A check that had to pass before results were kept: Microsoft on 30 September 2021, price $281.92, 7.515 billion shares, market cap $2.119 trillion. Amazon on the same date used a 20-for-1 split factor on 506.4 million reported shares and a market cap of $1.664 trillion.

Of the eligible rows, 12.5 percent had debt set to zero because no debt tag was on that balance-sheet date, and 10.4 percent used the finance-lease-inclusive PP&E tag. Cash was not invented. Operating-lease liabilities were not added to debt.

Primary portfolio: top 30, equal weight, held to the next September, cash yield zero. Costs: 0 and 10 basis points times the sum of absolute weight changes, including the initial buy. No final liquidation cost. Benchmarks on the same dates: MSFT total return, SPY total return, and an equal-weight rebalance of every classic-eligible name (about 227 to 250 names). Drawdowns below are changes between September marks. They do not measure the 2022 intra-year decline.

Growth of $1 from 30 September 2016 to 30 September 2026 (3,652 days):

| Series | Ending wealth | CAGR | September-mark drawdown |
| --- | ---: | ---: | ---: |
| MSFT total return | 10.028 | 25.93% | -16.70% |
| MSFT, 10 bps entry | 10.018 | 25.92% | -16.70% |
| Eligible universe, equal weight | 5.305 | 18.16% | -11.99% |
| Eligible universe, 10 bps | 5.284 | 18.12% | -12.02% |
| Repo-rules top 30 | 4.553 | 16.37% | -10.27% |
| Repo-rules top 30, 10 bps | 4.501 | 16.24% | -10.38% |
| SPY total return | 4.129 | 15.24% | -15.51% |
| SPY, 10 bps entry | 4.124 | 15.22% | -15.51% |
| Classic top 30 | 4.082 | 15.11% | -1.90% |
| Classic top 30, 10 bps | 4.038 | 14.98% | -2.01% |

Classic top 30 finished behind SPY. Repo-rules top 30, which adds the app's debt, liquidity, and 500% cap on top of the filing data, finished ahead of SPY and behind the equal-weight eligible universe. Both finished far behind MSFT buy-and-hold. From September 2021 to September 2022, SPY's total return was -15.5% and MSFT's was -16.7%. The classic top 30's September-to-September return that year was -1.9%. That is one annual mark, not a measured bear-market path. No price was missing on a formation date. Files: `research/artifacts/return_summary.csv`, `cumulative_wealth.csv`, `cumulative_wealth.png`.

MSFT classic rank (1 is best), earnings yield, and return on capital. The yield is SEC operating income over the constructed enterprise value, so it will not match the live Yahoo screen:

| As of | Rank | Universe | Yield | ROC | Repo-rules rank | Repo universe |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2016-09-30 | 178 | 227 | 4.18% | 20.5% | 141 | 180 |
| 2017-09-29 | 199 | 234 | 3.47% | 18.8% | 156 | 182 |
| 2018-09-28 | 185 | 236 | 3.72% | 24.9% | 149 | 185 |
| 2019-09-30 | 186 | 238 | 3.83% | 30.1% | 138 | 176 |
| 2020-09-30 | 144 | 228 | 3.23% | 34.4% | 103 | 176 |
| 2021-09-30 | 148 | 239 | 3.23% | 45.0% | 109 | 187 |
| 2022-09-30 | 140 | 249 | 4.70% | 56.0% | 92 | 186 |
| 2023-09-29 | 152 | 241 | 3.75% | 50.4% | 104 | 180 |
| 2024-09-30 | 128 | 242 | 3.39% | 64.4% | 73 | 177 |
| 2025-09-30 | 162 | 250 | 3.33% | 50.4% | 109 | 184 |
| 2026-09-30 | 150 | 248 | 4.06% | 44.1% | 109 | 189 |

MSFT was never in the top 30. Among the comparison names, the only top-30 appearances were LMT in four classic years (2019, 2020, 2021, 2023) and three repo-rules years, MU in 2018, and NFLX in the repo-rules lists for 2022 and 2026. On 30 September 2026, classic ranks were NFLX 41, LMT 46, MU 85, MSFT 150, META 162, GOOG 199, AMZN 212, SNPS 220. Nike and XOM had no `OperatingIncomeLoss`. LMT failed the repo-rules debt/equity screen that year, which matches the live Yahoo screen. Meta's market cap uses weighted-average basic shares. The September 2022 figure was $367 billion at $135.68, in line with the split-adjusted price history. Plot: `research/artifacts/msft_rank.png`.

## Integration

Use this as research, not as an Atlas feed.

- The live screen can produce a list. MSFT is on it and is not near the top. A top-30 list is a research queue.
- Do not auto-buy from it. The app's extra filters, the 500% cap, missing-data passes, Yahoo's EBIT label, and Yahoo's debt figure all move the list.
- Do not port the Python or the Next.js app. Reimplement the two ratios if a screen is still wanted, store the period end and the filing date, refuse non-positive enterprise value and non-positive tangible capital, and do not cap return on capital unless that choice is shown separately.
- Do not describe a future Atlas result as a Magic Formula backtest unless the universe includes companies that later left the index, fundamentals are limited to what was filed, and the comparison includes the equal-weight universe and a total-return market index. This file does the last two and does not do the first.

## What remains unproven

A fair test would need historical index membership, delisting returns, and a monthly staggered one-year hold. This study has none of those. It also does not replay Yahoo's `enterpriseValue` through time, because that field has no filing date. Nike never reports the operating-income tag used here. The current XOM CIK has no usable history. Twelve percent of eligible rows were given zero debt because the tag was absent. September-to-September drawdowns are not daily risk. One window, chosen in advance, in which classic top 30 finished slightly behind SPY and both variants finished behind the equal-weight survivor universe, is not a proof that the formula fails in a CRSP study. It is also not a proof that it works. The book's historical results were not re-estimated.

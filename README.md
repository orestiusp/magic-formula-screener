# Magic Formula Stock Screener

A full-stack stock screener implementing Joel Greenblatt's **Magic Formula** from *The Little Book That Beats the Market*. It ranks stocks by combining **earnings yield** and **return on capital** to find good companies at cheap prices.

![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)
![TypeScript](https://img.shields.io/badge/TypeScript-5-blue?logo=typescript)
![Python](https://img.shields.io/badge/Python-3-yellow?logo=python)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-4-38bdf8?logo=tailwindcss)

## Features

- **Multiple stock universes** — S&P 500, S&P 400 MidCap, S&P 500 + 400 combined, Nifty 500 (India), or a custom ticker list
- **Magic Formula ranking** — Ranks stocks by Earnings Yield + Return on Capital, surfaces the top N
- **Built-in quality filters** — Excludes financials/utilities/REITs, enforces positive EBIT, D/E < 2x, current ratio > 1x, and minimum market cap
- **Configurable parameters** — Adjust top N results (1–100) and minimum market cap
- **Dual data sources** — Primary: yfinance (free, no key needed) with automatic fallback to Financial Modeling Prep API
- **Rich results view** — Sortable table with metric tooltips, sector pie chart, summary statistics, and Greenblatt's strategy guide
- **Export** — Download results as CSV or XLSX
- **Multi-market support** — USD/billions for US stocks, INR/crores for Indian stocks

## How It Works

The Magic Formula ranks every stock on two metrics and combines the ranks:

| Metric | Formula | What It Measures |
|--------|---------|------------------|
| **Earnings Yield** | EBIT / Enterprise Value | How cheap the stock is |
| **Return on Capital** | EBIT / (Net Working Capital + Net PPE) | How efficient the business is |
| **Magic Formula Rank** | EY Rank + ROC Rank | Combined — lower is better |

Stocks that are both cheap **and** high-quality rise to the top.

## Getting Started

### Prerequisites

- **Node.js** 18+
- **Python** 3.9+
- Python packages: `yfinance`, `pandas`

### Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/magic-formula-screener.git
cd magic-formula-screener

# Install Node dependencies
npm install

# Install Python dependencies
pip install yfinance pandas
```

### Optional: FMP API Key (fallback data source)

If yfinance fails, the app can fall back to [Financial Modeling Prep](https://financialmodelingprep.com/). To enable this:

```bash
# Create .env.local in the project root
echo "FMP_API_KEY=your_key_here" > .env.local
```

### Run

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
├── src/
│   ├── app/
│   │   ├── page.tsx                 # Landing page
│   │   ├── results/page.tsx         # Results display
│   │   └── api/screener/
│   │       ├── run/route.ts         # Start a screening job
│   │       ├── status/route.ts      # Poll job progress
│   │       └── results/route.ts     # Fetch completed results
│   ├── components/
│   │   ├── ScreenerForm.tsx         # Main form orchestrator
│   │   ├── UniverseSelector.tsx     # Market/universe picker
│   │   ├── FilterPanel.tsx          # Top N & min market cap
│   │   ├── ResultsTable.tsx         # Sortable results table
│   │   ├── SummaryStats.tsx         # Median metrics cards
│   │   ├── SectorChart.tsx          # Sector distribution pie chart
│   │   └── ExportButton.tsx         # CSV/XLSX export
│   ├── lib/
│   │   ├── screener.ts              # Job execution & subprocess mgmt
│   │   ├── job-store.ts             # In-memory job state (1hr TTL)
│   │   ├── types.ts                 # TypeScript interfaces
│   │   ├── constants.ts             # Market configs & universe options
│   │   └── csv-parser.ts            # CSV result parsing
│   └── hooks/
│       └── useScreenerJob.ts        # React hook for job polling
├── scripts/
│   ├── fetch_yfinance.py            # Primary data fetcher (yfinance)
│   └── fetch_fmp.py                 # Fallback data fetcher (FMP API)
└── package.json
```

## Tech Stack

- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS 4, Recharts
- **Backend**: Next.js API routes spawning Python subprocesses
- **Data Sources**: yfinance (primary), Financial Modeling Prep (fallback)

## Filters Applied

The screener automatically excludes stocks that don't meet these criteria:

| Filter | Threshold |
|--------|-----------|
| EBIT | Must be positive |
| Debt-to-Equity | < 2.0x |
| Current Ratio | > 1.0x |
| Years Listed | > 1 year |
| Min Market Cap | Configurable (default: $300M US / ₹2,500 Cr India) |
| Excluded Sectors | Financials, Utilities, Real Estate |

## Disclaimer

This tool is for **educational and research purposes only**. It is not financial advice. Always do your own due diligence before making investment decisions. Data is sourced from third-party APIs and may be delayed or incomplete.

## License

MIT

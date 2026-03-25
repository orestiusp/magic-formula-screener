import { readFileSync } from "fs";
import { parse } from "csv-parse/sync";
import { StockResult, SummaryStats, Market } from "./types";

export function parseScreenerCSV(filePath: string): StockResult[] {
  const content = readFileSync(filePath, "utf-8");
  const records = parse(content, {
    columns: true,
    skip_empty_lines: true,
    cast: true,
    cast_date: false,
  }) as Record<string, unknown>[];

  return records.map((row) => ({
    mf_rank: Number(row.mf_rank) || 0,
    ticker: String(row.ticker || ""),
    name: String(row.name || ""),
    sector: String(row.sector || "Unknown"),
    industry: String(row.industry || "Unknown"),
    price: Number(row.price) || 0,
    market_cap: Number(row.market_cap) || 0,
    enterprise_value: Number(row.enterprise_value) || 0,
    ebit: Number(row.ebit) || 0,
    earnings_yield: Number(row.earnings_yield) || 0,
    return_on_capital: Number(row.return_on_capital) || 0,
    ey_rank: Number(row.ey_rank) || 0,
    roc_rank: Number(row.roc_rank) || 0,
    debt_equity: row.debt_equity != null && row.debt_equity !== "" ? Number(row.debt_equity) : null,
    current_ratio: row.current_ratio != null && row.current_ratio !== "" ? Number(row.current_ratio) : null,
    current_assets: Number(row.current_assets) || 0,
    current_liabilities: Number(row.current_liabilities) || 0,
    net_working_capital: Number(row.net_working_capital) || 0,
    net_ppe: Number(row.net_ppe) || 0,
    total_debt: Number(row.total_debt) || 0,
    total_equity: Number(row.total_equity) || 0,
    years_listed: row.years_listed != null && row.years_listed !== "" ? Number(row.years_listed) : null,
  }));
}

function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

export function computeSummary(stocks: StockResult[], totalScreened: number): SummaryStats {
  const eyValues = stocks.map((s) => s.earnings_yield).filter((v) => v > 0);
  const rocValues = stocks.map((s) => s.return_on_capital).filter((v) => v > 0);
  const deValues = stocks.map((s) => s.debt_equity).filter((v): v is number => v != null);
  const capValues = stocks.map((s) => s.market_cap).filter((v) => v > 0);

  const sectorDistribution: Record<string, number> = {};
  for (const stock of stocks) {
    sectorDistribution[stock.sector] = (sectorDistribution[stock.sector] || 0) + 1;
  }

  return {
    totalScreened,
    totalPassed: stocks.length,
    medianEarningsYield: median(eyValues),
    medianReturnOnCapital: median(rocValues),
    medianDebtEquity: median(deValues),
    medianMarketCap: median(capValues),
    sectorDistribution,
  };
}

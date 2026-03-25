export type Universe = "sp500" | "sp400" | "sp500+sp400" | "nifty500" | "custom";
export type Market = "us" | "india";

export interface ScreenerConfig {
  universe: Universe;
  customTickers?: string;
  topN: number;
  minMarketCap?: number;
}

export interface StockResult {
  mf_rank: number;
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  price: number;
  market_cap: number;
  enterprise_value: number;
  ebit: number;
  earnings_yield: number;
  return_on_capital: number;
  ey_rank: number;
  roc_rank: number;
  debt_equity: number | null;
  current_ratio: number | null;
  current_assets: number;
  current_liabilities: number;
  net_working_capital: number;
  net_ppe: number;
  total_debt: number;
  total_equity: number;
  years_listed: number | null;
}

export interface JobState {
  jobId: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: string;
  outputPath: string;
  error?: string;
  createdAt: number;
}

export interface JobStatusResponse {
  jobId: string;
  status: JobState["status"];
  progress: string;
  error?: string;
}

export interface SummaryStats {
  totalScreened: number;
  totalPassed: number;
  medianEarningsYield: number;
  medianReturnOnCapital: number;
  medianDebtEquity: number;
  medianMarketCap: number;
  sectorDistribution: Record<string, number>;
}

export interface ScreenerResponse {
  stocks: StockResult[];
  summary: SummaryStats;
  market: Market;
}

export interface MarketConfig {
  currency: string;
  currencySymbol: string;
  minMarketCap: number;
  capDisplayUnit: number;
  capDisplaySuffix: string;
}

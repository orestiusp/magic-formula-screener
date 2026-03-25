"use client";

import { StockResult } from "@/lib/types";

interface Props {
  stocks: StockResult[];
  filename?: string;
}

export function ExportButton({ stocks, filename = "magic-formula-results" }: Props) {
  function exportCSV() {
    const headers = [
      "MF Rank", "Ticker", "Company", "Sector", "Industry", "Price",
      "Market Cap", "Enterprise Value", "EBIT", "Earnings Yield",
      "Return on Capital", "EY Rank", "ROC Rank", "D/E", "Current Ratio",
    ];

    const rows = stocks.map((s) => [
      s.mf_rank, s.ticker, `"${s.name}"`, `"${s.sector}"`, `"${s.industry}"`,
      s.price, s.market_cap, s.enterprise_value, s.ebit,
      (s.earnings_yield * 100).toFixed(2) + "%",
      (s.return_on_capital * 100).toFixed(2) + "%",
      s.ey_rank, s.roc_rank,
      s.debt_equity?.toFixed(2) ?? "N/A",
      s.current_ratio?.toFixed(2) ?? "N/A",
    ]);

    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <button
      onClick={exportCSV}
      className="px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium transition-colors"
    >
      Export CSV
    </button>
  );
}

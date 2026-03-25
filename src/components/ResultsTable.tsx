"use client";

import { useState } from "react";
import { StockResult, Market } from "@/lib/types";
import { MARKET_CONFIGS } from "@/lib/constants";

type SortKey = keyof StockResult;

interface Props {
  stocks: StockResult[];
  market: Market;
}

export function ResultsTable({ stocks, market }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("mf_rank");
  const [sortAsc, setSortAsc] = useState(true);

  const config = MARKET_CONFIGS[market];

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(true);
    }
  }

  const sorted = [...stocks].sort((a, b) => {
    const aVal = a[sortKey];
    const bVal = b[sortKey];
    if (aVal == null && bVal == null) return 0;
    if (aVal == null) return 1;
    if (bVal == null) return -1;
    if (typeof aVal === "string" && typeof bVal === "string") {
      return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    }
    return sortAsc ? Number(aVal) - Number(bVal) : Number(bVal) - Number(aVal);
  });

  function formatCap(value: number): string {
    return `${config.currencySymbol}${(value / config.capDisplayUnit).toFixed(1)}${config.capDisplaySuffix}`;
  }

  function formatPrice(value: number): string {
    return `${config.currencySymbol}${value.toFixed(2)}`;
  }

  function formatPct(value: number): string {
    return `${(value * 100).toFixed(1)}%`;
  }

  function formatRatio(value: number | null): string {
    return value != null ? value.toFixed(2) : "N/A";
  }

  const SortHeader = ({ label, field, tooltip }: { label: string; field: SortKey; tooltip: string }) => (
    <th
      className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-gray-700 dark:hover:text-gray-200 whitespace-nowrap relative group"
      onClick={() => handleSort(field)}
    >
      <span className="border-b border-dotted border-gray-400 dark:border-gray-500">
        {label}
      </span>
      {sortKey === field && (
        <span className="ml-1">{sortAsc ? "\u25B2" : "\u25BC"}</span>
      )}
      <div className="absolute left-0 top-full mt-1 z-50 hidden group-hover:block w-64 px-3 py-2 text-xs font-normal normal-case tracking-normal text-white bg-gray-900 dark:bg-gray-700 rounded-lg shadow-lg pointer-events-none">
        {tooltip}
      </div>
    </th>
  );

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            <SortHeader label="Rank" field="mf_rank" tooltip="Magic Formula combined rank (EY Rank + ROC Rank). Lower is better." />
            <SortHeader label="Ticker" field="ticker" tooltip="Stock ticker symbol" />
            <SortHeader label="Company" field="name" tooltip="Company name" />
            <SortHeader label="Sector" field="sector" tooltip="GICS sector classification. Financials, Utilities, and REITs are excluded." />
            <SortHeader label="Price" field="price" tooltip="Current stock price" />
            <SortHeader label="Mkt Cap" field="market_cap" tooltip="Market capitalization — total market value of all outstanding shares" />
            <SortHeader label="EY Rank" field="ey_rank" tooltip="Earnings Yield rank among all screened stocks. Rank 1 = highest (cheapest)." />
            <SortHeader label="ROC Rank" field="roc_rank" tooltip="Return on Capital rank among all screened stocks. Rank 1 = highest (most efficient)." />
            <SortHeader label="Earnings Yield" field="earnings_yield" tooltip="EBIT / Enterprise Value — measures how cheap the stock is. Higher = better value." />
            <SortHeader label="Return on Capital" field="return_on_capital" tooltip="EBIT / (Net Working Capital + Net Fixed Assets) — measures capital efficiency. Higher = better business." />
            <SortHeader label="D/E" field="debt_equity" tooltip="Debt-to-Equity ratio — Total Debt / Total Equity. Stocks above 2.0x are filtered out." />
            <SortHeader label="Current Ratio" field="current_ratio" tooltip="Current Assets / Current Liabilities — measures short-term liquidity. Stocks below 1.0x are filtered out." />
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
          {sorted.map((stock) => (
            <tr key={stock.ticker} className="hover:bg-gray-50 dark:hover:bg-gray-800">
              <td className="px-3 py-2 text-sm font-bold text-blue-600 dark:text-blue-400">
                #{stock.mf_rank}
              </td>
              <td className="px-3 py-2 text-sm font-mono font-medium">
                {stock.ticker}
              </td>
              <td className="px-3 py-2 text-sm max-w-[200px] truncate" title={stock.name}>
                {stock.name}
              </td>
              <td className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
                {stock.sector}
              </td>
              <td className="px-3 py-2 text-sm text-right font-mono">
                {formatPrice(stock.price)}
              </td>
              <td className="px-3 py-2 text-sm text-right font-mono">
                {formatCap(stock.market_cap)}
              </td>
              <td className="px-3 py-2 text-sm text-center">{stock.ey_rank}</td>
              <td className="px-3 py-2 text-sm text-center">{stock.roc_rank}</td>
              <td className="px-3 py-2 text-sm text-right font-mono text-green-600 dark:text-green-400">
                {formatPct(stock.earnings_yield)}
              </td>
              <td className="px-3 py-2 text-sm text-right font-mono text-green-600 dark:text-green-400">
                {formatPct(stock.return_on_capital)}
              </td>
              <td className="px-3 py-2 text-sm text-right font-mono">
                {formatRatio(stock.debt_equity)}
              </td>
              <td className="px-3 py-2 text-sm text-right font-mono">
                {formatRatio(stock.current_ratio)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

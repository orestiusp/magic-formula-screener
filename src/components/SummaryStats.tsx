"use client";

import { SummaryStats as SummaryStatsType, Market } from "@/lib/types";
import { MARKET_CONFIGS } from "@/lib/constants";

interface Props {
  summary: SummaryStatsType;
  market: Market;
}

export function SummaryStats({ summary, market }: Props) {
  const config = MARKET_CONFIGS[market];

  const stats = [
    {
      label: "Stocks Passed",
      value: `${summary.totalPassed}`,
    },
    {
      label: "Median Earnings Yield",
      value: `${(summary.medianEarningsYield * 100).toFixed(1)}%`,
    },
    {
      label: "Median Return on Capital",
      value: `${(summary.medianReturnOnCapital * 100).toFixed(1)}%`,
    },
    {
      label: "Median D/E",
      value: `${summary.medianDebtEquity.toFixed(2)}x`,
    },
    {
      label: "Median Market Cap",
      value: `${config.currencySymbol}${(summary.medianMarketCap / config.capDisplayUnit).toFixed(1)}${config.capDisplaySuffix}`,
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4"
        >
          <div className="text-sm text-gray-500 dark:text-gray-400">{stat.label}</div>
          <div className="text-xl font-bold mt-1">{stat.value}</div>
        </div>
      ))}
    </div>
  );
}

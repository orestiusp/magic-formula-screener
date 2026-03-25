"use client";

import { useState } from "react";
import { Market } from "@/lib/types";
import { MARKET_CONFIGS } from "@/lib/constants";

interface Props {
  topN: number;
  onTopNChange: (value: number) => void;
  minMarketCapM: number;
  onMinMarketCapMChange: (value: number) => void;
  market: Market;
}

export function FilterPanel({ topN, onTopNChange, minMarketCapM, onMinMarketCapMChange, market }: Props) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const config = MARKET_CONFIGS[market];

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Settings</h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">
            Top N Results
          </label>
          <input
            type="number"
            value={topN}
            onChange={(e) => {
              const val = e.target.value === "" ? 1 : Math.max(1, Math.min(100, Number(e.target.value)));
              onTopNChange(val);
            }}
            min={1}
            max={100}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">Greenblatt recommends 20-30</p>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">
            Min Market Cap ({config.currencySymbol}M)
          </label>
          <input
            type="number"
            value={minMarketCapM}
            onChange={(e) => {
              const val = e.target.value === "" ? 0 : Math.max(0, Number(e.target.value));
              onMinMarketCapMChange(val);
            }}
            min={0}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            Default: {config.currencySymbol}{(config.minMarketCap / 1e6).toFixed(0)}M
          </p>
        </div>
      </div>

      <button
        type="button"
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="text-sm text-blue-500 hover:text-blue-600"
      >
        {showAdvanced ? "Hide" : "Show"} default filters
      </button>

      {showAdvanced && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg text-sm">
          <div>
            <span className="font-medium">Debt/Equity</span>
            <p className="text-gray-500">&lt; 2.0x</p>
          </div>
          <div>
            <span className="font-medium">Current Ratio</span>
            <p className="text-gray-500">&gt; 1.0x</p>
          </div>
          <div>
            <span className="font-medium">EBIT</span>
            <p className="text-gray-500">Must be positive</p>
          </div>
          <div>
            <span className="font-medium">Listed</span>
            <p className="text-gray-500">&gt; 1 year</p>
          </div>
          <div>
            <span className="font-medium">Excluded Sectors</span>
            <p className="text-gray-500">Financials, Utilities, REITs</p>
          </div>
        </div>
      )}
    </div>
  );
}

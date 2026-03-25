"use client";

import { Universe } from "@/lib/types";
import { UNIVERSE_OPTIONS } from "@/lib/constants";

interface Props {
  value: Universe;
  onChange: (value: Universe) => void;
  customTickers: string;
  onCustomTickersChange: (value: string) => void;
}

export function UniverseSelector({ value, onChange, customTickers, onCustomTickersChange }: Props) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Select Market Universe</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {UNIVERSE_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={`p-4 rounded-lg border-2 text-left transition-colors ${
              value === option.value
                ? "border-blue-500 bg-blue-50 dark:bg-blue-950"
                : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
            }`}
          >
            <div className="font-medium">{option.label}</div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {option.description}
            </div>
          </button>
        ))}
      </div>

      {value === "custom" && (
        <div className="mt-3">
          <label className="block text-sm font-medium mb-1">
            Tickers (comma-separated)
          </label>
          <textarea
            value={customTickers}
            onChange={(e) => onCustomTickersChange(e.target.value)}
            placeholder="AAPL, MSFT, GOOG, AMZN, META"
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      )}
    </div>
  );
}

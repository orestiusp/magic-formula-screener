"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Universe } from "@/lib/types";
import { getMarketForUniverse, DEFAULT_TOP_N, MARKET_CONFIGS } from "@/lib/constants";
import { UniverseSelector } from "./UniverseSelector";
import { FilterPanel } from "./FilterPanel";

export function ScreenerForm() {
  const router = useRouter();
  const [universe, setUniverse] = useState<Universe>("sp500");
  const [customTickers, setCustomTickers] = useState("");
  const [topN, setTopN] = useState(DEFAULT_TOP_N);
  const [minMarketCapM, setMinMarketCapM] = useState(300);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const market = getMarketForUniverse(universe);

  function handleUniverseChange(u: Universe) {
    setUniverse(u);
    // Update default min market cap when switching markets
    const m = getMarketForUniverse(u);
    setMinMarketCapM(MARKET_CONFIGS[m].minMarketCap / 1e6);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/screener/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          universe,
          customTickers: universe === "custom" ? customTickers.replace(/\s+/g, "") : undefined,
          topN,
          minMarketCap: minMarketCapM * 1e6,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error || "Failed to start screener");
        setLoading(false);
        return;
      }

      router.push(`/results?jobId=${data.jobId}&universe=${universe}`);
    } catch {
      setError("Failed to connect to server");
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      <UniverseSelector
        value={universe}
        onChange={handleUniverseChange}
        customTickers={customTickers}
        onCustomTickersChange={setCustomTickers}
      />

      <FilterPanel
        topN={topN}
        onTopNChange={setTopN}
        minMarketCapM={minMarketCapM}
        onMinMarketCapMChange={setMinMarketCapM}
        market={market}
      />

      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading || (universe === "custom" && !customTickers.trim())}
        className="w-full py-3 px-6 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold rounded-lg transition-colors text-lg"
      >
        {loading ? "Starting..." : "Run Screener"}
      </button>
    </form>
  );
}

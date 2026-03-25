"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { Universe } from "@/lib/types";
import { useScreenerJob } from "@/hooks/useScreenerJob";
import { LoadingState } from "@/components/LoadingState";
import { ResultsTable } from "@/components/ResultsTable";
import { SummaryStats } from "@/components/SummaryStats";
import { SectorChart } from "@/components/SectorChart";
import { ExportButton } from "@/components/ExportButton";
import Link from "next/link";

function ResultsContent() {
  const searchParams = useSearchParams();
  const jobId = searchParams.get("jobId");
  const universe = (searchParams.get("universe") || "sp500") as Universe;

  const { status, results, error, isLoading } = useScreenerJob(jobId, universe);

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-20 text-center">
        <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl p-8">
          <h2 className="text-xl font-semibold text-red-700 dark:text-red-300 mb-2">
            Screener Failed
          </h2>
          <p className="text-red-600 dark:text-red-400 text-sm mb-4 font-mono whitespace-pre-wrap max-h-48 overflow-auto">
            {error}
          </p>
          <Link
            href="/"
            className="inline-block px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Try Again
          </Link>
        </div>
      </div>
    );
  }

  if (isLoading || !results) {
    return <LoadingState progress={status?.progress || ""} />;
  }

  const dateStr = new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">
            Magic Formula Top {results.stocks.length}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Screened {dateStr} &middot; {results.market.toUpperCase()} market
          </p>
        </div>
        <div className="flex gap-3">
          <ExportButton stocks={results.stocks} />
          <Link
            href="/"
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            New Screen
          </Link>
        </div>
      </div>

      <SummaryStats summary={results.summary} market={results.market} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
            <ResultsTable stocks={results.stocks} market={results.market} />
          </div>
        </div>
        <div>
          <SectorChart distribution={results.summary.sectorDistribution} />

          <div className="mt-6 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-4 text-sm space-y-2">
            <h3 className="font-semibold text-blue-800 dark:text-blue-200">
              How to Use (Greenblatt&apos;s Method)
            </h3>
            <ul className="list-disc list-inside text-blue-700 dark:text-blue-300 space-y-1">
              <li>Buy 5-7 positions from the top 30 every 2-3 months</li>
              <li>Hold each for ~1 year</li>
              <li>Sell losers just before 1 year (tax loss harvesting)</li>
              <li>Sell winners just after 1 year (long-term cap gains)</li>
              <li>Commit to the strategy for at least 3-5 years</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="text-xs text-gray-400 text-center pt-4 border-t border-gray-200 dark:border-gray-700">
        This screener produces educational analysis, not investment advice.
        Data sourced via yfinance and may be delayed or estimated. Always verify before trading.
      </div>
    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense fallback={<LoadingState progress="" />}>
      <ResultsContent />
    </Suspense>
  );
}

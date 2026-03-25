"use client";

import { useEffect, useState } from "react";

interface Props {
  progress: string;
}

export function LoadingState({ progress }: Props) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;

  return (
    <div className="flex flex-col items-center justify-center py-20 space-y-6">
      <div className="relative">
        <div className="w-16 h-16 border-4 border-gray-200 dark:border-gray-700 rounded-full" />
        <div className="absolute top-0 left-0 w-16 h-16 border-4 border-blue-500 rounded-full border-t-transparent animate-spin" />
      </div>

      <div className="text-center space-y-2">
        <h2 className="text-xl font-semibold">Running Magic Formula Screener</h2>
        <p className="text-gray-500 dark:text-gray-400">
          {minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`} elapsed
        </p>
      </div>

      {progress && (
        <div className="max-w-lg w-full px-4">
          <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-3 font-mono text-xs text-gray-600 dark:text-gray-300 truncate">
            {progress}
          </div>
        </div>
      )}

      <p className="text-sm text-gray-400 max-w-md text-center">
        Fetching financial data for all stocks in the universe. This typically takes 2-5 minutes depending on the market size.
      </p>
    </div>
  );
}

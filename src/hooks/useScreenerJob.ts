"use client";

import { useState, useEffect, useCallback } from "react";
import { JobStatusResponse, ScreenerResponse, Universe } from "@/lib/types";

interface UseScreenerJobResult {
  status: JobStatusResponse | null;
  results: ScreenerResponse | null;
  error: string | null;
  isLoading: boolean;
}

export function useScreenerJob(jobId: string | null, universe: Universe): UseScreenerJobResult {
  const [status, setStatus] = useState<JobStatusResponse | null>(null);
  const [results, setResults] = useState<ScreenerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchResults = useCallback(async () => {
    if (!jobId) return;
    try {
      const res = await fetch(`/api/screener/results?jobId=${jobId}&universe=${universe}`);
      const data = await res.json();
      if (res.ok) {
        setResults(data);
      } else {
        setError(data.error || "Failed to fetch results");
      }
    } catch {
      setError("Failed to connect to server");
    } finally {
      setIsLoading(false);
    }
  }, [jobId, universe]);

  useEffect(() => {
    if (!jobId) {
      setIsLoading(false);
      setError("No job ID provided");
      return;
    }

    let intervalId: NodeJS.Timeout;

    async function pollStatus() {
      try {
        const res = await fetch(`/api/screener/status?jobId=${jobId}`);
        const data: JobStatusResponse = await res.json();

        if (!res.ok) {
          setError(data.error || "Job not found");
          setIsLoading(false);
          clearInterval(intervalId);
          return;
        }

        setStatus(data);

        if (data.status === "completed") {
          clearInterval(intervalId);
          await fetchResults();
        } else if (data.status === "failed") {
          clearInterval(intervalId);
          setError(data.error || "Screener failed");
          setIsLoading(false);
        }
      } catch {
        setError("Failed to connect to server");
        setIsLoading(false);
        clearInterval(intervalId);
      }
    }

    pollStatus();
    intervalId = setInterval(pollStatus, 3000);

    return () => clearInterval(intervalId);
  }, [jobId, fetchResults]);

  return { status, results, error, isLoading };
}

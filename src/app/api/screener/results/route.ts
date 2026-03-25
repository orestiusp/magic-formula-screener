import { NextRequest, NextResponse } from "next/server";
import { existsSync } from "fs";
import { getJob } from "@/lib/job-store";
import { parseScreenerCSV, computeSummary } from "@/lib/csv-parser";
import { getMarketForUniverse } from "@/lib/constants";
import { ScreenerResponse, Universe } from "@/lib/types";

export async function GET(request: NextRequest) {
  const jobId = request.nextUrl.searchParams.get("jobId");
  const universe = (request.nextUrl.searchParams.get("universe") || "sp500") as Universe;

  if (!jobId) {
    return NextResponse.json({ error: "Missing jobId parameter" }, { status: 400 });
  }

  const job = getJob(jobId);
  if (!job) {
    return NextResponse.json({ error: "Job not found" }, { status: 404 });
  }

  if (job.status !== "completed") {
    return NextResponse.json(
      { error: `Job is not completed (status: ${job.status})` },
      { status: 400 }
    );
  }

  if (!existsSync(job.outputPath)) {
    return NextResponse.json({ error: "Results file not found" }, { status: 404 });
  }

  try {
    const stocks = parseScreenerCSV(job.outputPath);
    const market = getMarketForUniverse(universe);
    const summary = computeSummary(stocks, stocks.length);

    const response: ScreenerResponse = {
      stocks,
      summary,
      market,
    };

    return NextResponse.json(response);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to parse results" },
      { status: 500 }
    );
  }
}

import { NextRequest, NextResponse } from "next/server";
import { hasRunningJob } from "@/lib/job-store";
import { runScreener } from "@/lib/screener";
import { ScreenerConfig, Universe } from "@/lib/types";

const VALID_UNIVERSES: Universe[] = ["sp500", "sp400", "sp500+sp400", "nifty500", "custom"];

export async function POST(request: NextRequest) {
  try {
    if (hasRunningJob()) {
      return NextResponse.json(
        { error: "A screener job is already running. Please wait for it to complete." },
        { status: 409 }
      );
    }

    const body = await request.json();

    const universe = body.universe as Universe;
    if (!VALID_UNIVERSES.includes(universe)) {
      return NextResponse.json(
        { error: `Invalid universe: ${universe}` },
        { status: 400 }
      );
    }

    const config: ScreenerConfig = {
      universe,
      customTickers: body.customTickers || undefined,
      topN: Math.max(1, Math.min(100, Number(body.topN) || 30)),
      minMarketCap: body.minMarketCap ? Number(body.minMarketCap) : undefined,
    };

    if (universe === "custom" && !config.customTickers) {
      return NextResponse.json(
        { error: "Custom universe requires a ticker list" },
        { status: 400 }
      );
    }

    const jobId = runScreener(config);

    return NextResponse.json({ jobId }, { status: 202 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

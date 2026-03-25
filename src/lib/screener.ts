import { execFile } from "child_process";
import { existsSync } from "fs";
import path from "path";
import { v4 as uuidv4 } from "uuid";
import { createJob, updateJob } from "./job-store";
import { getMarketForUniverse, MARKET_CONFIGS } from "./constants";
import { ScreenerConfig } from "./types";

const TICKER_PATTERN = /^[A-Za-z0-9.,\-&]+$/;

function buildArgs(config: ScreenerConfig, outputPath: string): string[] {
  const market = getMarketForUniverse(config.universe);
  const marketConfig = MARKET_CONFIGS[market];
  const minCap = config.minMarketCap ?? marketConfig.minMarketCap;

  const args: string[] = [
    "--universe", config.universe === "custom" ? "custom" : config.universe,
    "--output", outputPath,
    "--top", String(config.topN),
    "--min-market-cap", String(minCap),
  ];

  if (config.universe === "custom" && config.customTickers) {
    args.push("--tickers", config.customTickers.trim());
  }

  return args;
}

function runScript(
  scriptPath: string,
  args: string[],
  env: Record<string, string | undefined>,
  jobId: string,
  onSuccess: () => void,
  onFailure: (stdout: string, stderr: string, error: Error) => void,
) {
  const child = execFile("python3", [scriptPath, ...args], {
    timeout: 10 * 60 * 1000,
    maxBuffer: 10 * 1024 * 1024,
    env: { ...process.env, ...env },
  }, (error, stdout, stderr) => {
    if (error) {
      onFailure(stdout || "", stderr || "", error);
    } else {
      onSuccess();
    }
  });

  if (child.stdout) {
    child.stdout.on("data", (data: Buffer) => {
      const lines = data.toString().split("\n").filter(Boolean);
      if (lines.length > 0) {
        updateJob(jobId, { progress: lines[lines.length - 1].trim() });
      }
    });
  }

  if (child.stderr) {
    child.stderr.on("data", (data: Buffer) => {
      const line = data.toString().trim();
      if (line) {
        updateJob(jobId, { progress: line });
      }
    });
  }
}

export function runScreener(config: ScreenerConfig): string {
  const jobId = uuidv4();
  const outputPath = `/tmp/mf_${jobId}.csv`;

  createJob(jobId, outputPath);

  if (config.universe === "custom" && config.customTickers) {
    const tickers = config.customTickers.trim();
    if (!TICKER_PATTERN.test(tickers)) {
      updateJob(jobId, {
        status: "failed",
        error: "Invalid ticker format. Use comma-separated tickers (e.g. AAPL,MSFT,GOOG)",
      });
      return jobId;
    }
  }

  updateJob(jobId, { status: "running" });

  const yfinancePath = path.join(process.cwd(), "scripts", "fetch_yfinance.py");
  const fmpPath = path.join(process.cwd(), "scripts", "fetch_fmp.py");
  const args = buildArgs(config, outputPath);
  const fmpKey = process.env.FMP_API_KEY;

  // Try yfinance first
  runScript(yfinancePath, args, {}, jobId,
    // yfinance succeeded
    () => {
      // Verify the CSV was actually created and has data
      if (existsSync(outputPath)) {
        updateJob(jobId, { status: "completed" });
      } else {
        // Output file missing — try FMP fallback
        attemptFmpFallback();
      }
    },
    // yfinance failed — try FMP fallback
    (stdout, stderr, error) => {
      if (fmpKey) {
        updateJob(jobId, { progress: "yfinance failed, trying FMP fallback..." });
        attemptFmpFallback();
      } else {
        const errorDetail = stderr.trim() || stdout.trim() || error.message;
        const lines = errorDetail.split("\n").filter(Boolean);
        updateJob(jobId, {
          status: "failed",
          error: lines.slice(-5).join("\n"),
        });
      }
    },
  );

  function attemptFmpFallback() {
    if (!fmpKey) {
      updateJob(jobId, {
        status: "failed",
        error: "yfinance failed and no FMP API key configured for fallback.",
      });
      return;
    }

    const fmpArgs = [...args, "--api-key", fmpKey];

    runScript(fmpPath, fmpArgs, { FMP_API_KEY: fmpKey }, jobId,
      () => {
        updateJob(jobId, { status: "completed" });
      },
      (stdout, stderr, error) => {
        const errorDetail = stderr.trim() || stdout.trim() || error.message;
        const lines = errorDetail.split("\n").filter(Boolean);
        updateJob(jobId, {
          status: "failed",
          error: "Both yfinance and FMP failed.\n" + lines.slice(-5).join("\n"),
        });
      },
    );
  }

  return jobId;
}

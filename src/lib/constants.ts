import { Market, MarketConfig, Universe } from "./types";

export const MARKET_CONFIGS: Record<Market, MarketConfig> = {
  us: {
    currency: "USD",
    currencySymbol: "$",
    minMarketCap: 300_000_000,
    capDisplayUnit: 1e9,
    capDisplaySuffix: "B",
  },
  india: {
    currency: "INR",
    currencySymbol: "\u20B9",
    minMarketCap: 25_000_000_000,
    capDisplayUnit: 1e7,
    capDisplaySuffix: "Cr",
  },
};

export function getMarketForUniverse(universe: Universe): Market {
  return universe === "nifty500" ? "india" : "us";
}

export const UNIVERSE_OPTIONS: { value: Universe; label: string; description: string }[] = [
  { value: "sp500", label: "S&P 500", description: "500 large-cap US stocks" },
  { value: "sp400", label: "S&P 400 MidCap", description: "400 mid-cap US stocks" },
  { value: "sp500+sp400", label: "S&P 500 + S&P 400", description: "900 large + mid-cap US stocks" },
  { value: "nifty500", label: "Nifty 500", description: "500 large + mid + small-cap Indian stocks (NSE)" },
  { value: "custom", label: "Custom", description: "Enter your own ticker list" },
];

export const DEFAULT_TOP_N = 30;

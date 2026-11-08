"""Independent Magic Formula math for the research case study.

This is not the screener. The screener's behavior is locked by
research/tests/test_original_formula.py. Differences from that code are
intentional and listed in research/PROTOCOL.md.
"""

from __future__ import annotations

import pandas as pd

MIN_MARKET_CAP = 300_000_000
REPO_ROC_CAP = 5.0


def prepare_metrics(df: pd.DataFrame, roc_cap: float | None) -> pd.DataFrame:
    """Keep rows with a defined positive enterprise value and tangible capital.

    Earnings yield is EBIT / enterprise value.
    Return on capital is EBIT / (net working capital + net fixed assets).
    """
    out = df.copy()
    out["tangible_capital"] = out["net_working_capital"] + out["net_ppe"]
    out = out[
        (out["ebit"] > 0)
        & (out["enterprise_value"] > 0)
        & (out["tangible_capital"] > 0)
        & (out["market_cap"] >= MIN_MARKET_CAP)
    ].copy()
    out["earnings_yield"] = out["ebit"] / out["enterprise_value"]
    roc = out["ebit"] / out["tangible_capital"]
    if roc_cap is not None:
        roc = roc.clip(upper=roc_cap)
    out["return_on_capital"] = roc
    return out


def rank_magic_formula(df: pd.DataFrame, roc_cap: float | None = None) -> pd.DataFrame:
    """Rank with a deterministic tie-break the original screener does not have."""
    out = prepare_metrics(df, roc_cap=roc_cap)
    if out.empty:
        return out
    out["ey_rank"] = out["earnings_yield"].rank(ascending=False, method="min").astype(int)
    out["roc_rank"] = out["return_on_capital"].rank(ascending=False, method="min").astype(int)
    out["mf_score"] = out["ey_rank"] + out["roc_rank"]
    out = out.sort_values(
        ["mf_score", "earnings_yield", "ticker"],
        ascending=[True, False, True],
        kind="mergesort",
    )
    out["mf_rank"] = range(1, len(out) + 1)
    return out


def apply_repo_ratio_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Match the app: a missing debt/equity or current ratio does not fail."""
    de_ok = df["debt_equity"].isna() | (df["debt_equity"] < 2.0)
    cr_ok = df["current_ratio"].isna() | (df["current_ratio"] > 1.0)
    return df[de_ok & cr_ok].copy()

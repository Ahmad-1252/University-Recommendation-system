"""
Fairness metrics for recommendation system bias detection.

Provides tools to measure and monitor:
  - Country-based bias (score distribution skew across countries)
  - Financial access (% of programs accessible at each budget level)
  - Tier distribution by region
  - Demographic parity across protected attributes
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_country_bias(
    df: pd.DataFrame,
    score_col: str = "match_score",
    min_samples: int = 10,
    bias_threshold: float = 0.10,
) -> pd.DataFrame:
    """Measure score distribution skew across countries.

    Args:
        df: DataFrame with scores and country column.
        score_col: name of the score column.
        min_samples: minimum samples per country to include.
        bias_threshold: flag countries with > |threshold| deviation.

    Returns:
        DataFrame with country, mean score, std, count, and bias ratio.
    """
    stats = df.groupby("country")[score_col].agg(["mean", "std", "count"])
    stats = stats[stats["count"] >= min_samples]
    global_mean = df[score_col].mean()
    stats["bias"] = (stats["mean"] - global_mean) / global_mean
    stats["flagged"] = stats["bias"].abs() > bias_threshold
    return stats.sort_values("bias", ascending=False)


def calculate_financial_access(
    df: pd.DataFrame,
    tuition_col: str = "tuition_international",
) -> Dict[int, float]:
    """Measure what % of programs are accessible at each budget level.

    Returns:
        dict mapping budget thresholds to fraction of accessible programs.
    """
    budgets = [5000, 10000, 15000, 20000, 30000, 50000, 100000]
    tuition = df[tuition_col].dropna()
    return {b: round(float((tuition <= b).mean()), 4) for b in budgets}


def calculate_tier_distribution_by_country(
    df: pd.DataFrame,
    tier_col: str = "university_tier",
) -> pd.DataFrame:
    """Compute normalized tier distribution per country.

    Returns:
        DataFrame with countries as rows, tiers as columns, values as proportions.
    """
    return pd.crosstab(df["country"], df[tier_col], normalize="index")


def demographic_parity(
    predicted_positive: np.ndarray,
    groups: np.ndarray,
) -> Dict[str, float]:
    """Calculate P(positive_prediction | group) for each group.

    Demographic parity requires: P(pos | A) ≈ P(pos | B) for all groups.

    Args:
        predicted_positive: boolean array of positive predictions.
        groups: array of group labels (e.g. country names).

    Returns:
        dict mapping group → P(positive prediction).
    """
    result = {}
    for group in np.unique(groups):
        mask = groups == group
        result[str(group)] = float(predicted_positive[mask].mean())
    return result


def equalized_odds(
    predictions: np.ndarray,
    labels: np.ndarray,
    groups: np.ndarray,
) -> Dict[str, Dict[str, float]]:
    """Calculate TPR and FPR per group.

    Equalized odds requires: TPR and FPR equal across groups.

    Returns:
        dict mapping group → {tpr, fpr, count}.
    """
    result = {}
    for group in np.unique(groups):
        mask = groups == group
        g_pred = predictions[mask]
        g_true = labels[mask]

        tp = ((g_pred == 1) & (g_true == 1)).sum()
        fn = ((g_pred == 0) & (g_true == 1)).sum()
        fp = ((g_pred == 1) & (g_true == 0)).sum()
        tn = ((g_pred == 0) & (g_true == 0)).sum()

        tpr = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0

        result[str(group)] = {"tpr": round(tpr, 4), "fpr": round(fpr, 4), "count": int(mask.sum())}
    return result


def fairness_report(
    df: pd.DataFrame,
    score_col: str = "match_score",
    tier_col: str = "university_tier",
    tuition_col: str = "tuition_international",
) -> Dict[str, Any]:
    """Generate a complete fairness audit report.

    Args:
        df: scored DataFrame with predictions.
        score_col: name of the match score column.
        tier_col: name of the tier column.
        tuition_col: name of the tuition column.

    Returns:
        dict with country_bias, financial_access, tier_distribution.
    """
    report = {}

    # Country bias
    try:
        bias_df = calculate_country_bias(df, score_col)
        flagged = bias_df[bias_df["flagged"]]
        report["country_bias"] = {
            "total_countries": len(bias_df),
            "flagged_countries": len(flagged),
            "max_bias": round(float(bias_df["bias"].abs().max()), 4) if len(bias_df) > 0 else 0.0,
            "worst_country": str(flagged.index[0]) if len(flagged) > 0 else None,
        }
    except Exception as e:
        report["country_bias"] = {"error": str(e)}

    # Financial access
    try:
        report["financial_access"] = calculate_financial_access(df, tuition_col)
    except Exception as e:
        report["financial_access"] = {"error": str(e)}

    # Tier distribution
    try:
        tier_dist = calculate_tier_distribution_by_country(df, tier_col)
        # Find countries with 0% top-tier programs
        if "top" in tier_dist.columns:
            no_top = tier_dist[tier_dist["top"] == 0].index.tolist()
            report["tier_equity"] = {
                "countries_with_no_top_tier": no_top[:10],
                "total_no_top": len(no_top),
            }
        else:
            report["tier_equity"] = {"note": "no 'top' tier in data"}
    except Exception as e:
        report["tier_equity"] = {"error": str(e)}

    return report

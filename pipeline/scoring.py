"""
Canonical match_score computation — single source of truth.

All code paths (recommend(), score_program(), retrain scored_programs)
MUST use these functions to ensure consistent scoring.

Weight rationale:
  - "top" tier programs receive full weight (1.0)
  - "good" tier receives 60% weight (0.6) — still strongly desirable
  - "standard" tier receives 20% weight (0.2) — contributes but doesn't dominate

The resulting score is a probability-weighted sum in [0, 1].
"""

from typing import Dict, List, Sequence, Union

import numpy as np

# ── Canonical tier weights ────────────────────────────────────────────────────
TIER_WEIGHTS: Dict[str, float] = {
    "top": 1.0,
    "good": 0.6,
    "standard": 0.2,
}


def compute_match_score(
    proba: Union[np.ndarray, Sequence[float]],
    classes: List[str],
) -> float:
    """Compute match_score from a probability vector.

    Args:
        proba: array of shape (n_classes,) — predicted class probabilities.
        classes: list of class names matching proba indices.

    Returns:
        float in [0, 1].
    """
    score = 0.0
    for tier, weight in TIER_WEIGHTS.items():
        if tier in classes:
            score += float(proba[classes.index(tier)]) * weight
    return min(max(score, 0.0), 1.0)


def compute_match_scores_batch(
    proba: np.ndarray,
    classes: List[str],
) -> np.ndarray:
    """Vectorised match_score for an (n_samples, n_classes) probability matrix.

    Args:
        proba: array of shape (n_samples, n_classes).
        classes: list of class names matching column indices.

    Returns:
        1-D array of shape (n_samples,) with scores clipped to [0, 1].
    """
    weight_vec = np.zeros(len(classes), dtype=np.float64)
    for tier, weight in TIER_WEIGHTS.items():
        if tier in classes:
            weight_vec[classes.index(tier)] = weight
    scores = proba @ weight_vec
    return np.clip(scores, 0.0, 1.0)


def compute_confidence_band(proba: Union[np.ndarray, Sequence[float]]) -> str:
    """Return 'high', 'medium', or 'low' based on max predicted probability.

    High  = dominant class has ≥ 80% probability.
    Medium = dominant class has ≥ 50% probability.
    Low   = no class exceeds 50%.
    """
    max_p = float(max(proba)) if not isinstance(proba, np.ndarray) else float(proba.max())
    if max_p >= 0.80:
        return "high"
    if max_p >= 0.50:
        return "medium"
    return "low"


def compute_confidence_bands_batch(proba: np.ndarray) -> np.ndarray:
    """Vectorised confidence bands for (n_samples, n_classes) matrix."""
    max_proba = proba.max(axis=1)
    return np.where(
        max_proba >= 0.80, "high",
        np.where(max_proba >= 0.50, "medium", "low"),
    )

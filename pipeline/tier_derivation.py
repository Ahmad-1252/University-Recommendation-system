"""Multi-signal tier derivation using real QS ranking data.

Replaces the old synthetic `pd.cut(qs_world_ranking)` approach with a
cascading multi-signal strategy built on 5 real QS ranking systems.

Tier Definitions:
    top      -- ~QS World Top 200, or strong regional equivalent
    good     -- ~QS World 200-800, or moderate regional ranking
    standard -- QS World 800+, regional-only, or unranked universities

Cascading Logic:
    1. If QS World ranking exists  → primary signal (weight 0.60)
       Boosted by subject / sustainability rankings if available.
    2. If only regional rankings exist → scale down (× 0.70 discount)
       because Asian #50 ≈ World #300, not World #50.
    3. No rankings at all → "standard" immediately.
"""

from __future__ import annotations

import logging
from typing import Optional

from pipeline.ranking_normalizer import (
    QS_WORLD,
    QS_SUBJECT,
    QS_ASIA,
    QS_EUROPE,
    QS_LATAM,
    QS_EE,
    QS_ARAB,
    QS_SUSTAIN,
    QS_EMPLOY,
    extract_rank_value,
    rank_to_percentile_score,
    normalize_rankings_array,
)

logger = logging.getLogger(__name__)

# ── Tier boundary constants ──────────────────────────────────────────────────
TOP_THRESHOLD = 0.70     # score ≥ 0.70 → top   (QS World ≈ ≤200)
GOOD_THRESHOLD = 0.35    # score ≥ 0.35 → good  (QS World ≈ 200-800)
# score < 0.35 → standard

# ── Max ranks per system (for percentile score normalisation) ─────────────────
MAX_RANKS = {
    QS_WORLD: 1500,
    QS_SUBJECT: 900,
    QS_ASIA: 1400,
    QS_EUROPE: 900,
    QS_LATAM: 400,
    QS_EE: 400,
    QS_ARAB: 300,
    QS_SUSTAIN: 1400,
    QS_EMPLOY: 1000,
}

# ── Weights used when QS World is the primary signal ─────────────────────────
PRIMARY_WEIGHTS = {
    QS_WORLD:   0.60,
    QS_SUBJECT: 0.20,
    QS_SUSTAIN: 0.10,
    QS_EMPLOY:  0.10,
}

# ── Regional ranking systems (no QS World present) ───────────────────────────
REGIONAL_SYSTEMS = [QS_ASIA, QS_EUROPE, QS_LATAM, QS_EE, QS_ARAB]
REGIONAL_DISCOUNT = 0.70   # regional rankings imply lower global standing


def _weighted_average(scores: dict[str, float], weights: dict[str, float]) -> float:
    """Weighted average over available signals only (normalises missing weights)."""
    total_w = 0.0
    total_s = 0.0
    for system, score in scores.items():
        w = weights.get(system, 0.0)
        total_s += w * score
        total_w += w
    return total_s / total_w if total_w > 0 else 0.0


def derive_tier(rankings: list[dict]) -> str:
    """Derive university tier from real QS ranking signals.

    Args:
        rankings: The ``rankings`` array from a TopUniversities university
                  record (after normalisation). Each element must have at
                  least ``ranking_type`` and ``rank`` (or ``rank_display``).

    Returns:
        One of ``"top"``, ``"good"``, or ``"standard"``.
    """
    # Normalise array first (dedup, parse rank strings)
    rankings = normalize_rankings_array(rankings)

    qs_world = extract_rank_value(rankings, QS_WORLD)

    # ── Path 1: QS World present ─────────────────────────────────────────────
    if qs_world:
        scores: dict[str, float] = {
            QS_WORLD: rank_to_percentile_score(qs_world, MAX_RANKS[QS_WORLD])
        }
        # Optionally boost with other global signals
        for system in (QS_SUBJECT, QS_SUSTAIN, QS_EMPLOY):
            rank = extract_rank_value(rankings, system)
            if rank:
                scores[system] = rank_to_percentile_score(rank, MAX_RANKS[system])

        composite = _weighted_average(scores, PRIMARY_WEIGHTS)

    # ── Path 2: Regional rankings only ───────────────────────────────────────
    else:
        regional_scores: list[float] = []
        for system in REGIONAL_SYSTEMS:
            rank = extract_rank_value(rankings, system)
            if rank:
                regional_scores.append(
                    rank_to_percentile_score(rank, MAX_RANKS[system])
                )

        if not regional_scores:
            # No ranking data at all → standard
            return "standard"

        # Use the strongest regional signal and discount it
        composite = max(regional_scores) * REGIONAL_DISCOUNT

    # ── Apply thresholds ─────────────────────────────────────────────────────
    if composite >= TOP_THRESHOLD:
        return "top"
    if composite >= GOOD_THRESHOLD:
        return "good"
    return "standard"


def derive_tier_with_metadata(rankings: list[dict]) -> dict:
    """Like ``derive_tier`` but returns full diagnostic metadata.

    Useful for auditing, adversarial validation, and debugging.

    Returns:
        Dict with keys: tier, composite_score, qs_world_rank, path, signals
    """
    rankings = normalize_rankings_array(rankings)
    qs_world = extract_rank_value(rankings, QS_WORLD)

    metadata: dict = {
        "qs_world_rank": qs_world,
        "signals": {},
        "path": None,
        "composite_score": 0.0,
        "tier": "standard",
    }

    if qs_world:
        metadata["path"] = "qs_world_primary"
        scores: dict[str, float] = {
            QS_WORLD: rank_to_percentile_score(qs_world, MAX_RANKS[QS_WORLD])
        }
        for system in (QS_SUBJECT, QS_SUSTAIN, QS_EMPLOY):
            rank = extract_rank_value(rankings, system)
            if rank:
                scores[system] = rank_to_percentile_score(rank, MAX_RANKS[system])
        composite = _weighted_average(scores, PRIMARY_WEIGHTS)
        metadata["signals"] = scores

    else:
        regional_scores: dict[str, float] = {}
        for system in REGIONAL_SYSTEMS:
            rank = extract_rank_value(rankings, system)
            if rank:
                regional_scores[system] = rank_to_percentile_score(
                    rank, MAX_RANKS[system]
                )

        if not regional_scores:
            metadata["path"] = "no_rankings"
            return metadata

        composite = max(regional_scores.values()) * REGIONAL_DISCOUNT
        metadata["path"] = "regional_fallback"
        metadata["signals"] = regional_scores

    metadata["composite_score"] = round(composite, 4)

    if composite >= TOP_THRESHOLD:
        metadata["tier"] = "top"
    elif composite >= GOOD_THRESHOLD:
        metadata["tier"] = "good"
    else:
        metadata["tier"] = "standard"

    return metadata


def print_tier_stats(records: list[dict]) -> None:
    """Print tier distribution summary for a list of university records.

    Args:
        records: List of dicts, each with a ``rankings`` key.
    """
    counts: dict[str, int] = {"top": 0, "good": 0, "standard": 0}
    paths: dict[str, int] = {"qs_world_primary": 0, "regional_fallback": 0, "no_rankings": 0}

    for rec in records:
        meta = derive_tier_with_metadata(rec.get("rankings", []))
        counts[meta["tier"]] += 1
        paths[meta.get("path", "no_rankings")] += 1

    total = len(records)
    print("\n── Tier Distribution ──────────────────────────────")
    for tier, count in counts.items():
        pct = 100 * count / total if total else 0
        print(f"  {tier:10s}: {count:5d}  ({pct:.1f}%)")

    print("\n── Derivation Path ─────────────────────────────────")
    for path, count in paths.items():
        pct = 100 * count / total if total else 0
        print(f"  {path:25s}: {count:5d}  ({pct:.1f}%)")
    print(f"\n  Total: {total}")
    print("────────────────────────────────────────────────────\n")

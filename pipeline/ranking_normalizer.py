"""Ranking normalization utilities for TopUniversities data.

Handles quirks found in real scraped data:
  - Duplicate ranking entries (same ranking appears twice in array)
  - Range ranks: "1201-1400" → midpoint 1300
  - Tied ranks: "=114" → 114
  - Bound ranks: "1401+" → 1401
  - Hash prefix: "#101" → 101
"""

from __future__ import annotations

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Canonical names we recognize in the TopUniversities rankings array
QS_WORLD = "QS World University Rankings"
QS_SUBJECT = "QS WUR Ranking By Subject"
QS_ASIA = "Asian University Rankings"
QS_EUROPE = "Europe University Rankings"
QS_LATAM = "Latin America and the Caribbean Rankings"
QS_EE = "EECA University Rankings"          # Emerging Europe & Central Asia
QS_ARAB = "Arab Region University Rankings"
QS_SUSTAIN = "QS Sustainability Ranking"
QS_EMPLOY = "QS Graduate Employability Rankings"

ALL_KNOWN_SYSTEMS = {
    QS_WORLD, QS_SUBJECT, QS_ASIA, QS_EUROPE,
    QS_LATAM, QS_EE, QS_ARAB, QS_SUSTAIN, QS_EMPLOY,
}


def parse_rank(rank_text: str | None) -> Optional[int]:
    """Parse a rank string into a numeric integer (lower = better).

    Handles all TopUniversities rank display formats:
        "#1"        → 1
        "=5"        → 5
        "101-150"   → 101   (take lower bound)
        "501-550"   → 501
        "1201-1400" → 1201
        "1401+"     → 1401
        "1001+"     → 1001
    """
    if not rank_text:
        return None

    cleaned = str(rank_text).strip().lstrip("#").strip()

    # "1401+" style bound  (e.g. "1001+")
    bound_match = re.match(r"(\d+)\+", cleaned)
    if bound_match:
        return int(bound_match.group(1))

    # "101-150" range → take lower bound
    range_match = re.match(r"(\d+)\s*[-–]\s*(\d+)", cleaned)
    if range_match:
        return int(range_match.group(1))

    # "=5" tied or plain "5"
    exact_match = re.match(r"=?(\d+)", cleaned)
    if exact_match:
        return int(exact_match.group(1))

    return None


def parse_rank_midpoint(rank_text: str | None) -> Optional[int]:
    """Like parse_rank but uses midpoint for ranges (useful for scoring)."""
    if not rank_text:
        return None

    cleaned = str(rank_text).strip().lstrip("#").strip()

    bound_match = re.match(r"(\d+)\+", cleaned)
    if bound_match:
        return int(bound_match.group(1))

    range_match = re.match(r"(\d+)\s*[-–]\s*(\d+)", cleaned)
    if range_match:
        lo, hi = int(range_match.group(1)), int(range_match.group(2))
        return (lo + hi) // 2

    exact_match = re.match(r"=?(\d+)", cleaned)
    if exact_match:
        return int(exact_match.group(1))

    return None


def deduplicate_rankings(rankings: list[dict]) -> list[dict]:
    """Remove duplicate ranking entries found in TopUniversities data.

    The TopUni scraper produces duplicates e.g. QS World appears twice
    with identical values. Keep only the first occurrence per ranking_type.
    """
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in rankings:
        key = r.get("ranking_type", "")
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    return deduped


def extract_rank_value(
    rankings: list[dict],
    ranking_type: str,
) -> Optional[int]:
    """Extract numeric rank for a specific ranking system.

    Uses the lower bound of ranges (conservative estimate).

    Args:
        rankings: List of ranking dicts from TopUniversities data.
        ranking_type: Name of the ranking system (use module-level constants).

    Returns:
        Integer rank (lower is better), or None if not present.
    """
    deduped = deduplicate_rankings(rankings)
    for r in deduped:
        if r.get("ranking_type", "") == ranking_type:
            rank = r.get("rank") or parse_rank(r.get("rank_display"))
            if rank and rank > 0:
                return rank
    return None


def normalize_rankings_array(rankings: list[dict]) -> list[dict]:
    """Clean and normalize the entire rankings array.

    Steps:
        1. Deduplicate entries by ranking_type.
        2. Parse rank_display into numeric `rank` where missing.
        3. Ensure `rank_display` is clean string.
    """
    deduped = deduplicate_rankings(rankings)
    result = []
    for r in deduped:
        entry = dict(r)
        # Parse numeric rank if not already populated
        if not entry.get("rank") and entry.get("rank_display"):
            entry["rank"] = parse_rank(entry["rank_display"])
        # Clean rank_display (strip extra whitespace)
        if entry.get("rank_display"):
            entry["rank_display"] = str(entry["rank_display"]).strip()
        result.append(entry)
    return result


def rank_to_percentile_score(rank: int, max_rank: int = 1500) -> float:
    """Convert rank to a 0-1 score where 1.0 = rank 1, 0.0 = rank >= max_rank.

    Used for multi-signal tier derivation.

    Args:
        rank: Numeric rank (lower is better).
        max_rank: The cap for the ranking system.

    Returns:
        Float in [0, 1].
    """
    if rank <= 0:
        return 0.0
    return max(0.0, 1.0 - (rank - 1) / max_rank)

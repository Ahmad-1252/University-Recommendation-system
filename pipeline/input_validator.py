"""
Input Validator — detect adversarial and nonsensical ML inputs.

Validates student profiles beyond basic type/range checking.
Catches semantically invalid combinations that could indicate:
  - API abuse / model probing
  - Data entry errors
  - Adversarial inputs designed to extract model boundaries
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# Budget sanity bounds (in USD)
MAX_REASONABLE_BUDGET = 200_000
MIN_REASONABLE_BUDGET = 100

# GPA bounds
MAX_GPA = 4.0
MIN_GPA = 0.0


def validate_student_profile(profile: Dict[str, Any]) -> List[str]:
    """Detect adversarial or nonsensical inputs in a student profile.

    Args:
        profile: student profile dict from API request.

    Returns:
        List of warning strings. Empty list = profile is clean.
    """
    warnings: List[str] = []

    gpa = profile.get("gpa")
    budget = profile.get("budget")
    countries = profile.get("preferred_countries", [])

    # High GPA + unrealistically low budget
    if gpa is not None and budget is not None:
        if gpa >= 3.8 and budget < 1000:
            warnings.append("suspicious: high GPA (≥3.8) with budget < $1000")

    # Unrealistically high budget
    if budget is not None and budget > MAX_REASONABLE_BUDGET:
        warnings.append(f"unrealistic: budget ${budget:,} exceeds ${MAX_REASONABLE_BUDGET:,}")

    # Zero or negative budget
    if budget is not None and budget <= 0:
        warnings.append("invalid: budget must be positive")

    # GPA out of range
    if gpa is not None and (gpa < MIN_GPA or gpa > MAX_GPA):
        warnings.append(f"invalid: GPA {gpa} outside [{MIN_GPA}, {MAX_GPA}]")

    # Too many countries (possible enumeration)
    if len(countries) > 10:
        warnings.append(f"suspicious: {len(countries)} preferred countries (max recommended: 10)")

    # Empty profile
    if not gpa and not budget and not countries:
        warnings.append("empty: no meaningful filters provided")

    return warnings


def check_rate_abuse(
    request_ip_hash: str,
    recent_requests: Dict[str, int],
    window_seconds: int = 60,
    max_requests: int = 20,
) -> bool:
    """Check if a client is making too many requests.

    Args:
        request_ip_hash: hashed IP address for privacy.
        recent_requests: dict mapping ip_hash → request count in window.
        window_seconds: time window for rate checking.
        max_requests: maximum allowed requests in window.

    Returns:
        True if the client should be throttled.
    """
    count = recent_requests.get(request_ip_hash, 0)
    return count > max_requests

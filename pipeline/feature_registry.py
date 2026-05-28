"""
Centralized Feature Registry — single source of truth for feature classification.

Every feature used in the ML pipeline is registered here with its type,
usage classification, and any constraints. This prevents:
  - Leaky features reaching the model
  - Training/inference feature set mismatch
  - Undocumented features entering the pipeline
"""

from typing import Dict, List, Set

# ── Feature Registry ──────────────────────────────────────────────────────────
# type: "numeric", "categorical", "text", "id"
# use:  "training" (used by ML model)
#       "display"  (returned in API response but not used for prediction)
#       "blocked"  (explicitly excluded — leaky or irrelevant)
#       "id"       (identifier — never used for training)

REGISTRY: Dict[str, Dict[str, str]] = {
    # ── Numeric training features ─────────────────────────────────────────
    "gpa_requirement_min":       {"type": "numeric",      "use": "training"},
    "tuition_domestic":          {"type": "numeric",      "use": "training"},
    "tuition_international":     {"type": "numeric",      "use": "training"},
    "tuition_domestic_usd":      {"type": "numeric",      "use": "training"},
    "tuition_international_usd": {"type": "numeric",      "use": "training"},
    "cost_of_living":            {"type": "numeric",      "use": "training"},
    "cost_of_living_usd":        {"type": "numeric",      "use": "training"},
    "ielts_min":                 {"type": "numeric",      "use": "training"},
    "toefl_min":                 {"type": "numeric",      "use": "training"},
    "duration_years":            {"type": "numeric",      "use": "training"},
    "application_fee":           {"type": "numeric",      "use": "training"},

    # ── Categorical training features ────────────────────────────────────
    "country":                   {"type": "categorical",  "use": "training"},
    "degree_level":              {"type": "categorical",  "use": "training"},
    "program_category":          {"type": "categorical",  "use": "training"},

    # ── Text training features ───────────────────────────────────────────
    "specializations":           {"type": "text",         "use": "training"},
    "career_outcomes":           {"type": "text",         "use": "training"},

    # ── Interaction features (computed at train/inference time) ───────────
    "affordability_ratio":       {"type": "numeric",      "use": "training"},
    "selectivity_index":         {"type": "numeric",      "use": "training"},

    # ── Display-only features ────────────────────────────────────────────
    "university_name":           {"type": "categorical",  "use": "display"},
    "program_name":              {"type": "categorical",  "use": "display"},
    "city":                      {"type": "categorical",  "use": "display"},
    "degree_type":               {"type": "categorical",  "use": "display"},
    "tuition_currency":          {"type": "categorical",  "use": "display"},

    # ── ID features ──────────────────────────────────────────────────────
    "university_id":             {"type": "id",           "use": "id"},

    # ── BLOCKED features — never used in training or inference ───────────
    # These are QS ranking-derived features that leak the target variable.
    "qs_world_ranking":          {"type": "numeric",      "use": "blocked", "reason": "leaky — QS rank determines tier directly"},
    "qs_overall_score":          {"type": "numeric",      "use": "blocked", "reason": "leaky — derived from QS rank"},
    "qs_academic_reputation":    {"type": "numeric",      "use": "blocked", "reason": "leaky — QS sub-score"},
    "qs_employer_reputation":    {"type": "numeric",      "use": "blocked", "reason": "leaky — QS sub-score"},
    "qs_faculty_student_ratio":  {"type": "numeric",      "use": "blocked", "reason": "leaky — QS sub-score"},
    "qs_citations":              {"type": "numeric",      "use": "blocked", "reason": "leaky — QS sub-score"},
    "qs_intl_students":          {"type": "numeric",      "use": "blocked", "reason": "leaky — QS sub-score"},
    "qs_intl_faculty":           {"type": "numeric",      "use": "blocked", "reason": "leaky — QS sub-score"},
    "qs_employment_outcomes":    {"type": "numeric",      "use": "blocked", "reason": "leaky — QS sub-score"},
    "qs_sustainability":         {"type": "numeric",      "use": "blocked", "reason": "leaky — QS sub-score"},

    # ── Target variable ──────────────────────────────────────────────────
    "university_tier":           {"type": "categorical",  "use": "target"},
}


def get_training_features() -> Set[str]:
    """Return set of feature names approved for training."""
    return {k for k, v in REGISTRY.items() if v["use"] == "training"}


def get_blocked_features() -> Set[str]:
    """Return set of feature names that must be excluded from training/inference."""
    return {k for k, v in REGISTRY.items() if v["use"] == "blocked"}


def get_display_features() -> Set[str]:
    """Return set of feature names for API response (not for prediction)."""
    return {k for k, v in REGISTRY.items() if v["use"] in ("display", "id")}


def get_target() -> str:
    """Return the target column name."""
    targets = [k for k, v in REGISTRY.items() if v["use"] == "target"]
    assert len(targets) == 1, f"Expected exactly 1 target, found {len(targets)}"
    return targets[0]


def validate_feature_set(columns: List[str]) -> Dict[str, List[str]]:
    """Validate a set of columns against the registry.

    Returns:
        dict with keys:
          - "approved": features in registry with use=training
          - "blocked_present": blocked features that should be removed
          - "unregistered": features not in the registry at all
    """
    approved = []
    blocked_present = []
    unregistered = []

    for col in columns:
        if col not in REGISTRY:
            unregistered.append(col)
        elif REGISTRY[col]["use"] == "blocked":
            blocked_present.append(col)
        elif REGISTRY[col]["use"] == "training":
            approved.append(col)

    return {
        "approved": approved,
        "blocked_present": blocked_present,
        "unregistered": unregistered,
    }

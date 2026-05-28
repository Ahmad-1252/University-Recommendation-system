"""
Regression tests for Phase 1 bug fixes.

Tests verify:
  1. _build_similarity_matrix() drops QS leaky features
  2. score_program() drops QS leaky features before prediction
  3. match_score uses canonical weights (1.0/0.6/0.2) everywhere
  4. pipeline.scoring module produces correct outputs
"""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

# ── Setup project root ──────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 1: pipeline.scoring module correctness
# ═══════════════════════════════════════════════════════════════════════════════


class TestScoringModule:
    """Test the canonical scoring module."""

    def test_weights_are_canonical(self):
        """TIER_WEIGHTS must be exactly {top: 1.0, good: 0.6, standard: 0.2}."""
        from pipeline.scoring import TIER_WEIGHTS

        assert TIER_WEIGHTS == {"top": 1.0, "good": 0.6, "standard": 0.2}

    def test_compute_match_score_all_top(self):
        """If P(top)=1.0 → match_score = 1.0."""
        from pipeline.scoring import compute_match_score

        proba = np.array([0.0, 0.0, 1.0])  # good=0, standard=0, top=1
        classes = ["good", "standard", "top"]
        assert compute_match_score(proba, classes) == pytest.approx(1.0)

    def test_compute_match_score_all_standard(self):
        """If P(standard)=1.0 → match_score = 0.2."""
        from pipeline.scoring import compute_match_score

        proba = np.array([0.0, 1.0, 0.0])  # good=0, standard=1, top=0
        classes = ["good", "standard", "top"]
        assert compute_match_score(proba, classes) == pytest.approx(0.2)

    def test_compute_match_score_all_good(self):
        """If P(good)=1.0 → match_score = 0.6."""
        from pipeline.scoring import compute_match_score

        proba = np.array([1.0, 0.0, 0.0])
        classes = ["good", "standard", "top"]
        assert compute_match_score(proba, classes) == pytest.approx(0.6)

    def test_compute_match_score_uniform(self):
        """Uniform distribution → weighted average = (1.0+0.6+0.2)/3 = 0.6."""
        from pipeline.scoring import compute_match_score

        proba = np.array([1 / 3, 1 / 3, 1 / 3])
        classes = ["good", "standard", "top"]
        expected = (1.0 / 3 * 0.6) + (1.0 / 3 * 0.2) + (1.0 / 3 * 1.0)
        assert compute_match_score(proba, classes) == pytest.approx(expected)

    def test_compute_match_score_clipped(self):
        """Score should never exceed 1.0 even with unusual probabilities."""
        from pipeline.scoring import compute_match_score

        proba = np.array([0.5, 0.5, 0.5])  # intentionally sums > 1
        classes = ["good", "standard", "top"]
        assert compute_match_score(proba, classes) <= 1.0

    def test_batch_consistency(self):
        """Batch and single-item scoring must produce identical results."""
        from pipeline.scoring import (
            compute_match_score,
            compute_match_scores_batch,
        )

        classes = ["good", "standard", "top"]
        probas = np.array(
            [
                [0.1, 0.2, 0.7],
                [0.8, 0.1, 0.1],
                [0.33, 0.34, 0.33],
            ]
        )

        batch = compute_match_scores_batch(probas, classes)
        singles = [compute_match_score(row, classes) for row in probas]

        for b, s in zip(batch, singles):
            assert b == pytest.approx(s, abs=1e-10)

    def test_confidence_band_high(self):
        from pipeline.scoring import compute_confidence_band

        assert compute_confidence_band(np.array([0.05, 0.10, 0.85])) == "high"

    def test_confidence_band_medium(self):
        from pipeline.scoring import compute_confidence_band

        assert compute_confidence_band(np.array([0.20, 0.25, 0.55])) == "medium"

    def test_confidence_band_low(self):
        from pipeline.scoring import compute_confidence_band

        assert compute_confidence_band(np.array([0.35, 0.35, 0.30])) == "low"

    def test_confidence_bands_batch(self):
        from pipeline.scoring import (
            compute_confidence_band,
            compute_confidence_bands_batch,
        )

        probas = np.array(
            [
                [0.05, 0.10, 0.85],
                [0.20, 0.25, 0.55],
                [0.35, 0.35, 0.30],
            ]
        )
        batch = compute_confidence_bands_batch(probas)
        singles = [compute_confidence_band(row) for row in probas]
        for b, s in zip(batch, singles):
            assert b == s


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 2: QS leaky features must never reach the pipeline
# ═══════════════════════════════════════════════════════════════════════════════


class TestLeakyFeatureExclusion:
    """Verify QS features are dropped in all code paths."""

    QS_FEATURES = {
        "qs_world_ranking",
        "qs_overall_score",
        "qs_academic_reputation",
        "qs_employer_reputation",
        "qs_faculty_student_ratio",
        "qs_citations",
        "qs_intl_students",
        "qs_intl_faculty",
        "qs_employment_outcomes",
        "qs_sustainability",
    }

    def test_recommendation_service_imports_scoring(self):
        """recommendation_service.py must import from pipeline.scoring."""
        src = Path(PROJECT_ROOT / "src" / "services" / "recommendation_service.py")
        content = src.read_text()
        assert (
            "from pipeline.scoring import" in content
        ), "recommendation_service.py must import canonical scoring"

    def test_recommendation_service_no_inline_weights(self):
        """No inline weight constants (0.5 * proba or 0.1 * proba) should remain."""
        src = Path(PROJECT_ROOT / "src" / "services" / "recommendation_service.py")
        content = src.read_text()
        # These patterns indicate the old inline scoring
        assert "0.5 * proba" not in content, "Old 0.5 weight found"
        assert "0.1 * proba" not in content, "Old 0.1 weight found"
        assert "+ 0.5 *" not in content, "Old inline scoring pattern found"

    def test_retrain_model_no_inline_weights(self):
        """retrain_model.py must not contain old inline scoring weights."""
        src = Path(PROJECT_ROOT / "scripts" / "retrain_model.py")
        content = src.read_text()
        assert (
            "* 0.5" not in content.split("scored_programs")[0]
            or "compute_match_scores_batch" in content
        ), "retrain_model.py still has inline scoring"

    def test_similarity_matrix_drops_leaky_features(self):
        """_build_similarity_matrix() must reference leaky_features_removed."""
        src = Path(PROJECT_ROOT / "src" / "services" / "recommendation_service.py")
        content = src.read_text()
        # Find the _build_similarity_matrix method
        sim_start = content.find("def _build_similarity_matrix")
        sim_end = content.find("def find_similar")
        sim_method = content[sim_start:sim_end]
        assert (
            "leaky_features" in sim_method
        ), "_build_similarity_matrix() must drop leaky features"
        assert (
            "QS_LEAKY_FEATURES" in sim_method
        ), "_build_similarity_matrix() must reference QS_LEAKY_FEATURES"

    def test_score_program_drops_leaky_features(self):
        """score_program() must drop leaky features before prediction."""
        src = Path(PROJECT_ROOT / "src" / "services" / "recommendation_service.py")
        content = src.read_text()
        # Find the score_program method
        sp_start = content.find("def score_program")
        sp_end = content.find("def get_model_info")
        sp_method = content[sp_start:sp_end]
        assert (
            "QS_LEAKY_FEATURES" in sp_method
        ), "score_program() must reference QS_LEAKY_FEATURES"
        assert "drop" in sp_method.lower(), "score_program() must drop leaky columns"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST GROUP 3: Model metadata integrity
# ═══════════════════════════════════════════════════════════════════════════════


class TestModelMetadata:
    """Verify model_metadata.json records leakage removal."""

    def test_metadata_records_leaky_features(self):
        meta_path = PROJECT_ROOT / "model_artifacts" / "model_metadata.json"
        if not meta_path.exists():
            pytest.skip("model_metadata.json not found")
        with open(meta_path) as f:
            meta = json.load(f)
        assert "leaky_features_removed" in meta
        assert len(meta["leaky_features_removed"]) >= 9

    def test_metadata_leakage_check_passed(self):
        meta_path = PROJECT_ROOT / "model_artifacts" / "model_metadata.json"
        if not meta_path.exists():
            pytest.skip("model_metadata.json not found")
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta.get("leakage_check_passed") is True

    def test_metadata_accuracy_not_perfect(self):
        meta_path = PROJECT_ROOT / "model_artifacts" / "model_metadata.json"
        if not meta_path.exists():
            pytest.skip("model_metadata.json not found")
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["metrics"]["accuracy"] < 1.0, "Perfect accuracy indicates leakage"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

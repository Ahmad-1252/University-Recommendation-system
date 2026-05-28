"""ML Recommendation Service — loads model and serves predictions."""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

# Add project root to path so pipeline package is importable
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from pipeline.scoring import (
    compute_confidence_band,
    compute_confidence_bands_batch,
    compute_match_score,
    compute_match_scores_batch,
)

logger = logging.getLogger(__name__)

# Path to model artifacts (relative to project root)
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent.parent / "model_artifacts"

# L1-L3: Features that were removed from training due to target leakage.
# Must also be dropped during inference so the feature set matches the trained pipeline.
QS_LEAKY_FEATURES = {
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


class RecommendationService:
    """
    ML-powered recommendation service.

    Loads the trained pipeline once and exposes:
      - recommend(profile) → scored program list
      - find_similar(program_idx, top_n) → similar programs
      - score_single(program_dict) → tier + match_score
      - get_model_info() → metadata dict
    """

    def __init__(self, artifacts_dir: Optional[Path] = None):
        self.artifacts_dir = artifacts_dir or ARTIFACTS_DIR
        self.pipeline = None
        self.label_encoder = None
        self.metadata: Dict[str, Any] = {}
        self._programs_df: Optional[pd.DataFrame] = None
        self._sim_matrix: Optional[np.ndarray] = None
        self._sim_sample: Optional[pd.DataFrame] = None
        self._loaded = False

    # ─── Startup ─────────────────────────────────────────────

    def load(self) -> bool:
        """Load model artifacts from disk. Call once at app startup."""
        try:
            pipeline_path = self.artifacts_dir / "model_pipeline.joblib"
            le_path = self.artifacts_dir / "label_encoder.joblib"
            meta_path = self.artifacts_dir / "model_metadata.json"

            if not pipeline_path.exists():
                logger.error(f"Model pipeline not found: {pipeline_path}")
                return False

            self.pipeline = joblib.load(pipeline_path)
            logger.info(
                f"Loaded model pipeline ({pipeline_path.stat().st_size / 1024:.0f} KB)"
            )

            if le_path.exists():
                self.label_encoder = joblib.load(le_path)
                logger.info(
                    f"Loaded label encoder: {list(self.label_encoder.classes_)}"
                )

            if meta_path.exists():
                with open(meta_path) as f:
                    self.metadata = json.load(f)
                logger.info(
                    f"Loaded metadata: {self.metadata.get('model_backend', 'unknown')}"
                )

            self._loaded = True
            return True

        except Exception as e:
            logger.error(f"Failed to load model artifacts: {e}", exc_info=True)
            return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self.pipeline is not None

    # ─── Data Loading ────────────────────────────────────────

    def load_programs_dataframe(self, df: Optional[pd.DataFrame] = None) -> int:
        """
        Load program data for recommendations.
        Accepts a DataFrame or loads from scored_programs.csv.
        Returns number of programs loaded.
        """
        if df is not None:
            self._programs_df = df.copy()
        else:
            # Prefer the original training data (has correct columns for the model)
            # over scored_programs.csv (may be from a different model version).
            search_paths = [
                Path("data/exports/training_dataset_latest.csv"),
                Path("data/universities.csv"),
                self.artifacts_dir / "scored_programs.csv",
            ]
            for p in search_paths:
                if p.exists():
                    self._programs_df = pd.read_csv(p)
                    logger.info(f"Loaded {len(self._programs_df)} programs from {p}")
                    break

        if self._programs_df is None:
            logger.warning("No programs data available for recommendations")
            return 0

        return len(self._programs_df)

    def _get_programs(self) -> pd.DataFrame:
        """Get programs DataFrame, loading if needed."""
        if self._programs_df is None:
            self.load_programs_dataframe()
        if self._programs_df is None:
            raise RuntimeError(
                "No programs data loaded. Call load_programs_dataframe() first."
            )
        return self._programs_df

    # ─── Content-Based Recommendations ───────────────────────

    def recommend(self, profile: Dict[str, Any], top_n: int = 10) -> Dict[str, Any]:
        """
        Content-based recommendation from a student profile.

        Args:
            profile: dict with keys gpa, ielts, toefl, budget,
                     preferred_country, degree_level, program_category
            top_n: number of results

        Returns:
            dict with recommendations, total_candidates, filters_applied
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        programs = self._get_programs()
        candidates = programs.copy()
        filters = {}

        # ── Hard filters ──
        gpa = profile.get("gpa")
        if gpa and "gpa_requirement_min" in candidates.columns:
            candidates = candidates[candidates["gpa_requirement_min"] <= gpa]
            filters["gpa"] = gpa

        ielts = profile.get("ielts")
        if ielts and "ielts_min" in candidates.columns:
            candidates = candidates[candidates["ielts_min"] <= ielts]
            filters["ielts"] = ielts

        toefl = profile.get("toefl")
        if toefl and "toefl_min" in candidates.columns:
            candidates = candidates[candidates["toefl_min"] <= toefl]
            filters["toefl"] = toefl

        budget = profile.get("budget")
        if budget and "tuition_international" in candidates.columns:
            candidates = candidates[candidates["tuition_international"] <= budget]
            filters["budget"] = budget

        country = profile.get("preferred_country")
        if country and "country" in candidates.columns:
            candidates = candidates[candidates["country"] == country]
            filters["country"] = country

        level = profile.get("degree_level")
        if level and "degree_level" in candidates.columns:
            candidates = candidates[candidates["degree_level"] == level]
            filters["degree_level"] = level

        category = profile.get("program_category")
        if category and "program_category" in candidates.columns:
            candidates = candidates[candidates["program_category"] == category]
            filters["program_category"] = category

        total_candidates = len(candidates)

        if total_candidates == 0:
            return {
                "recommendations": [],
                "total_candidates": 0,
                "filters_applied": filters,
                "model_backend": self.metadata.get("model_backend", "unknown"),
            }

        # ── Score with ML model ──
        target_col = self.metadata.get("target_column", "university_tier")
        id_features = self.metadata.get("id_features", [])
        leaky_features = self.metadata.get("leaky_features_removed", [])
        drop_cols = [target_col] + id_features + leaky_features
        # Also drop any QS features not explicitly listed in metadata
        drop_cols += [c for c in QS_LEAKY_FEATURES if c in candidates.columns]
        drop_cols = list(set(drop_cols))  # deduplicate
        X_cand = candidates.drop(
            columns=[c for c in drop_cols if c in candidates.columns],
            errors="ignore",
        )

        try:
            proba = self.pipeline.predict_proba(X_cand)
            classes = list(self.label_encoder.classes_)

            # Canonical scoring from pipeline.scoring (single source of truth)
            match_scores = compute_match_scores_batch(proba, classes)
            predicted_tiers = self.label_encoder.inverse_transform(proba.argmax(axis=1))
            confidence_bands = compute_confidence_bands_batch(proba)

        except Exception as e:
            logger.error(f"Model prediction failed: {e}")
            match_scores = np.full(len(candidates), 0.5)
            predicted_tiers = ["unknown"] * len(candidates)
            confidence_bands = np.full(len(candidates), "low")

        candidates = candidates.copy()
        candidates["match_score"] = match_scores
        candidates["predicted_tier"] = predicted_tiers
        candidates["confidence_band"] = confidence_bands

        # Sort and take top_n
        top = candidates.sort_values("match_score", ascending=False).head(top_n)

        # Build response
        recommendations = []
        for _, row in top.iterrows():
            rec = {
                "university_name": str(row.get("university_name", "Unknown")),
                "program_name": str(row.get("program_name", "")) or None,
                "country": str(row.get("country", "")) or None,
                "degree_level": str(row.get("degree_level", "")) or None,
                "program_category": str(row.get("program_category", "")) or None,
                "qs_world_ranking": int(row["qs_world_ranking"])
                if pd.notnull(row.get("qs_world_ranking"))
                else None,
                "tuition_international": float(row["tuition_international"])
                if pd.notnull(row.get("tuition_international"))
                else None,
                "match_score": round(float(row["match_score"]), 4),
                "predicted_tier": str(row["predicted_tier"]),
                "confidence_band": str(row["confidence_band"]),
            }
            recommendations.append(rec)

        return {
            "recommendations": recommendations,
            "total_candidates": total_candidates,
            "filters_applied": filters,
            "model_backend": self.metadata.get("model_backend", "unknown"),
        }

    # ─── Item-to-Item Similarity ─────────────────────────────

    def _build_similarity_matrix(self, max_programs: int = 5000):
        """Pre-compute cosine similarity matrix."""
        programs = self._get_programs()
        sample = programs.head(max_programs).copy()

        # BUG FIX: Drop leaky features from similarity computation
        # (was missing — QS features leaked into cosine similarity)
        target_col = self.metadata.get("target_column", "university_tier")
        id_features = self.metadata.get("id_features", [])
        leaky_features = self.metadata.get("leaky_features_removed", [])
        drop_cols = [target_col] + id_features + leaky_features
        drop_cols += [c for c in QS_LEAKY_FEATURES if c in sample.columns]
        drop_cols = list(set(drop_cols))
        X_sim = sample.drop(
            columns=[c for c in drop_cols if c in sample.columns], errors="ignore"
        )

        X_transformed = self.pipeline.named_steps["preprocessor"].transform(X_sim)
        if hasattr(X_transformed, "toarray"):
            X_transformed = X_transformed.toarray()

        self._sim_matrix = cosine_similarity(X_transformed)
        self._sim_sample = sample
        logger.info(f"Built similarity matrix: {self._sim_matrix.shape}")

    def find_similar(self, program_idx: int, top_n: int = 10) -> Dict[str, Any]:
        """
        Find programs similar to the given program index.

        Args:
            program_idx: row index of the query program
            top_n: number of similar programs to return

        Returns:
            dict with query_program and similar_programs
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        if self._sim_matrix is None:
            self._build_similarity_matrix()

        if program_idx >= len(self._sim_matrix):
            raise ValueError(
                f"Index {program_idx} out of range (max {len(self._sim_matrix) - 1})"
            )

        similarities = self._sim_matrix[program_idx]
        top_indices = np.argsort(similarities)[::-1][1 : top_n + 1]

        query = self._sim_sample.iloc[program_idx]
        result_df = self._sim_sample.iloc[top_indices].copy()
        result_df["similarity_score"] = similarities[top_indices]

        display_cols = [
            c
            for c in [
                "university_name",
                "program_name",
                "degree_level",
                "program_category",
                "country",
                "qs_world_ranking",
                "tuition_international",
                "similarity_score",
            ]
            if c in result_df.columns
        ]

        query_info = {
            c: _safe_val(query.get(c)) for c in display_cols if c != "similarity_score"
        }
        similar = [
            {c: _safe_val(row.get(c)) for c in display_cols}
            for _, row in result_df[display_cols].iterrows()
        ]

        return {
            "query_program": query_info,
            "similar_programs": similar,
            "similarity_method": "cosine",
        }

    # ─── Single Program Scoring ──────────────────────────────

    def score_program(self, program: Dict[str, Any]) -> Dict[str, Any]:
        """Score a single program and return tier + match_score."""
        if not self.is_loaded:
            raise RuntimeError("Model not loaded.")

        # BUG FIX: Drop leaky features before prediction
        # (was missing — QS features passed directly to pipeline)
        row = pd.DataFrame([program])
        leaky = list(QS_LEAKY_FEATURES) + self.metadata.get(
            "leaky_features_removed", []
        )
        id_cols = self.metadata.get("id_features", [])
        target_col = self.metadata.get("target_column", "university_tier")
        drop = list(set(leaky + id_cols + [target_col]))
        row = row.drop(columns=[c for c in drop if c in row.columns], errors="ignore")

        proba = self.pipeline.predict_proba(row)[0]
        classes = list(self.label_encoder.classes_)

        # BUG FIX: Use canonical scoring (was using old 1.0/0.5/0.1 weights)
        return {
            "predicted_tier": classes[proba.argmax()],
            "match_score": round(compute_match_score(proba, classes), 4),
            "confidence_band": compute_confidence_band(proba),
            "probabilities": {c: round(float(p), 4) for c, p in zip(classes, proba)},
        }

    # ─── Model Info ──────────────────────────────────────────

    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata for the /api/model/info endpoint."""
        return {
            "model_backend": self.metadata.get("model_backend", "unknown"),
            "target_column": self.metadata.get("target_column", "university_tier"),
            "class_names": self.metadata.get("class_names", []),
            "metrics": self.metadata.get("metrics", {}),
            "dataset_shape": self.metadata.get("dataset_shape", []),
            "training_time_seconds": self.metadata.get("training_time_seconds", 0),
            "numeric_features": self.metadata.get("numeric_features", []),
            "categorical_features": self.metadata.get("categorical_features", []),
            "created_at": self.metadata.get("created_at", ""),
        }


def _safe_val(v):
    """Convert numpy/pandas types to JSON-safe Python types."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return round(float(v), 4)
    if isinstance(v, np.bool_):
        return bool(v)
    return v

"""
Drift Detector — monitors for feature and prediction distribution drift.

Compares a new dataset (production inference data) against the training
baseline to detect data drift using Population Stability Index (PSI)
and feature-level Kolmogorov-Smirnov tests.

When drift is detected, an alert is raised and the model should be
retrained with fresh data.

Usage:
    from mlops.drift_detector import DriftDetector

    detector = DriftDetector.from_training_data("data/exports/training_dataset_latest.csv")
    report = detector.check_drift(new_data_df)
    if report.drift_detected:
        print(report.summary())
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class DriftReport:
    """Results from a drift detection analysis."""
    drift_detected: bool = False
    overall_psi: float = 0.0
    feature_drift: Dict[str, Dict] = field(default_factory=dict)
    prediction_drift: Dict[str, float] = field(default_factory=dict)
    drifted_features: List[str] = field(default_factory=list)
    timestamp: str = ""

    def summary(self) -> str:
        status = "⚠️ DRIFT DETECTED" if self.drift_detected else "✅ NO DRIFT"
        lines = [
            f"{status}",
            f"Overall PSI: {self.overall_psi:.4f}",
            f"Drifted features ({len(self.drifted_features)}):",
        ]
        for feat in self.drifted_features[:10]:
            info = self.feature_drift.get(feat, {})
            lines.append(
                f"  - {feat}: PSI={info.get('psi', 0):.4f}, "
                f"KS p-value={info.get('ks_pvalue', 1):.4f}"
            )
        return "\n".join(lines)


def _compute_psi(
    expected: np.ndarray,
    actual: np.ndarray,
    n_bins: int = 10,
    epsilon: float = 1e-4,
) -> float:
    """
    Population Stability Index (PSI) between two distributions.

    PSI < 0.10: No significant change
    PSI 0.10-0.25: Moderate drift — investigate
    PSI > 0.25: Significant drift — retrain

    Args:
        expected: Baseline distribution (training data).
        actual: New distribution (production data).
        n_bins: Number of histogram bins.
        epsilon: Small value to avoid division by zero.

    Returns:
        PSI value (unbounded, >= 0).
    """
    # Create bins from the expected distribution
    breakpoints = np.percentile(expected, np.linspace(0, 100, n_bins + 1))
    breakpoints = np.unique(breakpoints)

    if len(breakpoints) < 2:
        return 0.0

    # Compute bin proportions
    expected_counts = np.histogram(expected, bins=breakpoints)[0].astype(float)
    actual_counts = np.histogram(actual, bins=breakpoints)[0].astype(float)

    # Normalize to proportions
    expected_pct = expected_counts / (expected_counts.sum() + epsilon)
    actual_pct = actual_counts / (actual_counts.sum() + epsilon)

    # Add epsilon to avoid log(0)
    expected_pct = np.clip(expected_pct, epsilon, 1)
    actual_pct = np.clip(actual_pct, epsilon, 1)

    # PSI formula
    psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
    return float(psi)


class DriftDetector:
    """
    Detects data drift by comparing feature distributions.

    Stores baseline statistics from training data and compares
    against new data to detect distribution changes.
    """

    def __init__(
        self,
        baseline_stats: Dict[str, Dict],
        psi_threshold: float = 0.20,
        ks_alpha: float = 0.01,
    ):
        """
        Args:
            baseline_stats: Dict mapping feature_name → {mean, std, min, max, values}.
            psi_threshold: PSI threshold for drift detection (default 0.20).
            ks_alpha: KS test significance level (default 0.01).
        """
        self.baseline_stats = baseline_stats
        self.psi_threshold = psi_threshold
        self.ks_alpha = ks_alpha

    @classmethod
    def from_training_data(
        cls,
        csv_path: str,
        numeric_features: Optional[List[str]] = None,
        sample_size: int = 10000,
        **kwargs,
    ) -> "DriftDetector":
        """
        Create a DriftDetector from a training dataset CSV.

        Computes baseline statistics for all numeric features.

        Args:
            csv_path: Path to training CSV.
            numeric_features: List of numeric feature names to track.
                If None, auto-detects numeric columns.
            sample_size: Max number of values to store per feature
                (for PSI computation).
        """
        df = pd.read_csv(csv_path)
        logger.info(f"Building drift baseline from {csv_path} ({len(df)} rows)")

        if numeric_features is None:
            numeric_features = df.select_dtypes(include=[np.number]).columns.tolist()

        baseline_stats = {}
        for col in numeric_features:
            if col not in df.columns:
                continue
            values = df[col].dropna().values
            if len(values) == 0:
                continue

            # Sample if too large
            if len(values) > sample_size:
                rng = np.random.RandomState(42)
                values = rng.choice(values, size=sample_size, replace=False)

            baseline_stats[col] = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "median": float(np.median(values)),
                "n_samples": int(len(values)),
                "values": values.tolist(),  # stored for PSI computation
            }

        logger.info(f"Drift baseline computed for {len(baseline_stats)} features")
        return cls(baseline_stats, **kwargs)

    def check_drift(
        self,
        new_data: pd.DataFrame,
        prediction_col: Optional[str] = None,
    ) -> DriftReport:
        """
        Check for drift between baseline and new data.

        Runs PSI and KS tests on each tracked feature.

        Args:
            new_data: DataFrame with new/production data.
            prediction_col: Optional column with model predictions to check.

        Returns:
            DriftReport with all findings.
        """
        from datetime import datetime

        report = DriftReport(timestamp=datetime.now().isoformat())

        psi_values = []

        for feat_name, baseline in self.baseline_stats.items():
            if feat_name not in new_data.columns:
                continue

            new_values = new_data[feat_name].dropna().values
            if len(new_values) == 0:
                continue

            baseline_values = np.array(baseline["values"])

            # PSI
            psi = _compute_psi(baseline_values, new_values)
            psi_values.append(psi)

            # KS test
            ks_stat, ks_pvalue = stats.ks_2samp(baseline_values, new_values)

            # Mean shift
            mean_shift = abs(np.mean(new_values) - baseline["mean"]) / (baseline["std"] + 1e-8)

            feature_result = {
                "psi": round(psi, 4),
                "ks_statistic": round(float(ks_stat), 4),
                "ks_pvalue": round(float(ks_pvalue), 6),
                "mean_shift_sigma": round(float(mean_shift), 2),
                "baseline_mean": baseline["mean"],
                "new_mean": round(float(np.mean(new_values)), 4),
                "drift_detected": psi > self.psi_threshold or ks_pvalue < self.ks_alpha,
            }

            report.feature_drift[feat_name] = feature_result

            if feature_result["drift_detected"]:
                report.drifted_features.append(feat_name)

        # Overall PSI (average across features)
        report.overall_psi = float(np.mean(psi_values)) if psi_values else 0.0

        # Prediction distribution drift
        if prediction_col and prediction_col in new_data.columns:
            pred_values = new_data[prediction_col].value_counts(normalize=True).to_dict()
            report.prediction_drift = {str(k): round(v, 4) for k, v in pred_values.items()}

        # Set overall drift flag
        report.drift_detected = len(report.drifted_features) > 0

        if report.drift_detected:
            logger.warning(
                f"DATA DRIFT DETECTED in {len(report.drifted_features)} features: "
                f"{report.drifted_features[:5]}"
            )
        else:
            logger.info("No data drift detected")

        return report

    def save_baseline(self, path: str = "mlops/drift_baseline.json") -> None:
        """Save baseline statistics to JSON for persistence."""
        # Remove values arrays (too large for JSON) and keep summary stats
        save_stats = {}
        for feat, stats_dict in self.baseline_stats.items():
            save_stats[feat] = {k: v for k, v in stats_dict.items() if k != "values"}

        filepath = Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(save_stats, f, indent=2)
        logger.info(f"Drift baseline saved: {filepath}")

    @classmethod
    def from_baseline_file(cls, path: str = "mlops/drift_baseline.json", **kwargs) -> "DriftDetector":
        """Load a DriftDetector from a saved baseline file."""
        with open(path) as f:
            stats = json.load(f)
        return cls(stats, **kwargs)

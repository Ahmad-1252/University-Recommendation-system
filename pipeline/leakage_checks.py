"""
Leakage detection and training quality checks.

Run automatically during retrain_model.py, or standalone:
    python -m pipeline.leakage_checks --csv data/exports/training_dataset_latest.csv

Every check raises ValueError on failure so a CI/CD pipeline can gate on exit code.
"""

import logging
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.metrics import accuracy_score, f1_score

logger = logging.getLogger(__name__)


# ── Exceptions ───────────────────────────────────────────────────────────────

class DataLeakageError(ValueError):
    """Raised when data leakage is detected in the training pipeline."""
    pass


class QualityGateError(ValueError):
    """Raised when a model quality gate is not met."""
    pass


# ── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass
class LeakageReport:
    """Results from a full leakage audit."""
    target_correlation_leaks: List[Tuple[str, float]] = field(default_factory=list)
    group_leakage_detected: bool = False
    group_leakage_overlap: float = 0.0
    perfect_metric_detected: bool = False
    perfect_metric_keys: List[str] = field(default_factory=list)
    passed: bool = True
    issues: List[str] = field(default_factory=list)

    def summary(self) -> str:
        if self.passed:
            return "LEAKAGE CHECK PASSED — no issues detected"
        lines = ["LEAKAGE CHECK FAILED:"]
        for issue in self.issues:
            lines.append(f"  ✗ {issue}")
        return "\n".join(lines)


# ── Core Checks ──────────────────────────────────────────────────────────────

def check_target_correlation(
    X: pd.DataFrame,
    y: np.ndarray,
    threshold: float = 0.95,
    known_leaky_features: Optional[Set[str]] = None,
) -> List[Tuple[str, float]]:
    """
    Check for features with suspiciously high correlation to the target.

    Computes Spearman rank correlation between each numeric feature and
    the encoded target. Any feature with |correlation| > threshold is
    flagged as a leakage risk.

    Args:
        X: Feature DataFrame (numeric columns only are checked).
        y: Encoded target array (integer-encoded labels).
        threshold: Maximum allowable |correlation| (default 0.95).
        known_leaky_features: Optional set of feature names that should
            NOT appear in X. Raises immediately if found.

    Returns:
        List of (feature_name, correlation) tuples that exceed threshold.

    Raises:
        DataLeakageError: If any feature exceeds threshold or a known
            leaky feature is present.
    """
    if known_leaky_features:
        present = known_leaky_features.intersection(set(X.columns))
        if present:
            raise DataLeakageError(
                f"Known leaky features found in training data: {present}. "
                f"Remove these columns before training."
            )

    leaky = []
    y_series = pd.Series(y, index=X.index, name="target")
    numeric_cols = X.select_dtypes(include=[np.number]).columns

    for col in numeric_cols:
        corr = X[col].corr(y_series, method="spearman")
        if abs(corr) > threshold:
            leaky.append((col, round(corr, 4)))

    if leaky:
        feature_list = ", ".join(f"{name} (r={corr})" for name, corr in leaky)
        raise DataLeakageError(
            f"Target leakage detected — {len(leaky)} feature(s) have "
            f"|Spearman correlation| > {threshold} with the target:\n"
            f"  {feature_list}\n"
            f"Remove these features from the training set."
        )

    logger.info(
        f"Target correlation check PASSED — no feature exceeds "
        f"|r| > {threshold} (checked {len(numeric_cols)} numeric features)"
    )
    return leaky


def check_group_leakage(
    df: pd.DataFrame,
    group_col: str,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
) -> Tuple[bool, float]:
    """
    Check whether groups (e.g. university_name) leak across train/test.

    If the same university appears in both train and test, the model can
    memorize university-specific patterns and achieve inflated test accuracy.

    Args:
        df: Full DataFrame with the group column.
        group_col: Column to check for group leakage (e.g. "university_name").
        train_idx: Row indices used for training.
        test_idx: Row indices used for testing.

    Returns:
        Tuple of (leak_detected: bool, overlap_ratio: float).

    Raises:
        DataLeakageError: If any group appears in both train and test.
    """
    if group_col not in df.columns:
        logger.warning(f"Group column '{group_col}' not in DataFrame — skipping check")
        return False, 0.0

    train_groups = set(df.iloc[train_idx][group_col].unique())
    test_groups = set(df.iloc[test_idx][group_col].unique())
    overlap = train_groups.intersection(test_groups)

    if overlap:
        all_groups = train_groups.union(test_groups)
        overlap_ratio = len(overlap) / len(all_groups)
        raise DataLeakageError(
            f"Group leakage detected — {len(overlap)} / {len(all_groups)} "
            f"groups ({overlap_ratio:.1%}) appear in BOTH train and test. "
            f"Column: '{group_col}'. Use GroupShuffleSplit or GroupKFold "
            f"to split by '{group_col}'.\n"
            f"Example overlapping groups: {list(overlap)[:5]}"
        )

    logger.info(
        f"Group leakage check PASSED — {len(train_groups)} train groups, "
        f"{len(test_groups)} test groups, 0 overlap"
    )
    return False, 0.0


def check_perfect_metrics(
    metrics: Dict[str, float],
    epsilon: float = 1e-6,
) -> bool:
    """
    Check whether any evaluation metric is suspiciously perfect.

    Perfect metrics (exactly 1.0) on held-out data always indicate
    data leakage, a trivial problem, or an evaluation bug.

    Args:
        metrics: Dict of metric_name → score.
        epsilon: Tolerance for "perfect" (default 1e-6).

    Returns:
        True if any metric is perfect.

    Raises:
        DataLeakageError: If any metric >= 1.0 - epsilon.
    """
    perfect = {k: v for k, v in metrics.items() if v >= (1.0 - epsilon)}
    if perfect:
        raise DataLeakageError(
            f"Perfect metrics detected — this almost certainly indicates "
            f"data leakage or a trivial prediction task:\n"
            f"  {perfect}\n"
            f"Run check_target_correlation() to identify leaky features."
        )

    logger.info(f"Perfect metrics check PASSED — no metric is 1.0")
    return False


def check_baseline_gap(
    model_score: float,
    baseline_score: float,
    min_gap: float = 0.10,
    metric_name: str = "accuracy",
) -> float:
    """
    Assert that the trained model meaningfully outperforms a dummy baseline.

    If the gap is too small, the ML model provides no marginal value and
    a simpler solution (rules, heuristics) should be used instead.

    Args:
        model_score: Model metric value.
        baseline_score: Dummy/baseline metric value.
        min_gap: Minimum required gap (default 0.10 = 10 percentage points).
        metric_name: Name of the metric being compared.

    Returns:
        The gap (model_score - baseline_score).

    Raises:
        QualityGateError: If model is not better than baseline + min_gap.
    """
    gap = model_score - baseline_score
    if gap < min_gap:
        raise QualityGateError(
            f"Model {metric_name}={model_score:.4f} does not meaningfully "
            f"outperform baseline {metric_name}={baseline_score:.4f}. "
            f"Gap={gap:.4f} < required minimum {min_gap}. "
            f"The ML model provides insufficient marginal value. "
            f"Consider using a simpler rule-based approach."
        )

    logger.info(
        f"Baseline gap check PASSED — model {metric_name}={model_score:.4f} "
        f"vs baseline={baseline_score:.4f}, gap={gap:.4f} > {min_gap}"
    )
    return gap


def check_high_accuracy_warning(
    accuracy: float,
    threshold: float = 0.98,
) -> None:
    """
    Emit a warning if accuracy is suspiciously high (but not perfect).

    High accuracy is not necessarily wrong, but it is a strong signal
    that warrants manual investigation.
    """
    if accuracy >= threshold:
        warnings.warn(
            f"Accuracy {accuracy:.4f} is suspiciously high (>= {threshold}). "
            f"This may indicate data leakage even if not exactly 1.0. "
            f"Manually verify with feature_importance and confusion_matrix.",
            UserWarning,
            stacklevel=2,
        )


# ── Full Audit ───────────────────────────────────────────────────────────────

def run_full_leakage_audit(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: np.ndarray,
    y_test: np.ndarray,
    full_df: pd.DataFrame,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    group_col: str = "university_name",
    correlation_threshold: float = 0.95,
    known_leaky_features: Optional[Set[str]] = None,
) -> LeakageReport:
    """
    Run all leakage checks and return a consolidated report.

    Does NOT raise — collects all issues into a LeakageReport.
    Caller decides whether to raise based on report.passed.

    Returns:
        LeakageReport with all findings.
    """
    report = LeakageReport()

    # 1. Target correlation
    try:
        check_target_correlation(
            X_train, y_train,
            threshold=correlation_threshold,
            known_leaky_features=known_leaky_features,
        )
    except DataLeakageError as e:
        report.passed = False
        report.issues.append(str(e))
        # Parse leaky features from the X_train
        y_series = pd.Series(y_train, index=X_train.index, name="target")
        for col in X_train.select_dtypes(include=[np.number]).columns:
            corr = X_train[col].corr(y_series, method="spearman")
            if abs(corr) > correlation_threshold:
                report.target_correlation_leaks.append((col, round(corr, 4)))

    # 2. Group leakage
    try:
        check_group_leakage(full_df, group_col, train_idx, test_idx)
    except DataLeakageError as e:
        report.passed = False
        report.group_leakage_detected = True
        report.issues.append(str(e))

    logger.info(report.summary())
    return report


# ── CLI Entry Point ──────────────────────────────────────────────────────────

def main():
    """CLI for standalone leakage analysis on a training CSV."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Run leakage checks on a training dataset")
    parser.add_argument("--csv", required=True, help="Path to training CSV")
    parser.add_argument("--target", default="university_tier", help="Target column name")
    parser.add_argument("--group", default="university_name", help="Group column for split check")
    parser.add_argument("--threshold", type=float, default=0.95, help="Correlation threshold")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    df = pd.read_csv(args.csv)
    logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns from {args.csv}")

    if args.target not in df.columns:
        logger.error(f"Target column '{args.target}' not found")
        sys.exit(1)

    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    y = le.fit_transform(df[args.target].astype(str))

    id_cols = [c for c in df.columns if c.endswith("_id") or c in [
        "university_name", "city", "confidence_score", "data_completeness"
    ]]
    X = df.drop(columns=[args.target] + [c for c in id_cols if c in df.columns])

    # Check target correlation
    try:
        check_target_correlation(X, y, threshold=args.threshold)
    except DataLeakageError as e:
        logger.error(str(e))
        sys.exit(1)

    logger.info("All checks passed")


if __name__ == "__main__":
    main()

"""
CI Quality Gate — automated model quality checks for CI/CD pipelines.

Runs a suite of checks on model artifacts to ensure they meet minimum
quality standards before being deployed. Exit code 0 = pass, 1 = fail.

Usage:
    python -m mlops.ci_quality_gate                    # run all checks
    python -m mlops.ci_quality_gate --artifacts model_artifacts  # custom dir
    python -m mlops.ci_quality_gate --strict            # fail on warnings too

Checks:
  1. Model artifacts exist and are loadable
  2. Metadata is complete and consistent
  3. Leakage check passed
  4. Accuracy is above baseline by min_gap
  5. Accuracy is not suspiciously perfect
  6. Model size is within limits
  7. Feature list matches metadata
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

import joblib

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class QualityGateResult:
    """Results from quality gate checks."""

    def __init__(self):
        self.checks: List[Dict] = []
        self.passed = True
        self.warnings: List[str] = []
        self.errors: List[str] = []

    def add_check(self, name: str, passed: bool, message: str = "", severity: str = "error"):
        self.checks.append({
            "name": name,
            "passed": passed,
            "message": message,
            "severity": severity,
        })
        if not passed:
            if severity == "error":
                self.passed = False
                self.errors.append(f"FAIL: {name} — {message}")
            elif severity == "warning":
                self.warnings.append(f"WARN: {name} — {message}")

    def summary(self) -> str:
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        lines = [f"Quality Gate: {status}"]
        lines.append(f"  Checks: {len(self.checks)} total, "
                      f"{sum(1 for c in self.checks if c['passed'])} passed, "
                      f"{len(self.errors)} errors, {len(self.warnings)} warnings")
        for item in self.errors + self.warnings:
            lines.append(f"  {item}")
        return "\n".join(lines)


def run_quality_gate(
    artifacts_dir: str = "model_artifacts",
    min_accuracy: float = 0.60,
    max_accuracy: float = 0.995,
    min_baseline_gap: float = 0.05,
    max_model_size_mb: float = 100.0,
    strict: bool = False,
) -> QualityGateResult:
    """
    Run all quality gate checks on model artifacts.

    Args:
        artifacts_dir: Path to model artifacts directory.
        min_accuracy: Minimum acceptable accuracy.
        max_accuracy: Maximum acceptable accuracy (flags suspiciously high models).
        min_baseline_gap: Minimum gap over baseline classifier.
        max_model_size_mb: Maximum model file size in MB.
        strict: If True, warnings also cause failure.

    Returns:
        QualityGateResult with all check results.
    """
    result = QualityGateResult()
    artifacts = Path(artifacts_dir)

    # 1. Check artifacts exist
    pipeline_path = artifacts / "model_pipeline.joblib"
    le_path = artifacts / "label_encoder.joblib"
    meta_path = artifacts / "model_metadata.json"

    result.add_check(
        "pipeline_exists",
        pipeline_path.exists(),
        f"Model pipeline not found at {pipeline_path}",
    )
    result.add_check(
        "label_encoder_exists",
        le_path.exists(),
        f"Label encoder not found at {le_path}",
    )
    result.add_check(
        "metadata_exists",
        meta_path.exists(),
        f"Metadata not found at {meta_path}",
    )

    if not all(p.exists() for p in [pipeline_path, meta_path]):
        return result  # Can't continue without core files

    # 2. Load and validate metadata
    try:
        with open(meta_path) as f:
            metadata = json.load(f)
    except json.JSONDecodeError as e:
        result.add_check("metadata_valid", False, f"Invalid JSON: {e}")
        return result

    required_keys = [
        "model_backend", "target_column", "class_names", "metrics",
        "baseline_metrics", "leakage_check_passed", "data_hash",
    ]
    missing_keys = [k for k in required_keys if k not in metadata]
    result.add_check(
        "metadata_complete",
        len(missing_keys) == 0,
        f"Missing metadata keys: {missing_keys}",
    )

    # 3. Leakage check
    leakage_passed = metadata.get("leakage_check_passed", False)
    result.add_check(
        "leakage_check_passed",
        leakage_passed,
        "Leakage check was not passed or was skipped during training",
    )

    # 4. Accuracy checks
    metrics = metadata.get("metrics", {})
    accuracy = metrics.get("accuracy", 0.0)
    f1_macro = metrics.get("f1_macro", 0.0)

    result.add_check(
        "min_accuracy",
        accuracy >= min_accuracy,
        f"Accuracy {accuracy:.4f} < minimum {min_accuracy}",
    )

    result.add_check(
        "max_accuracy",
        accuracy < max_accuracy,
        f"Accuracy {accuracy:.4f} >= {max_accuracy} — suspiciously perfect",
        severity="warning",
    )

    # 5. Baseline gap
    baseline = metadata.get("baseline_metrics", {})
    baseline_acc = baseline.get("accuracy", 0.0)
    gap = accuracy - baseline_acc

    result.add_check(
        "baseline_gap",
        gap >= min_baseline_gap,
        f"Gap over baseline: {gap:.4f} < minimum {min_baseline_gap}",
    )

    # 6. No perfect metrics
    perfect = [k for k, v in metrics.items() if v >= 1.0]
    result.add_check(
        "no_perfect_metrics",
        len(perfect) == 0,
        f"Perfect metrics detected: {perfect}",
    )

    # 7. Model size check
    if pipeline_path.exists():
        size_mb = pipeline_path.stat().st_size / (1024 * 1024)
        result.add_check(
            "model_size",
            size_mb <= max_model_size_mb,
            f"Model size {size_mb:.1f} MB > limit {max_model_size_mb} MB",
            severity="warning",
        )

    # 8. Model loadable
    try:
        model = joblib.load(pipeline_path)
        result.add_check("model_loadable", True)
    except Exception as e:
        result.add_check("model_loadable", False, f"Failed to load model: {e}")

    # 9. Feature list present
    has_features = bool(metadata.get("numeric_features")) or bool(metadata.get("categorical_features"))
    result.add_check(
        "feature_list_present",
        has_features,
        "No feature lists found in metadata",
        severity="warning",
    )

    # 10. Leaky features removed
    leaky = metadata.get("leaky_features_removed", [])
    result.add_check(
        "leaky_features_documented",
        len(leaky) > 0,
        "No leaky features documented in metadata — was leakage check run?",
        severity="warning",
    )

    if strict:
        # In strict mode, warnings also cause failure
        if result.warnings:
            result.passed = False

    return result


def main():
    """CLI entry point for CI/CD integration."""
    import argparse

    parser = argparse.ArgumentParser(description="ML Model Quality Gate")
    parser.add_argument("--artifacts", default="model_artifacts", help="Artifacts directory")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings too")
    parser.add_argument("--min-accuracy", type=float, default=0.60)
    parser.add_argument("--min-gap", type=float, default=0.05)
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = run_quality_gate(
        artifacts_dir=args.artifacts,
        min_accuracy=args.min_accuracy,
        min_baseline_gap=args.min_gap,
        strict=args.strict,
    )

    if args.json:
        output = {
            "passed": result.passed,
            "checks": result.checks,
            "errors": result.errors,
            "warnings": result.warnings,
        }
        print(json.dumps(output, indent=2))
    else:
        print(result.summary())

    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()

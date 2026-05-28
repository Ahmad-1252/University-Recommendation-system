"""
Experiment Tracker — lightweight wrapper around MLflow for tracking experiments.

If MLflow is not installed, falls back to local JSON logging.

Usage:
    from mlops.experiment_tracker import ExperimentTracker

    tracker = ExperimentTracker("university_recommendation")
    with tracker.start_run("retrain_v2"):
        tracker.log_params({"n_estimators": 500, "lr": 0.05})
        tracker.log_metrics({"accuracy": 0.87, "f1_macro": 0.82})
        tracker.log_artifact("model_artifacts/model_pipeline.joblib")
"""

import json
import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Try to import MLflow
try:
    import mlflow
    import mlflow.sklearn
    HAS_MLFLOW = True
except ImportError:
    HAS_MLFLOW = False
    logger.info("MLflow not installed — using local JSON experiment tracking")


class ExperimentTracker:
    """
    Tracks ML experiments with MLflow or local JSON fallback.

    Logs parameters, metrics, and artifacts for each training run
    to enable comparison and reproducibility.
    """

    def __init__(
        self,
        experiment_name: str = "university_recommendation",
        tracking_uri: Optional[str] = None,
        local_dir: str = "mlops/experiments",
    ):
        self.experiment_name = experiment_name
        self._local_dir = Path(local_dir)
        self._local_dir.mkdir(parents=True, exist_ok=True)
        self._current_run: Dict[str, Any] = {}
        self._run_active = False

        if HAS_MLFLOW:
            if tracking_uri:
                mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment(experiment_name)
            logger.info(f"MLflow experiment: {experiment_name}")
        else:
            logger.info(f"Local experiment tracking: {self._local_dir}")

    @contextmanager
    def start_run(self, run_name: str = None):
        """
        Context manager for an experiment run.

        Usage:
            with tracker.start_run("retrain_v2"):
                tracker.log_params({...})
                tracker.log_metrics({...})
        """
        self._current_run = {
            "run_name": run_name or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "started_at": datetime.now().isoformat(),
            "params": {},
            "metrics": {},
            "artifacts": [],
            "tags": {},
        }
        self._run_active = True

        if HAS_MLFLOW:
            with mlflow.start_run(run_name=run_name):
                try:
                    yield self
                finally:
                    self._save_local_run()
                    self._run_active = False
        else:
            try:
                yield self
            finally:
                self._save_local_run()
                self._run_active = False

    def log_params(self, params: Dict[str, Any]) -> None:
        """Log hyperparameters for the current run."""
        if not self._run_active:
            logger.warning("No active run — call start_run() first")
            return

        # Convert all values to strings for MLflow compatibility
        safe_params = {k: str(v) for k, v in params.items()}
        self._current_run["params"].update(safe_params)

        if HAS_MLFLOW:
            try:
                mlflow.log_params(safe_params)
            except Exception as e:
                logger.warning(f"MLflow log_params failed: {e}")

    def log_metrics(self, metrics: Dict[str, float], step: int = None) -> None:
        """Log evaluation metrics for the current run."""
        if not self._run_active:
            logger.warning("No active run — call start_run() first")
            return

        self._current_run["metrics"].update(metrics)

        if HAS_MLFLOW:
            try:
                mlflow.log_metrics(metrics, step=step)
            except Exception as e:
                logger.warning(f"MLflow log_metrics failed: {e}")

    def log_metric(self, key: str, value: float, step: int = None) -> None:
        """Log a single metric."""
        self.log_metrics({key: value}, step=step)

    def log_artifact(self, artifact_path: str) -> None:
        """Log an artifact (file) for the current run."""
        if not self._run_active:
            logger.warning("No active run — call start_run() first")
            return

        self._current_run["artifacts"].append(str(artifact_path))

        if HAS_MLFLOW:
            try:
                if Path(artifact_path).exists():
                    mlflow.log_artifact(artifact_path)
            except Exception as e:
                logger.warning(f"MLflow log_artifact failed: {e}")

    def log_model(self, model: Any, artifact_path: str = "model") -> None:
        """Log a sklearn model for the current run."""
        if not self._run_active:
            return

        if HAS_MLFLOW:
            try:
                mlflow.sklearn.log_model(model, artifact_path)
            except Exception as e:
                logger.warning(f"MLflow log_model failed: {e}")

    def set_tag(self, key: str, value: str) -> None:
        """Set a tag on the current run."""
        if not self._run_active:
            return

        self._current_run.setdefault("tags", {})[key] = value

        if HAS_MLFLOW:
            try:
                mlflow.set_tag(key, value)
            except Exception as e:
                logger.warning(f"MLflow set_tag failed: {e}")

    def log_feature_importance(
        self,
        feature_names: list,
        importances: list,
        top_n: int = 20,
    ) -> None:
        """Log feature importance as a metric series."""
        pairs = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
        for i, (name, imp) in enumerate(pairs[:top_n]):
            self.log_metric(f"feature_importance_{name}", float(imp))
        self._current_run["feature_importance"] = [
            {"feature": name, "importance": float(imp)} for name, imp in pairs[:top_n]
        ]

    def _save_local_run(self) -> None:
        """Save the current run as a local JSON file."""
        self._current_run["finished_at"] = datetime.now().isoformat()
        run_name = self._current_run.get("run_name", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{run_name}_{timestamp}.json"
        filepath = self._local_dir / filename

        with open(filepath, "w") as f:
            json.dump(self._current_run, f, indent=2, default=str)

        logger.info(f"Experiment run saved: {filepath}")

    # ── Query ────────────────────────────────────────────────────────────────

    def list_runs(self, limit: int = 10) -> list:
        """List recent experiment runs from local storage."""
        runs = sorted(self._local_dir.glob("*.json"), reverse=True)[:limit]
        result = []
        for p in runs:
            try:
                with open(p) as f:
                    run = json.load(f)
                result.append({
                    "run_name": run.get("run_name"),
                    "started_at": run.get("started_at"),
                    "metrics": run.get("metrics", {}),
                    "filename": p.name,
                })
            except Exception:
                continue
        return result

    def get_best_run(self, metric: str = "f1_macro") -> Optional[Dict]:
        """Find the run with the best value for a given metric."""
        runs = self.list_runs(limit=100)
        best = None
        best_val = -float("inf")
        for run in runs:
            val = run.get("metrics", {}).get(metric, -float("inf"))
            if val > best_val:
                best_val = val
                best = run
        return best

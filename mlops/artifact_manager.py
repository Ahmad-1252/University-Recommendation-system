"""
Artifact Manager — versioned model and dataset storage with cleanup.

Manages the lifecycle of model artifacts:
  - Save models with timestamp + git hash versioning
  - Load latest or specific model versions
  - List all available versions
  - Cleanup old versions (keep N most recent)

Usage:
    from mlops.artifact_manager import ArtifactManager

    manager = ArtifactManager("model_artifacts")
    manager.save_model(pipeline, "model_pipeline", metadata={...})
    latest = manager.load_latest_model("model_pipeline")
    manager.cleanup(keep=5)  # keep only 5 most recent versions
"""

import json
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib

logger = logging.getLogger(__name__)


def _get_git_hash() -> str:
    """Get current git short hash, or 'nogit' if not in a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "nogit"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "nogit"


class ArtifactManager:
    """
    Manages versioned model artifacts on local filesystem.

    Naming convention: {name}_{timestamp}_{git_hash}.{ext}
    Example: model_pipeline_20260219_123456_abc1234.joblib

    Also maintains a "latest" symlink/copy for easy loading.
    """

    def __init__(self, artifacts_dir: str = "model_artifacts"):
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._versions_dir = self.artifacts_dir / "versions"
        self._versions_dir.mkdir(exist_ok=True)

    def _make_version_name(self, name: str, ext: str = "joblib") -> str:
        """Generate versioned filename with timestamp and git hash."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        git_hash = _get_git_hash()
        return f"{name}_{timestamp}_{git_hash}.{ext}"

    # ── Save ─────────────────────────────────────────────────────────────────

    def save_model(
        self,
        model: Any,
        name: str = "model_pipeline",
        metadata: Optional[Dict] = None,
    ) -> Path:
        """
        Save a model artifact with versioning.

        Creates:
          - model_artifacts/{name}.joblib (latest, overwritten each time)
          - model_artifacts/versions/{name}_{ts}_{git}.joblib (versioned)
          - model_artifacts/versions/{name}_{ts}_{git}_metadata.json (if metadata provided)

        Args:
            model: Scikit-learn pipeline or model object.
            name: Base name for the artifact.
            metadata: Optional metadata dict to save alongside.

        Returns:
            Path to the versioned artifact.
        """
        # Save latest
        latest_path = self.artifacts_dir / f"{name}.joblib"
        joblib.dump(model, latest_path)
        logger.info(f"Saved latest: {latest_path} ({latest_path.stat().st_size / 1024:.0f} KB)")

        # Save versioned copy
        version_name = self._make_version_name(name, "joblib")
        version_path = self._versions_dir / version_name
        joblib.dump(model, version_path)
        logger.info(f"Saved version: {version_path}")

        # Save metadata alongside version
        if metadata:
            meta_name = version_name.replace(".joblib", "_metadata.json")
            meta_path = self._versions_dir / meta_name
            with open(meta_path, "w") as f:
                json.dump(metadata, f, indent=2, default=str)

        return version_path

    def save_dataset(
        self,
        df: Any,
        name: str = "training_dataset",
        format: str = "csv",
    ) -> Path:
        """
        Save a dataset with versioning.

        Args:
            df: pandas DataFrame to save.
            name: Base name for the dataset.
            format: 'csv' or 'parquet'.

        Returns:
            Path to the versioned dataset.
        """
        # Save latest
        ext = "csv" if format == "csv" else "parquet"
        latest_path = self.artifacts_dir / f"{name}.{ext}"

        if format == "csv":
            df.to_csv(latest_path, index=False)
        else:
            df.to_parquet(latest_path, index=False)

        logger.info(f"Saved latest dataset: {latest_path} ({len(df)} rows)")

        # Save versioned copy
        version_name = self._make_version_name(name, ext)
        version_path = self._versions_dir / version_name

        if format == "csv":
            df.to_csv(version_path, index=False)
        else:
            df.to_parquet(version_path, index=False)

        return version_path

    # ── Load ─────────────────────────────────────────────────────────────────

    def load_latest_model(self, name: str = "model_pipeline") -> Any:
        """Load the latest version of a model artifact."""
        latest_path = self.artifacts_dir / f"{name}.joblib"
        if not latest_path.exists():
            raise FileNotFoundError(f"No model found at {latest_path}")

        model = joblib.load(latest_path)
        logger.info(f"Loaded model: {latest_path}")
        return model

    def load_version(self, version_filename: str) -> Any:
        """Load a specific versioned artifact."""
        version_path = self._versions_dir / version_filename
        if not version_path.exists():
            raise FileNotFoundError(f"Version not found: {version_path}")

        return joblib.load(version_path)

    # ── List ─────────────────────────────────────────────────────────────────

    def list_versions(self, name: str = "model_pipeline") -> List[Dict]:
        """
        List all available versions of an artifact.

        Returns list of dicts with filename, size_kb, created_at.
        """
        pattern = f"{name}_*.joblib"
        versions = sorted(self._versions_dir.glob(pattern), reverse=True)

        result = []
        for p in versions:
            result.append({
                "filename": p.name,
                "size_kb": round(p.stat().st_size / 1024, 1),
                "created_at": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
            })

        return result

    # ── Cleanup ──────────────────────────────────────────────────────────────

    def cleanup(self, name: str = "model_pipeline", keep: int = 5) -> int:
        """
        Remove old versions of an artifact, keeping the N most recent.

        Args:
            name: Base name of the artifact.
            keep: Number of most recent versions to keep.

        Returns:
            Number of versions deleted.
        """
        pattern = f"{name}_*"
        all_files = sorted(self._versions_dir.glob(pattern), reverse=True)

        # Group by base name (remove _metadata.json pairs)
        version_files = [f for f in all_files if f.suffix == ".joblib"]
        to_delete = version_files[keep:]

        deleted = 0
        for f in to_delete:
            f.unlink()
            # Also delete metadata file if present
            meta_file = f.with_name(f.stem + "_metadata.json")
            if meta_file.exists():
                meta_file.unlink()
            deleted += 1

        if deleted:
            logger.info(f"Cleaned up {deleted} old versions of '{name}' (kept {keep})")

        return deleted

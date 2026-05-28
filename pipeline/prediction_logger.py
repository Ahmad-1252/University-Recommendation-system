"""
Prediction Logger — logs every recommendation for offline analysis.

Each prediction is logged as a JSON line to a daily rotating file.
Enables:
  - Offline evaluation of model quality
  - Debugging bad recommendations
  - Audit trail for compliance
  - Drift detection on serving data
"""

import json
import logging
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PredictionLogger:
    """Log predictions to daily JSONL files."""

    def __init__(self, log_dir: str = "logs/predictions"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._file = None
        self._current_date = None
        logger.info(f"PredictionLogger initialized: {self.log_dir}")

    def log(
        self,
        request_id: str,
        profile: Dict[str, Any],
        recommendations: List[Dict[str, Any]],
        latency_ms: float,
        model_version: Optional[str] = None,
    ) -> None:
        """Log a single recommendation request/response pair.

        Args:
            request_id: unique identifier for this request.
            profile: student profile that was submitted.
            recommendations: list of recommended programs.
            latency_ms: total inference time in milliseconds.
            model_version: version string of the model used.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "profile_hash": self._hash_profile(profile),
            "profile_country": profile.get("preferred_countries", [None])[0] if profile.get("preferred_countries") else None,
            "profile_budget": profile.get("budget"),
            "profile_gpa": profile.get("gpa"),
            "n_results": len(recommendations),
            "top_score": recommendations[0]["match_score"] if recommendations else None,
            "top_tier": recommendations[0].get("predicted_tier") if recommendations else None,
            "top_confidence": recommendations[0].get("confidence_band") if recommendations else None,
            "latency_ms": round(latency_ms, 1),
            "model_version": model_version,
        }

        try:
            f = self._get_file()
            f.write(json.dumps(entry) + "\n")
            f.flush()
        except Exception as e:
            logger.error(f"Failed to log prediction: {e}")

    def _hash_profile(self, profile: Dict[str, Any]) -> str:
        """Hash profile for grouping without storing PII."""
        import hashlib
        canonical = json.dumps(profile, sort_keys=True, default=str)
        return hashlib.md5(canonical.encode()).hexdigest()[:12]

    def _get_file(self):
        """Get or rotate the log file for today."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._current_date != today:
            if self._file:
                self._file.close()
            path = self.log_dir / f"predictions_{today}.jsonl"
            self._file = open(path, "a", encoding="utf-8")
            self._current_date = today
        return self._file

    def close(self):
        """Close the current log file."""
        if self._file:
            self._file.close()
            self._file = None

    def __del__(self):
        self.close()

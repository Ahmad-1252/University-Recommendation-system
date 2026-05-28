"""CLI interface for the University Recommendation System."""

from .commands import cli
from .dashboard import Dashboard
from .data_viewer import DataViewer

__all__ = ["Dashboard", "DataViewer", "cli"]

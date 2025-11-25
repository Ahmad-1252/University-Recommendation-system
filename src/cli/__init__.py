"""CLI interface for the University Recommendation System."""

from .dashboard import Dashboard
from .data_viewer import DataViewer
from .commands import cli

__all__ = [
    "Dashboard",
    "DataViewer",
    "cli"
]
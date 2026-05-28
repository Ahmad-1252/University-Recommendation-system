"""Data models for the University Recommendation System."""

from .university import (
    AnalysisResult,
    ApplicationDeadlines,
    DegreeType,
    ExportResult,
    LanguageProficiency,
    Rankings,
    ScrapingConfig,
    TuitionFees,
    UniversityProgram,
)

__all__ = [
    "UniversityProgram",
    "DegreeType",
    "LanguageProficiency",
    "TuitionFees",
    "ApplicationDeadlines",
    "Rankings",
    "ScrapingConfig",
    "AnalysisResult",
    "ExportResult",
]

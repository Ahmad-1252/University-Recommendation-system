"""Data quality analysis and monitoring."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..core.config import get_settings
from ..database.repositories import ProgramRepository
from ..models.university import AnalysisResult, UniversityProgram
from ..services.validation_service import ValidationService

logger = logging.getLogger(__name__)


class QualityAnalyzer:
    """Analyzes data quality and provides monitoring insights."""

    def __init__(
        self,
        repository: Optional[ProgramRepository] = None,
        validation_service: Optional[ValidationService] = None,
    ):
        self.settings = get_settings()
        self.repository = repository or ProgramRepository()
        self.validation_service = validation_service or ValidationService()

    def analyze_data_quality(
        self, programs: Optional[List[UniversityProgram]] = None
    ) -> AnalysisResult:
        """
        Analyze the quality of program data.

        Args:
            programs: List of programs to analyze (if None, gets all from database)

        Returns:
            AnalysisResult with quality metrics
        """
        if programs is None:
            programs = self.repository.get_all_programs()

        if not programs:
            return AnalysisResult(
                total_programs=0,
                average_completeness=0.0,
                quality_score=0.0,
                issues_found=["No programs found to analyze"],
                recommendations=["Add programs to the database before analysis"],
            )

        total_programs = len(programs)
        completeness_scores = []
        validation_issues = []
        quality_issues = []

        # Analyze each program
        for program in programs:
            # Calculate completeness
            completeness_scores.append(program.data_completeness)

            # Validate data
            validation_result = self.validation_service.validate_program_data(program)
            if not validation_result["is_valid"]:
                validation_issues.extend(validation_result["issues"])
            if validation_result["warnings"]:
                quality_issues.extend(validation_result["warnings"])

        # Calculate aggregate metrics
        avg_completeness = (
            sum(completeness_scores) / len(completeness_scores)
            if completeness_scores
            else 0.0
        )

        # Calculate overall quality score
        quality_score = self._calculate_overall_quality_score(
            avg_completeness, validation_issues, quality_issues, total_programs
        )

        # Generate recommendations
        recommendations = self._generate_quality_recommendations(
            avg_completeness, validation_issues, quality_issues
        )

        return AnalysisResult(
            total_programs=total_programs,
            average_completeness=avg_completeness,
            quality_score=quality_score,
            issues_found=validation_issues + quality_issues,
            recommendations=recommendations,
        )

    def _calculate_overall_quality_score(
        self,
        avg_completeness: float,
        validation_issues: List[str],
        quality_issues: List[str],
        total_programs: int,
    ) -> float:
        """Calculate overall quality score from 0.0 to 1.0."""
        # Base score from completeness
        score = avg_completeness * 0.7

        # Penalty for validation issues
        validation_penalty = min(len(validation_issues) / total_programs, 0.3)
        score -= validation_penalty

        # Penalty for quality issues
        quality_penalty = min(len(quality_issues) / (total_programs * 2), 0.2)
        score -= quality_penalty

        return max(0.0, min(1.0, score))

    def _generate_quality_recommendations(
        self,
        avg_completeness: float,
        validation_issues: List[str],
        quality_issues: List[str],
    ) -> List[str]:
        """Generate recommendations based on quality analysis."""
        recommendations = []

        if avg_completeness < 0.7:
            recommendations.append(
                "Improve data completeness - aim for 80%+ field coverage"
            )

        if validation_issues:
            issue_counts = defaultdict(int)
            for issue in validation_issues:
                issue_counts[issue] += 1

            top_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[
                :3
            ]
            for issue, count in top_issues:
                recommendations.append(f"Fix {count} programs with: {issue}")

        if quality_issues:
            recommendations.append("Review and address data quality warnings")

        if not recommendations:
            recommendations.append("Data quality is good - continue monitoring")

        return recommendations

    def analyze_universities_coverage(self) -> Dict[str, Any]:
        """
        Analyze coverage across different universities and countries.

        Returns:
            Coverage analysis results
        """
        programs = self.repository.get_all_programs()

        if not programs:
            return {"error": "No programs found"}

        # Count by university
        university_counts = defaultdict(int)
        country_counts = defaultdict(int)
        degree_counts = defaultdict(int)

        for program in programs:
            university_counts[program.university_name] += 1
            country_counts[program.country or "Unknown"] += 1
            degree_counts[program.degree_type] += 1

        return {
            "total_programs": len(programs),
            "universities_covered": len(university_counts),
            "countries_covered": len(country_counts),
            "degrees_offered": dict(degree_counts),
            "top_universities": dict(
                sorted(university_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
            "country_distribution": dict(
                sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
            ),
        }

    def analyze_freshness(self, days_threshold: int = 30) -> Dict[str, Any]:
        """
        Analyze data freshness.

        Args:
            days_threshold: Number of days to consider data stale

        Returns:
            Freshness analysis results
        """
        programs = self.repository.get_all_programs()
        cutoff_date = datetime.now(datetime.UTC) - timedelta(days=days_threshold)

        fresh_count = 0
        stale_count = 0
        oldest_update = None
        newest_update = None

        for program in programs:
            if program.last_updated >= cutoff_date:
                fresh_count += 1
            else:
                stale_count += 1

            if oldest_update is None or program.last_updated < oldest_update:
                oldest_update = program.last_updated
            if newest_update is None or program.last_updated > newest_update:
                newest_update = program.last_updated

        return {
            "total_programs": len(programs),
            "fresh_programs": fresh_count,
            "stale_programs": stale_count,
            "freshness_ratio": fresh_count / len(programs) if programs else 0.0,
            "oldest_update": oldest_update.isoformat() if oldest_update else None,
            "newest_update": newest_update.isoformat() if newest_update else None,
            "days_threshold": days_threshold,
        }

    def generate_quality_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive quality report.

        Returns:
            Complete quality analysis report
        """
        logger.info("Generating comprehensive quality report")

        # Basic quality analysis
        quality_analysis = self.analyze_data_quality()

        # Coverage analysis
        coverage_analysis = self.analyze_universities_coverage()

        # Freshness analysis
        freshness_analysis = self.analyze_freshness()

        # Additional statistics
        programs = self.repository.get_all_programs()
        stats = self.repository.get_statistics()

        return {
            "generated_at": datetime.now(datetime.UTC).isoformat(),
            "quality_analysis": quality_analysis.model_dump(),
            "coverage_analysis": coverage_analysis,
            "freshness_analysis": freshness_analysis,
            "database_stats": stats,
            "summary": {
                "total_programs": len(programs),
                "overall_quality_score": quality_analysis.quality_score,
                "data_completeness": quality_analysis.average_completeness,
                "critical_issues": len(
                    [
                        i
                        for i in quality_analysis.issues_found
                        if "required" in i.lower()
                    ]
                ),
                "recommendations_count": len(quality_analysis.recommendations),
            },
        }

"""University Validation and Milestone Tracker - Moved to tests/validation.
This file is the same as root validate_universities.py but updated to detect project root and not change working dir.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

import requests

# Setup path: compute project root instead of being relative to current script
script_dir = Path(__file__).resolve().parent
project_root = script_dir
while project_root != project_root.parent:
    if (
        (project_root / "pyproject.toml").exists()
        or (project_root / "setup.py").exists()
        or (project_root / "src").exists()
    ):
        break
    project_root = project_root.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

from dotenv import load_dotenv

load_dotenv(str(project_root / ".env"))

# Do not change current working dir; rely on explicit paths

from core.config import get_settings
from database.mongodb import get_mongo_connection
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt

console = Console()


class ValidationMilestone:
    """Represents a validation milestone for a university."""

    def __init__(self, university_name: str, university_id: str = None):
        self.university_name = university_name
        self.university_id = university_id
        self.checks = {}
        self.issues = []
        self.recommendations = []
        self.score = 0.0
        self.completed_at = None
        self.status = "pending"  # pending, in_progress, completed, failed

    def add_check(
        self, check_name: str, passed: bool, details: str = None, severity: str = "info"
    ):
        """Add a validation check result."""
        self.checks[check_name] = {
            "passed": passed,
            "details": details,
            "severity": severity,
            "timestamp": datetime.now(datetime.UTC).isoformat(),
        }

        if not passed and severity in ["error", "warning"]:
            self.issues.append(f"{check_name}: {details}")

    def add_recommendation(self, recommendation: str):
        """Add a recommendation for improvement."""
        self.recommendations.append(recommendation)

    def calculate_score(self) -> float:
        """Calculate overall validation score."""
        if not self.checks:
            return 0.0

        total_checks = len(self.checks)
        passed_checks = sum(1 for check in self.checks.values() if check["passed"])

        # Weight critical checks more heavily
        weighted_score = 0.0
        total_weight = 0.0

        for check_name, check_data in self.checks.items():
            weight = 1.0
            if "critical" in check_name.lower() or "required" in check_name.lower():
                weight = 2.0
            elif "optional" in check_name.lower():
                weight = 0.5

            if check_data["passed"]:
                weighted_score += weight
            total_weight += weight

        self.score = weighted_score / total_weight if total_weight > 0 else 0.0
        return self.score

    def complete(self, status: str = "completed"):
        """Mark milestone as completed."""
        self.status = status
        self.completed_at = datetime.now(datetime.UTC).isoformat()
        self.calculate_score()

    def to_dict(self) -> Dict[str, Any]:
        """Convert milestone to dictionary."""

        def make_serializable(obj):
            """Convert object to JSON-serializable format."""
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, (list, tuple)):
                return [make_serializable(item) for item in obj]
            elif isinstance(obj, dict):
                return {key: make_serializable(value) for key, value in obj.items()}
            elif hasattr(obj, "__dict__"):
                return str(obj)  # Convert objects to string
            else:
                return obj

        return {
            "university_name": self.university_name,
            "university_id": self.university_id,
            "status": self.status,
            "score": self.score,
            "checks": make_serializable(self.checks),
            "issues": self.issues,
            "recommendations": self.recommendations,
            "completed_at": self.completed_at,
            "total_checks": len(self.checks),
            "passed_checks": sum(
                1 for check in self.checks.values() if check["passed"]
            ),
        }


class UniversityValidator:
    """Comprehensive university validation system with milestone tracking."""

    def __init__(self):
        self.settings = get_settings()
        self.mongo_conn = None
        self.universities_data = []
        self.programs_data = []
        self.milestones = {}
        self.progress_file = (
            Path(self.settings.exports_dir) / "validation_milestones.json"
        )

    def connect_database(self) -> bool:
        """Connect to MongoDB and load data."""
        try:
            self.mongo_conn = get_mongo_connection()

            # Fetch all universities
            universities_collection = self.mongo_conn.universities_collection
            self.universities_data = list(universities_collection.find({}, {"_id": 0}))

            # Fetch all programs
            programs_collection = self.mongo_conn.collection
            self.programs_data = list(programs_collection.find({}, {"_id": 0}))

            console.print("[green]✓[/green] Connected to database successfully")
            console.print(
                f"[blue]🏫[/blue] Found {len(self.universities_data)} universities"
            )
            console.print(f"[blue]📊[/blue] Found {len(self.programs_data)} programs")

            return True

        except Exception as e:
            console.print(f"[red]✗[/red] Failed to connect to database: {e}")
            return False

    def load_existing_milestones(self) -> Dict[str, ValidationMilestone]:
        """Load existing milestones from file."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, encoding="utf-8") as f:
                    data = json.load(f)
                    milestones = {}
                    for uni_name, milestone_data in data.items():
                        milestone = ValidationMilestone(
                            uni_name, milestone_data.get("university_id")
                        )
                        milestone.checks = milestone_data.get("checks", {})
                        milestone.issues = milestone_data.get("issues", [])
                        milestone.recommendations = milestone_data.get(
                            "recommendations", []
                        )
                        milestone.score = milestone_data.get("score", 0.0)
                        milestone.status = milestone_data.get("status", "pending")
                        milestone.completed_at = milestone_data.get("completed_at")
                        milestones[uni_name] = milestone
                    return milestones
            except Exception as e:
                console.print(
                    f"[yellow]⚠[/yellow] Failed to load existing milestones: {e}"
                )

        return {}

    def save_milestones(self):
        """Save milestones to file."""
        try:
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                name: milestone.to_dict() for name, milestone in self.milestones.items()
            }

            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            console.print(
                f"[green]✓[/green] Saved {len(self.milestones)} milestones to {self.progress_file}"
            )
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to save milestones: {e}")

    def validate_university_basic_info(self, university: Dict) -> ValidationMilestone:
        """Validate basic university information."""
        name = university.get("name", "Unknown University")
        milestone = ValidationMilestone(name, university.get("university_id"))

        # Check required fields
        required_fields = ["name", "country", "city"]
        for field in required_fields:
            value = university.get(field)
            passed = value is not None and str(value).strip() != ""
            milestone.add_check(
                f"required_field_{field}",
                passed,
                f"Field '{field}' is {'present' if passed else 'missing or empty'}",
                "error" if not passed else "info",
            )

        # Check university_id format
        uni_id = university.get("university_id")
        if uni_id:
            import re

            match = re.match(r"^[a-f0-9]{12}$", str(uni_id))
            passed = match is not None
            milestone.add_check(
                "university_id_format",
                passed,
                f"University ID format is {'valid' if passed else 'invalid'}",
                "warning" if not passed else "info",
            )
        else:
            milestone.add_check(
                "university_id_missing", False, "University ID is missing", "warning"
            )

        # Check website URL
        website = university.get("website")
        if website:
            try:
                parsed = urlparse(website)
                passed = parsed.scheme in ["http", "https"] and parsed.netloc
                milestone.add_check(
                    "website_url_valid",
                    passed,
                    f"Website URL is {'valid' if passed else 'invalid'}",
                    "warning" if not passed else "info",
                )
            except:
                milestone.add_check(
                    "website_url_valid",
                    False,
                    "Website URL format is invalid",
                    "warning",
                )
        else:
            milestone.add_check(
                "website_url_missing", False, "Website URL is missing", "info"
            )

        return milestone

    def validate_university_rankings(self, university: Dict) -> None:
        """Validate university rankings data."""
        name = university.get("name", "Unknown University")
        if name not in self.milestones:
            return

        milestone = self.milestones[name]

        # Check ranking fields
        ranking_fields = ["qs_world_ranking", "the_world_ranking", "us_news_ranking"]
        has_any_ranking = False

        for field in ranking_fields:
            value = university.get(field)
            if value is not None:
                has_any_ranking = True
                passed = isinstance(value, int) and value > 0
                milestone.add_check(
                    f"ranking_{field}_valid",
                    passed,
                    f"{field} is {'valid' if passed else 'invalid'} ({value})",
                    "warning" if not passed else "info",
                )

        if not has_any_ranking:
            milestone.add_check(
                "no_rankings", False, "No ranking data available", "info"
            )
            milestone.add_recommendation(
                "Add university ranking information from QS, THE, or US News"
            )

        tier = university.get("tier")
        if tier:
            valid_tiers = ["top", "good", "standard"]
            passed = tier.lower() in valid_tiers
            milestone.add_check(
                "tier_classification",
                passed,
                f"Tier '{tier}' is {'valid' if passed else 'invalid'}",
                "warning" if not passed else "info",
            )
        else:
            milestone.add_check(
                "tier_missing", False, "University tier is not classified", "info"
            )

    def validate_university_programs(self, university: Dict) -> None:
        """Validate programs associated with university."""
        name = university.get("name", "Unknown University")
        if name not in self.milestones:
            return

        milestone = self.milestones[name]

        # Find programs for this university
        uni_programs = [
            p for p in self.programs_data if p.get("university_name") == name
        ]

        if not uni_programs:
            milestone.add_check(
                "no_programs", False, "No programs found for this university", "error"
            )
            milestone.add_recommendation("Scrape programs data for this university")
            return

        milestone.add_check(
            "programs_count",
            len(uni_programs) > 0,
            f"Found {len(uni_programs)} programs",
            "info",
        )

        # Check program data quality
        programs_with_descriptions = sum(
            1 for p in uni_programs if p.get("program_description", "").strip()
        )
        programs_with_fees = sum(
            1
            for p in uni_programs
            if p.get("tuition_fees", {}).get("domestic_per_year")
        )

        description_coverage = (
            programs_with_descriptions / len(uni_programs) if uni_programs else 0
        )
        fees_coverage = programs_with_fees / len(uni_programs) if uni_programs else 0

        milestone.add_check(
            "program_descriptions",
            description_coverage > 0.5,
            ".1%",
            "warning" if description_coverage < 0.5 else "info",
        )

        milestone.add_check(
            "program_fees",
            fees_coverage > 0.3,
            ".1%",
            "warning" if fees_coverage < 0.3 else "info",
        )

        # Check for duplicate programs
        program_names = [
            p.get("program_name", "").lower().strip() for p in uni_programs
        ]
        duplicates = len(program_names) - len(set(program_names))

        if duplicates > 0:
            milestone.add_check(
                "duplicate_programs",
                False,
                f"Found {duplicates} duplicate program names",
                "warning",
            )
            milestone.add_recommendation("Remove duplicate programs")

    def validate_university_completeness(self, university: Dict) -> None:
        """Validate overall data completeness."""
        name = university.get("name", "Unknown University")
        if name not in self.milestones:
            return

        milestone = self.milestones[name]

        important_fields = [
            "description",
            "website",
            "founding_year",
            "total_students",
            "qs_world_ranking",
            "type",
            "tier",
        ]

        filled_fields = sum(
            1 for field in important_fields if university.get(field) is not None
        )
        completeness = filled_fields / len(important_fields)

        milestone.add_check(
            "data_completeness",
            completeness > 0.6,
            ".1%",
            "warning" if completeness < 0.6 else "info",
        )

        if completeness < 0.6:
            milestone.add_recommendation(
                "Improve data completeness by adding missing fields"
            )

    async def validate_university_website(self, university: Dict) -> None:
        """Validate university website accessibility."""
        name = university.get("name", "Unknown University")
        if name not in self.milestones:
            return

        milestone = self.milestones[name]
        website = university.get("website")

        if not website:
            milestone.add_check(
                "website_accessibility", False, "No website URL to test", "info"
            )
            return

        try:
            response = requests.head(website, timeout=10, allow_redirects=True)
            passed = response.status_code == 200
            milestone.add_check(
                "website_accessibility",
                passed,
                f"Website returned status {response.status_code}",
                "error" if not passed else "info",
            )
        except requests.RequestException as e:
            milestone.add_check(
                "website_accessibility",
                False,
                f"Website not accessible: {str(e)}",
                "warning",
            )

    def validate_university_data_quality(self, university: Dict) -> ValidationMilestone:
        """Run all validation checks for a university."""
        name = university.get("name", "Unknown University")

        if name in self.milestones:
            milestone = self.milestones[name]
        else:
            milestone = self.validate_university_basic_info(university)
            self.milestones[name] = milestone

        milestone.status = "in_progress"

        self.validate_university_rankings(university)
        self.validate_university_programs(university)
        self.validate_university_completeness(university)

        milestone.complete("completed")

        return milestone

    async def validate_all_universities(
        self, check_websites: bool = False
    ) -> Dict[str, ValidationMilestone]:
        """Validate all universities with progress tracking."""
        if not self.universities_data:
            console.print("[yellow]⚠[/yellow] No universities to validate")
            return {}

        console.print(
            f"\n[bold blue]🔍 Starting validation of {len(self.universities_data)} universities[/bold blue]"
        )

        self.milestones = self.load_existing_milestones()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            main_task = progress.add_task(
                "Validating universities...", total=len(self.universities_data)
            )

            for i, university in enumerate(self.universities_data):
                name = university.get("name", f"University {i+1}")

                progress.update(main_task, description=f"Validating: {name[:50]}...")

                milestone = self.validate_university_data_quality(university)

                if check_websites:
                    await self.validate_university_website(university)

                progress.advance(main_task)

        self.save_milestones()

        return self.milestones

    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        if not self.milestones:
            return {"error": "No milestones to report"}

        total_universities = len(self.milestones)
        completed_validations = sum(
            1 for m in self.milestones.values() if m.status == "completed"
        )
        average_score = (
            sum(m.score for m in self.milestones.values()) / total_universities
            if total_universities > 0
            else 0
        )

        score_categories = {
            "excellent": sum(1 for m in self.milestones.values() if m.score >= 0.9),
            "good": sum(1 for m in self.milestones.values() if 0.7 <= m.score < 0.9),
            "needs_improvement": sum(
                1 for m in self.milestones.values() if 0.5 <= m.score < 0.7
            ),
            "critical_issues": sum(
                1 for m in self.milestones.values() if m.score < 0.5
            ),
        }

        all_issues = []
        all_recommendations = []

        for milestone in self.milestones.values():
            all_issues.extend(milestone.issues)
            all_recommendations.extend(milestone.recommendations)

        issue_summary = {}
        for issue in all_issues:
            category = issue.split(":")[0] if ":" in issue else "other"
            issue_summary[category] = issue_summary.get(category, 0) + 1

        return {
            "summary": {
                "total_universities": total_universities,
                "completed_validations": completed_validations,
                "average_score": round(average_score, 3),
                "score_distribution": score_categories,
            },
            "issues": {
                "total_issues": len(all_issues),
                "by_category": issue_summary,
                "top_issues": all_issues[:20],
            },
            "recommendations": list(set(all_recommendations)),
            "milestones": {name: m.to_dict() for name, m in self.milestones.items()},
        }

    def display_validation_results(self, report: Dict[str, Any]):
        """Display validation results in a nice format."""
        if "error" in report:
            console.print(f"[red]❌ {report['error']}[/red]")
            return

        summary = report["summary"]

        console.print("\n[bold green]📊 Validation Summary[/bold green]")
        console.print(f"Total Universities: {summary['total_universities']}")
        console.print(f"Completed Validations: {summary['completed_validations']}")
        console.print(f"Average Score: {summary['average_score']:.3f}")

        console.print("\n[bold blue]📈 Score Distribution[/bold blue]")
        distribution = summary["score_distribution"]
        for category, count in distribution.items():
            emoji = {
                "excellent": "🌟",
                "good": "✅",
                "needs_improvement": "⚠️",
                "critical_issues": "❌",
            }.get(category, "❓")
            console.print(f"  {emoji} {category.replace('_', ' ').title()}: {count}")

        issues = report["issues"]
        if issues["total_issues"] > 0:
            console.print(
                f"\n[bold yellow]⚠️ Issues Found: {issues['total_issues']}[/bold yellow]"
            )
            console.print("[bold]Top Issue Categories:[/bold]")
            for category, count in sorted(
                issues["by_category"].items(), key=lambda x: x[1], reverse=True
            )[:10]:
                console.print(f"  • {category}: {count}")

        recommendations = report["recommendations"]
        if recommendations:
            console.print(
                f"\n[bold cyan]💡 Recommendations ({len(recommendations)})[/bold cyan]"
            )
            for rec in recommendations[:10]:
                console.print(f"  • {rec}")

    def export_validation_report(
        self, report: Dict[str, Any], format_type: str = "json"
    ):
        """Export validation report."""
        try:
            export_dir = Path(self.settings.exports_dir)
            export_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"validation_report_{timestamp}.{format_type}"
            filepath = export_dir / filename

            if format_type == "json":
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
            else:
                console.print(f"[red]❌ Unsupported export format: {format_type}[/red]")
                return False

            console.print(f"[green]✓[/green] Exported validation report to {filepath}")
            return True

        except Exception as e:
            console.print(f"[red]❌ Failed to export report: {e}[/red]")
            return False


async def main():
    console.print(
        Panel.fit(
            "[bold blue]🏫 University Validation & Milestone Tracker[/bold blue]\n"
            "Systematically validate each university and track progress",
            title="🔍 Validation System",
        )
    )

    validator = UniversityValidator()

    if not validator.connect_database():
        console.print("[red]❌ Cannot proceed without database connection[/red]")
        return

    console.print("\n[bold cyan]Choose validation action:[/bold cyan]")
    console.print("  [1] Validate all universities")
    console.print("  [2] Show existing validation results")
    console.print("  [3] Export validation report")

    choice = Prompt.ask("Enter your choice", choices=["1", "2", "3"])

    if choice == "1":
        check_websites = Confirm.ask("Check website accessibility? (may take longer)")

        console.print("\n[bold blue]🔄 Starting comprehensive validation...[/bold blue]")
        milestones = await validator.validate_all_universities(
            check_websites=check_websites
        )

        report = validator.generate_validation_report()
        validator.display_validation_results(report)

        if Confirm.ask("Export validation report?"):
            validator.export_validation_report(report)

    elif choice == "2":
        milestones = validator.load_existing_milestones()
        if milestones:
            report = validator.generate_validation_report()
            validator.display_validation_results(report)
        else:
            console.print("[yellow]⚠️ No existing validation results found[/yellow]")

    elif choice == "3":
        milestones = validator.load_existing_milestones()
        if milestones:
            report = validator.generate_validation_report()
            validator.export_validation_report(report)
        else:
            console.print("[yellow]⚠️ No validation data to export[/yellow]")


if __name__ == "__main__":
    asyncio.run(main())

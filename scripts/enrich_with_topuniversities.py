#!/usr/bin/env python
"""
Script to enrich existing university data with rankings from TopUniversities.com.

This script:
1. Fetches all universities from the database
2. Retrieves latest rankings from TopUniversities.com
3. Updates each university with fresh ranking data
4. Generates a comprehensive report

Usage:
    python scripts/enrich_with_topuniversities.py                    # Update all universities
    python scripts/enrich_with_topuniversities.py --university "Oxford"  # Update specific university
    python scripts/enrich_with_topuniversities.py --force-refresh    # Force fresh rankings fetch
    python scripts/enrich_with_topuniversities.py --output report.json  # Save report
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from database.mongodb import MongoDBConnection
from database.repositories import UniversityRepository
from models.university import University
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from services.ranking_service import RankingService

console = Console()


class EnrichmentResult:
    """Stores enrichment results for a single university."""

    def __init__(self, name: str):
        self.name = name
        self.success = False
        self.before_rank: int = None
        self.after_rank: int = None
        self.fields_updated: List[str] = []
        self.errors: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "success": self.success,
            "before_rank": self.before_rank,
            "after_rank": self.after_rank,
            "fields_updated": self.fields_updated,
            "errors": self.errors,
        }


class TopUniversitiesEnricher:
    """Enriches database universities with TopUniversities.com data."""

    def __init__(self, force_refresh: bool = False):
        self.force_refresh = force_refresh
        self.ranking_service = RankingService()
        self.db_connection = MongoDBConnection()
        self.university_repo = None
        self.results: Dict[str, EnrichmentResult] = {}

    async def __aenter__(self):
        """Context manager entry."""
        await self.db_connection.connect()
        self.university_repo = UniversityRepository(self.db_connection)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.db_connection.disconnect()

    async def enrich_university(self, university: University) -> EnrichmentResult:
        """Enrich a single university with TopUniversities data."""
        result = EnrichmentResult(university.name)
        result.before_rank = university.qs_world_ranking

        console.print(f"\n[cyan]Processing: {university.name}[/cyan]")

        try:
            # Get previous values
            before_country = university.country
            before_city = university.city

            # Update rankings
            updated_university = await self.ranking_service.update_university_rankings(
                university, force_refresh=self.force_refresh
            )

            # Track changes
            if updated_university.qs_world_ranking != result.before_rank:
                result.fields_updated.append("qs_world_ranking")
                result.after_rank = updated_university.qs_world_ranking
                console.print(
                    f"  [green]✓ Ranking: {result.before_rank or 'None'} → {result.after_rank}[/green]"
                )

            if updated_university.country != before_country:
                result.fields_updated.append("country")
                console.print(
                    f"  [green]✓ Country: {before_country or 'None'} → {updated_university.country}[/green]"
                )

            if updated_university.city != before_city:
                result.fields_updated.append("city")
                console.print(
                    f"  [green]✓ City: {before_city or 'None'} → {updated_university.city}[/green]"
                )

            # Save to database if changes were made
            if result.fields_updated:
                updated_university.updated_at = datetime.now()
                await self.university_repo.save(updated_university)
                result.success = True
                console.print(
                    f"  [bold green]✓ Saved {len(result.fields_updated)} updates[/bold green]"
                )
            else:
                result.success = True
                console.print("  [dim]No changes needed[/dim]")

        except Exception as e:
            error_msg = str(e)[:100]
            result.errors.append(error_msg)
            console.print(f"  [red]✗ Error: {error_msg}[/red]")

        return result

    async def enrich_all(
        self, university_filter: str = None
    ) -> Dict[str, EnrichmentResult]:
        """Enrich all universities (or filtered subset)."""
        console.print(
            Panel(
                f"[bold]TopUniversities.com Data Enrichment[/bold]\n"
                f"Force refresh: {self.force_refresh}\n"
                f"Filter: {university_filter or 'All universities'}",
                title="University Enrichment",
            )
        )

        # Fetch universities from database
        try:
            if university_filter:
                universities = await self.university_repo.find_by_name(
                    university_filter
                )
                if not universities:
                    # Try partial match
                    all_unis = await self.university_repo.get_all()
                    universities = [
                        u
                        for u in all_unis
                        if university_filter.lower() in u.name.lower()
                    ]
            else:
                universities = await self.university_repo.get_all()

            console.print(
                f"\n[bold]Found {len(universities)} universities to process[/bold]\n"
            )

            if not universities:
                console.print("[red]No universities found in database![/red]")
                return {}

            # Process each university
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "[cyan]Enriching universities...", total=len(universities)
                )

                for university in universities:
                    result = await self.enrich_university(university)
                    self.results[university.name] = result
                    progress.advance(task)

                    # Rate limiting
                    await asyncio.sleep(1)

        except Exception as e:
            console.print(f"[red]Error during enrichment: {e}[/red]")

        return self.results

    def generate_report(self) -> Dict[str, Any]:
        """Generate summary report of enrichment results."""
        total = len(self.results)
        success = sum(1 for r in self.results.values() if r.success)
        failed = total - success

        updated = sum(1 for r in self.results.values() if r.fields_updated)
        no_changes = sum(
            1 for r in self.results.values() if r.success and not r.fields_updated
        )

        total_fields_updated = sum(len(r.fields_updated) for r in self.results.values())

        # Count ranking updates
        ranking_updates = [
            r for r in self.results.values() if "qs_world_ranking" in r.fields_updated
        ]

        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_universities": total,
                "successful": success,
                "failed": failed,
                "updated": updated,
                "no_changes_needed": no_changes,
                "total_fields_updated": total_fields_updated,
                "ranking_updates": len(ranking_updates),
            },
            "universities": {
                name: result.to_dict() for name, result in self.results.items()
            },
        }

        return report

    def print_summary(self):
        """Print summary table of results."""
        console.print("\n")

        table = Table(title="Enrichment Results Summary")
        table.add_column("University", style="cyan", min_width=30)
        table.add_column("Status", justify="center")
        table.add_column("Before Rank", justify="right")
        table.add_column("After Rank", justify="right")
        table.add_column("Fields Updated", justify="center")

        for name, result in sorted(self.results.items()):
            status = (
                "[green]✓ SUCCESS[/green]" if result.success else "[red]✗ FAILED[/red]"
            )
            before = str(result.before_rank) if result.before_rank else "-"
            after = str(result.after_rank) if result.after_rank else "-"
            fields = str(len(result.fields_updated)) if result.fields_updated else "-"

            table.add_row(name[:35], status, before, after, fields)

        console.print(table)

        # Print summary stats
        report = self.generate_report()
        summary = report["summary"]

        console.print(
            Panel(
                f"[bold green]Successful: {summary['successful']}[/bold green] | "
                f"[bold red]Failed: {summary['failed']}[/bold red]\n"
                f"Updated: {summary['updated']} | "
                f"No changes: {summary['no_changes_needed']}\n"
                f"Total fields updated: {summary['total_fields_updated']}\n"
                f"Ranking updates: {summary['ranking_updates']}",
                title="Summary",
            )
        )

        # Show failed universities
        failed_unis = [r for r in self.results.values() if not r.success]
        if failed_unis:
            console.print("\n[bold red]Failed Universities:[/bold red]")
            for result in failed_unis[:10]:
                console.print(f"  [red]{result.name}[/red]")
                for error in result.errors[:2]:
                    console.print(f"    [dim]- {error}[/dim]")


async def main():
    parser = argparse.ArgumentParser(
        description="Enrich university data with TopUniversities.com rankings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/enrich_with_topuniversities.py                     # Update all universities
    python scripts/enrich_with_topuniversities.py --university "Oxford"  # Update specific university
    python scripts/enrich_with_topuniversities.py --force-refresh     # Force fresh data fetch
    python scripts/enrich_with_topuniversities.py --output report.json  # Save report
        """,
    )

    parser.add_argument(
        "--university", type=str, help="Filter universities by name (partial match)"
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force fresh data fetch, ignore cache",
    )
    parser.add_argument("--output", type=str, help="Save report to JSON file")

    args = parser.parse_args()

    try:
        async with TopUniversitiesEnricher(
            force_refresh=args.force_refresh
        ) as enricher:
            await enricher.enrich_all(university_filter=args.university)
            enricher.print_summary()

            # Save report if requested
            if args.output:
                report = enricher.generate_report()
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)

                console.print(f"\n[green]Report saved to: {output_path}[/green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Enrichment interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

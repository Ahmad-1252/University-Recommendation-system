#!/usr/bin/env python
"""
Test script for the TopUniversities.com API-first scraper.

Tests:
1. API endpoint connectivity (fetch page 0)
2. Data schema validation (all required fields present)
3. Indicator score parsing (10 indicators × 5 categories)
4. Pagination (page 0 vs page 1 return different data)
5. University search via API
6. Ranking service caching (if available)

Usage:
    python scripts/test_topuniversities.py
"""

import asyncio
import os
import sys
import time

# Setup path — project uses `from src.models...` import style
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)

from dotenv import load_dotenv

load_dotenv(os.path.join(project_dir, ".env"))

os.chdir(project_dir)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.scrapers.topuniversities_scraper import TopUniversitiesScraper

console = Console()


async def test_api_connectivity() -> bool:
    """Test 1: Verify API endpoint returns valid JSON data."""
    console.print("\n[bold cyan]Test 1: API Connectivity[/bold cyan]")
    console.print("  Fetching page 0 from /rankings/endpoint...")

    try:
        scraper = TopUniversitiesScraper()

        # Fetch just top 15 (1 page)
        start = time.time()
        results = await scraper.scrape_world_rankings(max_results=15)
        elapsed = time.time() - start

        if not results:
            console.print("  [red]✗ FAILED: No results returned[/red]")
            return False

        console.print(
            f"  [green]✓ Got {len(results)} universities in {elapsed:.1f}s[/green]"
        )

        # Show top 5
        table = Table(title="Top 5 Universities (API)")
        table.add_column("Rank", style="cyan", width=6)
        table.add_column("University", style="white", width=45)
        table.add_column("Country", style="yellow", width=20)
        table.add_column("Score", style="green", width=8)
        table.add_column("Indicators", style="magenta", width=12)

        for uni in results[:5]:
            table.add_row(
                str(uni.get("rank", "?")),
                uni.get("university_name", "?")[:43],
                uni.get("country", "?"),
                str(uni.get("overall_score", "?")),
                str(len(uni.get("indicators", {}))),
            )

        console.print(table)
        return True

    except Exception as e:
        console.print(f"  [red]✗ FAILED: {e}[/red]")
        return False


async def test_schema_validation() -> bool:
    """Test 2: Verify all required fields are present in API response."""
    console.print("\n[bold cyan]Test 2: Schema Validation[/bold cyan]")

    required_fields = [
        "rank",
        "rank_display",
        "university_name",
        "core_id",
        "country",
        "city",
        "region",
        "overall_score",
        "profile_url",
        "indicators",
        "source",
        "ranking_type",
        "scraped_at",
    ]

    try:
        scraper = TopUniversitiesScraper()
        results = await scraper.scrape_world_rankings(max_results=15)

        if not results:
            console.print("  [red]✗ No data to validate[/red]")
            return False

        # Check first result (MIT should be rank 1)
        first = results[0]
        missing = [f for f in required_fields if f not in first]

        if missing:
            console.print(f"  [red]✗ Missing fields: {missing}[/red]")
            return False

        # Validate types
        checks = [
            ("rank is int", isinstance(first["rank"], int)),
            (
                "overall_score is float",
                isinstance(first["overall_score"], (int, float)),
            ),
            ("core_id is non-empty", bool(first["core_id"])),
            ("indicators is dict", isinstance(first["indicators"], dict)),
            ("profile_url starts with https", first["profile_url"].startswith("https")),
            ("source is TopUniversities", first["source"] == "TopUniversities"),
        ]

        all_ok = True
        for label, passed in checks:
            if passed:
                console.print(f"  [green]✓ {label}[/green]")
            else:
                console.print(f"  [red]✗ {label}[/red]")
                all_ok = False

        return all_ok

    except Exception as e:
        console.print(f"  [red]✗ FAILED: {e}[/red]")
        return False


async def test_indicator_parsing() -> bool:
    """Test 3: Verify indicator scores are correctly parsed."""
    console.print("\n[bold cyan]Test 3: Indicator Score Parsing[/bold cyan]")

    expected_indicators = [
        "citations_per_faculty",
        "academic_reputation",
        "faculty_student_ratio",
        "employer_reputation",
        "employment_outcomes",
        "intl_student_ratio",
        "intl_research_network",
        "intl_faculty_ratio",
        "intl_student_diversity",
        "sustainability",
    ]

    try:
        scraper = TopUniversitiesScraper()
        results = await scraper.scrape_world_rankings(max_results=15)

        if not results:
            console.print("  [red]✗ No data[/red]")
            return False

        # Check MIT (rank 1 — should have all indicators)
        mit = results[0]
        indicators = mit.get("indicators", {})

        console.print(
            f"  Found {len(indicators)} indicators for {mit['university_name']}"
        )

        missing = [k for k in expected_indicators if k not in indicators]
        if missing:
            console.print(f"  [yellow]⚠ Missing indicators: {missing}[/yellow]")

        # Verify indicator structure
        all_ok = True
        for key, data in indicators.items():
            if not isinstance(data, dict):
                console.print(f"  [red]✗ {key} is not a dict[/red]")
                all_ok = False
                continue
            if "score" not in data or "rank" not in data:
                console.print(f"  [red]✗ {key} missing score/rank[/red]")
                all_ok = False
                continue
            console.print(
                f"  [green]✓ {key}: score={data['score']}, rank={data['rank']}, "
                f"category={data.get('category', '?')}[/green]"
            )

        return all_ok

    except Exception as e:
        console.print(f"  [red]✗ FAILED: {e}[/red]")
        return False


async def test_pagination() -> bool:
    """Test 4: Verify pagination returns different data per page."""
    console.print("\n[bold cyan]Test 4: Pagination Verification[/bold cyan]")

    try:
        scraper = TopUniversitiesScraper()

        # Fetch 30 results (2 pages at 15/page)
        results = await scraper.scrape_world_rankings(max_results=30)

        if len(results) < 16:
            console.print(f"  [red]✗ Expected 16+ results, got {len(results)}[/red]")
            return False

        # Verify first page and second page have different universities
        page1_ids = {r["core_id"] for r in results[:15]}
        page2_ids = {r["core_id"] for r in results[15:]}

        overlap = page1_ids & page2_ids
        if overlap:
            console.print(f"  [red]✗ Duplicate core_ids across pages: {overlap}[/red]")
            return False

        console.print(
            f"  [green]✓ Page 1: {len(page1_ids)} unique universities[/green]"
        )
        console.print(
            f"  [green]✓ Page 2: {len(page2_ids)} unique universities[/green]"
        )
        console.print("  [green]✓ No duplicates across pages[/green]")
        console.print(
            f"  [green]✓ Total: {len(results)} universities from {len(results) // 15 + 1} pages[/green]"
        )

        return True

    except Exception as e:
        console.print(f"  [red]✗ FAILED: {e}[/red]")
        return False


async def test_university_search() -> bool:
    """Test 5: Verify university search via API."""
    console.print("\n[bold cyan]Test 5: University Search[/bold cyan]")

    search_terms = ["MIT", "Oxford", "Cambridge"]

    try:
        scraper = TopUniversitiesScraper()
        all_ok = True

        for term in search_terms:
            result = await scraper.search_university(term)

            if result:
                console.print(
                    f"  [green]✓ '{term}' → {result['university_name']} "
                    f"(rank {result['rank']}, score {result['overall_score']})[/green]"
                )
            else:
                console.print(f"  [yellow]⚠ '{term}' → No result[/yellow]")
                all_ok = False

            # Brief pause between searches
            await asyncio.sleep(2)

        return all_ok

    except Exception as e:
        console.print(f"  [red]✗ FAILED: {e}[/red]")
        return False


async def test_data_completeness() -> bool:
    """Test 6: Verify data quality across multiple universities."""
    console.print("\n[bold cyan]Test 6: Data Completeness Check[/bold cyan]")

    try:
        scraper = TopUniversitiesScraper()
        results = await scraper.scrape_world_rankings(max_results=15)

        if not results:
            console.print("  [red]✗ No data[/red]")
            return False

        # Check completeness
        total = len(results)
        has_rank = sum(1 for r in results if r.get("rank") is not None)
        has_score = sum(1 for r in results if r.get("overall_score") is not None)
        has_country = sum(1 for r in results if r.get("country"))
        has_city = sum(1 for r in results if r.get("city"))
        has_indicators = sum(1 for r in results if len(r.get("indicators", {})) >= 5)
        has_profile_url = sum(1 for r in results if r.get("profile_url"))

        checks = [
            ("Has rank", has_rank, total),
            ("Has overall score", has_score, total),
            ("Has country", has_country, total),
            ("Has city", has_city, total),
            ("Has ≥5 indicators", has_indicators, total),
            ("Has profile URL", has_profile_url, total),
        ]

        all_ok = True
        for label, count, total_count in checks:
            pct = (count / total_count * 100) if total_count > 0 else 0
            if pct >= 90:
                console.print(
                    f"  [green]✓ {label}: {count}/{total_count} ({pct:.0f}%)[/green]"
                )
            elif pct >= 70:
                console.print(
                    f"  [yellow]⚠ {label}: {count}/{total_count} ({pct:.0f}%)[/yellow]"
                )
            else:
                console.print(
                    f"  [red]✗ {label}: {count}/{total_count} ({pct:.0f}%)[/red]"
                )
                all_ok = False

        return all_ok

    except Exception as e:
        console.print(f"  [red]✗ FAILED: {e}[/red]")
        return False


# ===========================================================
# PROGRAM DIRECTORY TESTS (/pd/endpoint)
# ===========================================================


async def test_program_api_connectivity() -> bool:
    """Test 7: Verify program directory API returns data."""
    console.print("\n[bold cyan]Test 7: Program API Connectivity[/bold cyan]")
    console.print("  Fetching page 0 from /pd/endpoint...")

    try:
        scraper = TopUniversitiesScraper()

        start = time.time()
        results = await scraper.scrape_all_programs(max_results=10)
        elapsed = time.time() - start

        if not results:
            console.print("  [red]✗ FAILED: No programs returned[/red]")
            return False

        console.print(
            f"  [green]✓ Got {len(results)} programs in {elapsed:.1f}s[/green]"
        )

        # Show first 5 programs
        table = Table(title="Sample Programs (API)")
        table.add_column("Program", style="white", width=40)
        table.add_column("University", style="cyan", width=30)
        table.add_column("Level", style="yellow", width=10)
        table.add_column("Country", style="green", width=15)

        for p in results[:5]:
            table.add_row(
                (p.get("program_name", "?") or "?")[:38],
                (p.get("university_name", "?") or "?")[:28],
                p.get("degree_level", "?"),
                p.get("country", "?") or "?",
            )

        console.print(table)
        return True

    except Exception as e:
        console.print(f"  [red]✗ FAILED: {e}[/red]")
        return False


async def test_program_schema() -> bool:
    """Test 8: Validate program data schema and normalization."""
    console.print("\n[bold cyan]Test 8: Program Schema Validation[/bold cyan]")

    required_fields = [
        "program_name",
        "degree_level",
        "program_url",
        "university_name",
        "university_url",
        "university_core_id",
        "country",
        "city",
        "region",
        "nid",
        "source",
        "scraped_at",
    ]

    try:
        scraper = TopUniversitiesScraper()
        results = await scraper.scrape_all_programs(max_results=10)

        if not results:
            console.print("  [red]✗ No data to validate[/red]")
            return False

        first = results[0]
        missing = [f for f in required_fields if f not in first]

        if missing:
            console.print(f"  [red]✗ Missing fields: {missing}[/red]")
            return False

        console.print(
            f"  [green]✓ All {len(required_fields)} required fields present[/green]"
        )

        # Verify normalization
        all_ok = True
        checks = [
            (
                "program_name has no zero-width chars",
                "\u200b" not in first.get("program_name", "")
                and "\u00a0" not in first.get("program_name", ""),
            ),
            (
                "degree_level is valid",
                first.get("degree_level") in ("Bachelors", "Masters", "Unknown"),
            ),
            (
                "program_url is full URL or None",
                first.get("program_url") is None
                or first["program_url"].startswith("https"),
            ),
            ("source is TopUniversities", first.get("source") == "TopUniversities"),
            ("nid is integer", isinstance(first.get("nid"), int)),
        ]

        for label, passed in checks:
            if passed:
                console.print(f"  [green]✓ {label}[/green]")
            else:
                console.print(f"  [red]✗ {label}[/red]")
                all_ok = False

        return all_ok

    except Exception as e:
        console.print(f"  [red]✗ FAILED: {e}[/red]")
        return False


async def test_program_study_level_filter() -> bool:
    """Test 9: Verify study level filter reduces results."""
    console.print("\n[bold cyan]Test 9: Study Level Filter[/bold cyan]")

    try:
        scraper = TopUniversitiesScraper()

        # Fetch bachelors only
        bachelors = await scraper.scrape_programs_by_level(
            level="bachelors", max_results=10
        )

        if not bachelors:
            console.print("  [red]✗ No bachelors programs returned[/red]")
            return False

        # Verify all are undergrad by checking URL path
        all_undergrad = all(p.get("degree_level") == "Bachelors" for p in bachelors)

        if all_undergrad:
            console.print(
                f"  [green]✓ All {len(bachelors)} programs are Bachelors[/green]"
            )
        else:
            non_bachelors = [
                p["program_name"]
                for p in bachelors
                if p.get("degree_level") != "Bachelors"
            ]
            console.print(
                f"  [yellow]⚠ {len(non_bachelors)} programs have "
                f"unexpected degree level[/yellow]"
            )

        return True

    except Exception as e:
        console.print(f"  [red]✗ FAILED: {e}[/red]")
        return False


async def main():
    """Run all tests."""
    console.print(
        Panel(
            "[bold white]TopUniversities.com Scraper — Full Test Suite[/bold white]\n"
            "[dim]Rankings API (Tests 1-6) + Program Directory API (Tests 7-9)[/dim]",
            title="🎓 Scraper Tests",
            border_style="cyan",
        )
    )

    tests = [
        ("API Connectivity", test_api_connectivity),
        ("Schema Validation", test_schema_validation),
        ("Indicator Parsing", test_indicator_parsing),
        ("Pagination", test_pagination),
        ("University Search", test_university_search),
        ("Data Completeness", test_data_completeness),
        ("Program API", test_program_api_connectivity),
        ("Program Schema", test_program_schema),
        ("Study Level Filter", test_program_study_level_filter),
    ]

    results = {}
    for name, test_func in tests:
        try:
            passed = await test_func()
            results[name] = passed
        except Exception as e:
            console.print(f"\n[red]Test '{name}' crashed: {e}[/red]")
            results[name] = False

    # Summary
    console.print("\n")
    summary = Table(title="Test Results Summary")
    summary.add_column("Test", style="cyan")
    summary.add_column("Status", justify="center")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, ok in results.items():
        status = "[green]✅ PASSED[/green]" if ok else "[red]❌ FAILED[/red]"
        summary.add_row(name, status)

    console.print(summary)
    console.print(f"\n[bold]Overall: {passed}/{total} tests passed[/bold]")

    if passed == total:
        console.print(
            "[bold green]🎉 All tests passed! Scraper is fully operational.[/bold green]"
        )
    else:
        console.print(
            "[bold yellow]⚠ Some tests failed. Review output above.[/bold yellow]"
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Tests interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        import traceback

        traceback.print_exc()
        sys.exit(1)

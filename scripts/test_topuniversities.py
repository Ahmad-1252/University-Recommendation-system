#!/usr/bin/env python
"""
Test script for TopUniversities.com scraper integration.

Tests:
1. Scraping world rankings
2. Searching for a university
3. Scraping university profile
4. Subject rankings
5. Ranking service caching

Usage:
    python scripts/test_topuniversities.py
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from scrapers.topuniversities_scraper import TopUniversitiesScraper
from services.ranking_service import RankingService
from models.university import University

console = Console()


async def test_world_rankings():
    """Test scraping world rankings."""
    console.print("\n[bold cyan]Test 1: World Rankings[/bold cyan]")
    
    try:
        async with TopUniversitiesScraper() as scraper:
            rankings = await scraper.scrape_world_rankings(max_results=10)
            
            if rankings:
                console.print(f"[green]✓ Successfully scraped {len(rankings)} universities[/green]")
                
                # Show first 5
                table = Table(title="Top 5 Universities")
                table.add_column("Rank", justify="right")
                table.add_column("University", style="cyan")
                table.add_column("Country", style="green")
                table.add_column("Score", justify="right")
                
                for ranking in rankings[:5]:
                    table.add_row(
                        str(ranking.get('rank', '-')),
                        ranking.get('university_name', 'Unknown')[:50],
                        ranking.get('country', '-'),
                        str(ranking.get('score', '-'))
                    )
                
                console.print(table)
                return True
            else:
                console.print("[red]✗ No rankings retrieved[/red]")
                return False
                
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        return False


async def test_university_search():
    """Test searching for a university."""
    console.print("\n[bold cyan]Test 2: University Search[/bold cyan]")
    
    universities_to_search = ["Oxford", "Cambridge", "MIT"]
    
    try:
        async with TopUniversitiesScraper() as scraper:
            for uni_name in universities_to_search:
                profile_url = await scraper.search_university(uni_name)
                
                if profile_url:
                    console.print(f"[green]✓ Found {uni_name}: {profile_url[:60]}...[/green]")
                else:
                    console.print(f"[yellow]⚠ Could not find profile for {uni_name}[/yellow]")
            
            return True
            
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        return False


async def test_subject_rankings():
    """Test scraping subject rankings."""
    console.print("\n[bold cyan]Test 3: Subject Rankings (Computer Science)[/bold cyan]")
    
    try:
        async with TopUniversitiesScraper() as scraper:
            rankings = await scraper.scrape_subject_rankings(
                subject="computer-science",
                max_results=5
            )
            
            if rankings:
                console.print(f"[green]✓ Successfully scraped {len(rankings)} CS programs[/green]")
                
                for ranking in rankings[:5]:
                    console.print(f"  {ranking.get('rank', '-')}. {ranking.get('university_name', 'Unknown')}")
                
                return True
            else:
                console.print("[yellow]⚠ No subject rankings retrieved (may require different selectors)[/yellow]")
                return False
                
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        return False


async def test_ranking_service():
    """Test ranking service with caching."""
    console.print("\n[bold cyan]Test 4: Ranking Service[/bold cyan]")
    
    try:
        service = RankingService()
        
        # First fetch (no cache)
        console.print("  Fetching rankings (no cache)...")
        rankings1 = await service.fetch_world_rankings(max_results=10)
        console.print(f"  [green]✓ Retrieved {len(rankings1)} rankings[/green]")
        
        # Second fetch (should use cache)
        console.print("  Fetching rankings (should use cache)...")
        rankings2 = await service.fetch_world_rankings(max_results=10)
        console.print(f"  [green]✓ Retrieved {len(rankings2)} rankings from cache[/green]")
        
        # Test university ranking lookup
        if rankings1:
            test_uni_name = rankings1[0].get('university_name', '')
            if test_uni_name:
                console.print(f"  Looking up ranking for: {test_uni_name}")
                ranking = await service.get_university_ranking(test_uni_name)
                
                if ranking:
                    console.print(f"  [green]✓ Found ranking: {ranking.get('rank')}[/green]")
                else:
                    console.print("  [yellow]⚠ Ranking not found[/yellow]")
        
        # Get cache summary
        summary = await service.get_rankings_summary()
        console.print(f"  [dim]Cache: {summary['cached_datasets']} datasets[/dim]")
        
        return True
        
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        return False


async def test_university_update():
    """Test updating a University object with rankings."""
    console.print("\n[bold cyan]Test 5: University Update[/bold cyan]")
    
    try:
        # Create a mock university
        university = University(
            name="University of Oxford",
            country="United Kingdom",
            city="Oxford"
        )
        
        console.print(f"  Before: QS Rank = {university.qs_world_ranking}")
        
        # Update with ranking service
        service = RankingService()
        updated_uni = await service.update_university_rankings(university)
        
        console.print(f"  After: QS Rank = {updated_uni.qs_world_ranking}")
        
        if updated_uni.qs_world_ranking:
            console.print(f"  [green]✓ Successfully updated ranking[/green]")
            return True
        else:
            console.print(f"  [yellow]⚠ No ranking found (may need name mapping)[/yellow]")
            return False
            
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        return False


async def main():
    """Run all tests."""
    console.print(Panel(
        "[bold]TopUniversities.com Integration Tests[/bold]\n"
        "Testing scraper and ranking service functionality",
        title="Test Suite"
    ))
    
    results = {
        "World Rankings": await test_world_rankings(),
        "University Search": await test_university_search(),
        "Subject Rankings": await test_subject_rankings(),
        "Ranking Service": await test_ranking_service(),
        "University Update": await test_university_update()
    }
    
    # Summary
    console.print("\n")
    summary_table = Table(title="Test Results Summary")
    summary_table.add_column("Test", style="cyan")
    summary_table.add_column("Result", justify="center")
    
    for test_name, passed in results.items():
        status = "[green]✓ PASSED[/green]" if passed else "[red]✗ FAILED[/red]"
        summary_table.add_row(test_name, status)
    
    console.print(summary_table)
    
    # Overall result
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    console.print(Panel(
        f"[bold]Passed: {passed_tests}/{total_tests}[/bold]\n"
        f"Success Rate: {(passed_tests/total_tests*100):.1f}%",
        title="Overall Results"
    ))
    
    if passed_tests == total_tests:
        console.print("\n[bold green]All tests passed! ✓[/bold green]")
    else:
        console.print("\n[bold yellow]Some tests failed. See details above.[/bold yellow]")


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

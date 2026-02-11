#!/usr/bin/env python
"""
This file is a duplicate; the canonical file is `tests/integration/test_universities_bottom_up.py`.
"""
print('Duplicate file - remove test_universities_bottom_up_moved.py')
import asyncio
import argparse
import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Compute project root and insert src into sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir
while project_root != project_root.parent:
    if (project_root / 'pyproject.toml').exists() or (project_root / 'setup.py').exists() or (project_root / 'src').exists():
        break
    project_root = project_root.parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.constants import UNIVERSITY_COURSE_DIRECTORIES
from scrapers.university_scraper import UniversityScraper
from scrapers.link_discoverer import LinkDiscoverer

console = Console()


class LevelTestResult:
    """Stores test results for a single level (undergraduate/graduate/phd)."""
    
    def __init__(self, level: str, url: str):
        self.level = level
        self.url = url
        self.links_discovered: int = 0
        self.programs_scraped: int = 0
        self.sample_programs: List[Dict[str, Any]] = []
        self.error: Optional[str] = None
        self.status: str = "pending"  # pending, success, failed


class UniversityTestResult:
    """Stores test results for a single university across all levels."""
    
    def __init__(self, name: str):
        self.name = name
        self.level_results: Dict[str, LevelTestResult] = {}
        self.total_links_discovered: int = 0
        self.total_programs_scraped: int = 0
        self.duration_seconds: float = 0.0
        self.status: str = "pending"  # pending, success, partial, failed
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "total_links_discovered": self.total_links_discovered,
            "total_programs_scraped": self.total_programs_scraped,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "levels": {
                level: {
                    "url": lr.url,
                    "links_discovered": lr.links_discovered,
                    "programs_scraped": lr.programs_scraped,
                    "status": lr.status,
                    "error": lr.error,
                    "sample_programs": lr.sample_programs
                }
                for level, lr in self.level_results.items()
            }
        }


class BottomUpUniversityTester:
    """Tests scraping capabilities for all universities, starting from the bottom."""
    
    # Universities in reverse order (bottom to top)
    UNIVERSITY_ORDER = [
        "National and Kapodistrian University of Athens",
        "University of Tartu",
        "Université PSL",
        "Utrecht University",
        "Leiden University",
        "KU Leuven",
        "Delft University of Technology",
        "University of Amsterdam",
        "Heidelberg University",
        "LMU Munich",
        "Technical University of Munich",
        "EPFL",
        "ETH Zurich",
        "University of Warwick",
        "University of Leeds",
        "University of Glasgow",
        "King's College London",
        "University of Manchester",
        "University of Edinburgh",
        "UCL",
        "Imperial College London",
        "University of Cambridge",
        "University of Oxford"
    ]
    
    def __init__(self, total_programs: int = 10, dry_run: bool = False):
        self.total_programs = total_programs
        self.dry_run = dry_run
        self.link_discoverer = LinkDiscoverer()
        self.scraper = UniversityScraper() if not dry_run else None
        self.results: Dict[str, UniversityTestResult] = {}
        
    def _get_directory_levels(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Extract all directory URLs by level from config."""
        levels = {}
        level_keys = ['undergraduate', 'graduate', 'phd', 'all', 
                      'graduate_sciences', 'graduate_arch', 'graduate_mgmt']
        
        for key in level_keys:
            if key in config and key not in ['base_url', 'program_url_pattern', 'pagination']:
                levels[key] = config[key]
        
        return levels
    
    async def test_university(self, name: str, config: Dict[str, Any]) -> UniversityTestResult:
        """Test scraping for a single university across ALL levels."""
        result = UniversityTestResult(name)
        start_time = datetime.now()
        
        console.print(f"\n{'='*60}")
        console.print(f"[bold cyan]Testing: {name}[/bold cyan]")
        console.print(f"{'='*60}")
        
        base_url = config.get('base_url', '')
        program_url_pattern = config.get('program_url_pattern', '')
        pagination = config.get('pagination', None)
        
        # Get all directory levels
        directory_levels = self._get_directory_levels(config)
        
        if not directory_levels:
            console.print(f"  [red]✗ No directory URLs found in config[/red]")
            result.status = "failed"
            return result
        
        console.print(f"  [dim]Base URL: {base_url}[/dim]")
        console.print(f"  [dim]Pattern: {program_url_pattern or 'None (heuristic mode)'}[/dim]")
        console.print(f"  [dim]Levels to test: {', '.join(directory_levels.keys())}[/dim]")
        
        # Calculate programs per level to distribute evenly
        num_levels = len(directory_levels)
        programs_per_level = max(1, self.total_programs // num_levels)
        remaining_programs = self.total_programs - (programs_per_level * num_levels)
        
        console.print(f"  [dim]Programs per level: ~{programs_per_level} (total target: {self.total_programs})[/dim]")
        
        total_scraped = 0
        total_links = 0
        successful_levels = 0
        
        for level_name, directory_url in directory_levels.items():
            level_result = LevelTestResult(level_name, directory_url)
            
            # Add extra program to first levels if we have remainder
            level_target = programs_per_level
            if remaining_programs > 0:
                level_target += 1
                remaining_programs -= 1
            
            console.print(f"\n  [yellow]📚 Level: {level_name.upper()}[/yellow]")
            console.print(f"     URL: {directory_url[:70]}...")
            console.print(f"     Target: {level_target} programs")
            
            try:
                # Discover program links
                links = await self.link_discoverer.discover_all_program_links(
                    directory_url=directory_url,
                    base_url=base_url,
                    program_url_pattern=program_url_pattern,
                    pagination=pagination
                )
                
                level_result.links_discovered = len(links)
                total_links += len(links)
                
                console.print(f"     [green]✓ Discovered: {len(links)} program links[/green]")
                
                if links:
                    # Show first 2 sample links
                    for link in links[:2]:
                        prog_name = link.get('program_name', 'Unknown')[:45]
                        console.print(f"       [dim]- {prog_name}[/dim]")
                
                # Scrape programs if not dry run
                if not self.dry_run and links:
                    programs_to_scrape = links[:level_target]
                    console.print(f"     [yellow]Scraping {len(programs_to_scrape)} programs...[/yellow]")
                    
                    scraped_count = 0
                    for link in programs_to_scrape:
                        try:
                            url = link.get('program_url', '')
                            if url:
                                program = await self.scraper.scrape_program_data(url, skip_validation=True)
                                if program:
                                    scraped_count += 1
                                    total_scraped += 1
                                    level_result.sample_programs.append({
                                        "program_name": program.program_name,
                                        "university_name": program.university_name,
                                        "degree_type": program.degree_type,
                                        "degree_level": program.degree_level,
                                        "program_category": program.program_category,
                                        "level_tested": level_name,
                                        "url": url
                                    })
                                    console.print(f"       [green]✓ {program.program_name[:50]}[/green]")
                                else:
                                    console.print(f"       [red]✗ Failed to extract[/red]")
                        except Exception as e:
                            console.print(f"       [red]✗ Error: {str(e)[:40]}[/red]")
                        
                        # Rate limiting
                        await asyncio.sleep(1)
                    
                    level_result.programs_scraped = scraped_count
                
                # Determine level status
                if level_result.links_discovered == 0:
                    level_result.status = "failed"
                elif self.dry_run:
                    level_result.status = "success"
                    successful_levels += 1
                elif level_result.programs_scraped > 0:
                    level_result.status = "success"
                    successful_levels += 1
                else:
                    level_result.status = "failed"
                    
            except Exception as e:
                level_result.error = str(e)[:200]
                level_result.status = "failed"
                console.print(f"     [red]✗ Error: {str(e)[:50]}[/red]")
            
            result.level_results[level_name] = level_result
        
        # Set final counts and status
        result.total_links_discovered = total_links
        result.total_programs_scraped = total_scraped
        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        
        # Determine overall status
        if successful_levels == 0:
            result.status = "failed"
        elif successful_levels == len(directory_levels):
            result.status = "success"
        else:
            result.status = "partial"
        
        # Print summary for this university
        status_color = {"success": "green", "partial": "yellow", "failed": "red"}.get(result.status, "white")
        console.print(f"\n  [bold {status_color}]Status: {result.status.upper()}[/bold {status_color}]")
        console.print(f"  Total Links: {total_links} | Scraped: {total_scraped} | Duration: {result.duration_seconds:.1f}s")
        
        return result
    
    async def test_all(self, limit: Optional[int] = None, skip: int = 0) -> Dict[str, UniversityTestResult]:
        """Test all universities in bottom-to-top order."""
        
        # Get universities in correct order
        universities_to_test = []
        for name in self.UNIVERSITY_ORDER:
            if name in UNIVERSITY_COURSE_DIRECTORIES:
                universities_to_test.append((name, UNIVERSITY_COURSE_DIRECTORIES[name]))
        
        # Apply skip
        if skip > 0:
            universities_to_test = universities_to_test[skip:]
        
        if limit:
            universities_to_test = universities_to_test[:limit]
        
        console.print(Panel(
            f"[bold]Testing {len(universities_to_test)} Universities (Bottom -> Top)[/bold]\n"
            f"Total programs per university: {self.total_programs}\n"
            f"Dry run: {self.dry_run}\n\n"
            f"Order: {', '.join([u[0].split()[0] for u in universities_to_test[:5]])}...",
            title="University Scraper Test - Bottom Up"
        ))
        
        for idx, (name, config) in enumerate(universities_to_test, 1):
            console.print(f"\n[bold magenta]>>> University {idx}/{len(universities_to_test)} <<<[/bold magenta]")
            result = await self.test_university(name, config)
            self.results[name] = result
            
            # Delay between universities
            if idx < len(universities_to_test):
                console.print(f"\n[dim]Waiting 3 seconds before next university...[/dim]")
                await asyncio.sleep(3)
        
        return self.results
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a summary report of all test results."""
        total = len(self.results)
        success = sum(1 for r in self.results.values() if r.status == "success")
        partial = sum(1 for r in self.results.values() if r.status == "partial")
        failed = sum(1 for r in self.results.values() if r.status == "failed")
        
        total_links = sum(r.total_links_discovered for r in self.results.values())
        total_scraped = sum(r.total_programs_scraped for r in self.results.values())
        total_duration = sum(r.duration_seconds for r in self.results.values())
        
        # Count level-specific stats
        level_stats = {}
        for result in self.results.values():
            for level_name, level_result in result.level_results.items():
                if level_name not in level_stats:
                    level_stats[level_name] = {"tested": 0, "success": 0, "links": 0, "scraped": 0}
                level_stats[level_name]["tested"] += 1
                if level_result.status == "success":
                    level_stats[level_name]["success"] += 1
                level_stats[level_name]["links"] += level_result.links_discovered
                level_stats[level_name]["scraped"] += level_result.programs_scraped
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "test_order": "bottom_to_top",
            "summary": {
                "total_universities": total,
                "success": success,
                "partial": partial,
                "failed": failed,
                "success_rate": f"{(success / total * 100):.1f}%" if total > 0 else "0%",
                "total_links_discovered": total_links,
                "total_programs_scraped": total_scraped,
                "total_duration_seconds": total_duration
            },
            "level_stats": level_stats,
            "universities": {name: result.to_dict() for name, result in self.results.items()}
        }
        
        return report
    
    def print_summary(self):
        """Print a comprehensive summary table of results."""
        console.print("\n" + "="*80)
        
        # Main results table
        table = Table(title="University Test Results (Bottom -> Top)")
        table.add_column("#", style="dim", width=3)
        table.add_column("University", style="cyan", min_width=30)
        table.add_column("Status", justify="center", width=12)
        table.add_column("Links", justify="right", width=8)
        table.add_column("Scraped", justify="right", width=8)
        table.add_column("Levels OK", justify="center", width=10)
        table.add_column("Duration", justify="right", width=10)
        
        for idx, name in enumerate(self.UNIVERSITY_ORDER, 1):
            if name not in self.results:
                continue
            result = self.results[name]
            
            status_style = {
                "success": "[green]✓ SUCCESS[/green]",
                "partial": "[yellow]⚠ PARTIAL[/yellow]",
                "failed": "[red]✗ FAILED[/red]",
            }.get(result.status, result.status)
            
            levels_ok = sum(1 for lr in result.level_results.values() if lr.status == "success")
            levels_total = len(result.level_results)
            
            table.add_row(
                str(idx),
                name[:35],
                status_style,
                str(result.total_links_discovered),
                str(result.total_programs_scraped),
                f"{levels_ok}/{levels_total}",
                f"{result.duration_seconds:.1f}s"
            )
        
        console.print(table)
        
        # Level breakdown table
        level_table = Table(title="Results by Level")
        level_table.add_column("Level", style="cyan")
        level_table.add_column("Universities Tested", justify="right")
        level_table.add_column("Success Rate", justify="right")
        level_table.add_column("Total Links", justify="right")
        level_table.add_column("Total Scraped", justify="right")
        
        level_stats = {}
        for result in self.results.values():
            for level_name, level_result in result.level_results.items():
                if level_name not in level_stats:
                    level_stats[level_name] = {"tested": 0, "success": 0, "links": 0, "scraped": 0}
                level_stats[level_name]["tested"] += 1
                if level_result.status == "success":
                    level_stats[level_name]["success"] += 1
                level_stats[level_name]["links"] += level_result.links_discovered
                level_stats[level_name]["scraped"] += level_result.programs_scraped
        
        for level_name, stats in sorted(level_stats.items()):
            success_rate = (stats["success"] / stats["tested"] * 100) if stats["tested"] > 0 else 0
            level_table.add_row(
                level_name,
                str(stats["tested"]),
                f"{success_rate:.1f}%",
                str(stats["links"]),
                str(stats["scraped"])
            )
        
        console.print(level_table)
        
        # Summary panel
        report = self.generate_report()
        summary = report['summary']
        
        console.print(Panel(
            f"[bold green]Success: {summary['success']}[/bold green] | "
            f"[bold yellow]Partial: {summary['partial']}[/bold yellow] | "
            f"[bold red]Failed: {summary['failed']}[/bold red]\n"
            f"Overall Success Rate: {summary['success_rate']}\n"
            f"Total Links Discovered: {summary['total_links_discovered']}\n"
            f"Total Programs Scraped: {summary['total_programs_scraped']}\n"
            f"Total Duration: {summary['total_duration_seconds']:.1f}s",
            title="Overall Summary"
        ))
        
        # Print failed universities
        failed_universities = [(n, r) for n, r in self.results.items() if r.status == "failed"]
        if failed_universities:
            console.print("\n[bold red]Failed Universities:[/bold red]")
            for name, result in failed_universities:
                console.print(f"  [red]✗ {name}[/red]")
                for level_name, lr in result.level_results.items():
                    if lr.status == "failed":
                        console.print(f"    [dim]{level_name}: {lr.error or 'No links found'}[/dim]")


async def main():
    parser = argparse.ArgumentParser(
        description="Test university scraping from bottom to top",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python tests/integration/test_universities_bottom_up.py                      # Test all universities
    python tests/integration/test_universities_bottom_up.py --limit 3            # Test first 3 from bottom
    python tests/integration/test_universities_bottom_up.py --skip 5             # Skip first 5 universities  
    python tests/integration/test_universities_bottom_up.py --programs 15        # Scrape 15 programs per university
    python tests/integration/test_universities_bottom_up.py --dry-run            # Only discover links
    python tests/integration/test_universities_bottom_up.py --output report.json # Save report
        """
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of universities to test (from bottom)"
    )
    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        help="Skip first N universities from bottom (default: 0)"
    )
    parser.add_argument(
        "--programs",
        type=int,
        default=10,
        help="Total programs to scrape per university across all levels (default: 10)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only discover links, don't actually scrape programs"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save detailed report to JSON file"
    )
    
    args = parser.parse_args()
    
    tester = BottomUpUniversityTester(
        total_programs=args.programs,
        dry_run=args.dry_run
    )
    
    try:
        await tester.test_all(limit=args.limit, skip=args.skip)
        tester.print_summary()
        
        # Save report if requested
        if args.output:
            report = tester.generate_report()
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            console.print(f"\n[green]Report saved to: {output_path}[/green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted by user[/yellow]")
        tester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())

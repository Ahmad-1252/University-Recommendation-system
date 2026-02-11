#!/usr/bin/env python
"""
Test script to verify scraping works for all universities in UNIVERSITY_COURSE_DIRECTORIES.

This script tests each university by:
1. Attempting to discover program links from the course directory
2. Scraping 10 programs to verify the pattern works
3. Generating a detailed report with success/failure status

Usage:
    python tests/integration/test_all_universities.py                     # Test all universities
    python tests/integration/test_all_universities.py --university "Oxford"  # Test specific university
    python tests/integration/test_all_universities.py --max-programs 5      # Test with 5 programs per university
    python tests/integration/test_all_universities.py --dry-run            # Only discover links, don't scrape
"""

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
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from core.constants import UNIVERSITY_COURSE_DIRECTORIES
from scrapers.university_scraper import UniversityScraper
from scrapers.link_discoverer import LinkDiscoverer

console = Console()


class UniversityTestResult:
    """Stores test results for a single university."""
    
    def __init__(self, name: str):
        self.name = name
        self.directory_urls_tested: List[str] = []
        self.links_discovered: int = 0
        self.programs_scraped: int = 0
        self.programs_saved: int = 0
        self.errors: List[str] = []
        self.sample_programs: List[Dict[str, Any]] = []
        self.duration_seconds: float = 0.0
        self.status: str = "pending"  # pending, success, partial, failed
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "directory_urls_tested": self.directory_urls_tested,
            "links_discovered": self.links_discovered,
            "programs_scraped": self.programs_scraped,
            "programs_saved": self.programs_saved,
            "errors": self.errors,
            "sample_programs": self.sample_programs,
            "duration_seconds": self.duration_seconds,
            "status": self.status
        }


class UniversityTester:
    """Tests scraping capabilities for all universities."""
    
    def __init__(self, max_programs: int = 10, dry_run: bool = False):
        self.max_programs = max_programs
        self.dry_run = dry_run
        self.link_discoverer = LinkDiscoverer()
        self.scraper = UniversityScraper() if not dry_run else None
        self.results: Dict[str, UniversityTestResult] = {}
        
    async def test_university(self, name: str, config: Dict[str, Any]) -> UniversityTestResult:
        """Test scraping for a single university."""
        result = UniversityTestResult(name)
        start_time = datetime.now()
        
        console.print(f"\n[bold cyan]Testing: {name}[/bold cyan]")
        
        base_url = config.get('base_url', '')
        program_url_pattern = config.get('program_url_pattern', '')
        pagination = config.get('pagination', None)
        
        # Get all directory URLs to test
        directory_levels = ['undergraduate', 'graduate', 'phd', 'all', 
                          'graduate_sciences', 'graduate_arch', 'graduate_mgmt']
        
        for level in directory_levels:
            if level in config and level not in ['base_url', 'program_url_pattern', 'pagination']:
                directory_url = config[level]
                result.directory_urls_tested.append(directory_url)
        
        # If no specific levels, check for 'all' key
        if not result.directory_urls_tested and 'all' in config:
            result.directory_urls_tested.append(config['all'])
        
        if not result.directory_urls_tested:
            result.errors.append("No directory URLs found in config")
            result.status = "failed"
            return result
        
        console.print(f"  [dim]Directory URLs: {len(result.directory_urls_tested)}[/dim]")
        console.print(f"  [dim]Pattern: {program_url_pattern or 'None (heuristic mode)'}[/dim]")
        
        total_links = 0
        total_scraped = 0
        
        for directory_url in result.directory_urls_tested[:2]:  # Test first 2 levels max
            try:
                console.print(f"  [yellow]Discovering from: {directory_url}[/yellow]")
                
                # Discover program links
                links = await self.link_discoverer.discover_all_program_links(
                    directory_url=directory_url,
                    base_url=base_url,
                    program_url_pattern=program_url_pattern,
                    pagination=pagination
                )
                
                console.print(f"  [green]✓ Found {len(links)} program links[/green]")
                total_links += len(links)
                
                if links:
                    # Show first 3 sample links
                    for link in links[:3]:
                        console.print(f"    [dim]- {link.get('program_name', 'Unknown')[:50]}[/dim]")
                        console.print(f"      [dim]{link.get('program_url', '')[:80]}[/dim]")
                
                # Scrape programs if not dry run
                if not self.dry_run and links:
                    programs_to_scrape = links[:self.max_programs]
                    console.print(f"  [yellow]Scraping {len(programs_to_scrape)} programs...[/yellow]")
                    
                    for link in programs_to_scrape:
                        try:
                            url = link.get('program_url', '')
                            if url:
                                program = await self.scraper.scrape_program_data(url, skip_validation=True)
                                if program:
                                    total_scraped += 1
                                    result.sample_programs.append({
                                        "program_name": program.program_name,
                                        "university_name": program.university_name,
                                        "degree_type": program.degree_type,
                                        "program_category": program.program_category,
                                        "url": url
                                    })
                                    console.print(f"    [green]✓ {program.program_name}[/green]")
                                else:
                                    console.print(f"    [red]✗ Failed to extract: {url[:60]}[/red]")
                        except Exception as e:
                            result.errors.append(f"Scrape error: {str(e)[:100]}")
                            console.print(f"    [red]✗ Error: {str(e)[:50]}[/red]")
                        
                        # Rate limiting
                        await asyncio.sleep(1)
                    
            except Exception as e:
                error_msg = f"Discovery error for {directory_url}: {str(e)[:100]}"
                result.errors.append(error_msg)
                console.print(f"  [red]✗ {error_msg}[/red]")
        
        # Set final counts
        result.links_discovered = total_links
        result.programs_scraped = total_scraped
        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        
        # Determine status
        if total_links == 0:
            result.status = "failed"
        elif self.dry_run:
            result.status = "success" if total_links > 0 else "failed"
        elif total_scraped >= self.max_programs * 0.5:
            result.status = "success"
        elif total_scraped > 0:
            result.status = "partial"
        else:
            result.status = "failed"
        
        status_color = {
            "success": "green",
            "partial": "yellow", 
            "failed": "red",
            "pending": "dim"
        }.get(result.status, "white")
        
        console.print(f"  [bold {status_color}]Status: {result.status.upper()}[/bold {status_color}]")
        console.print(f"  [dim]Duration: {result.duration_seconds:.1f}s[/dim]")
        
        return result
    
    async def test_all(self, university_filter: Optional[str] = None) -> Dict[str, UniversityTestResult]:
        """Test all universities (or filtered subset)."""
        universities_to_test = {}
        
        for name, config in UNIVERSITY_COURSE_DIRECTORIES.items():
            if university_filter:
                if university_filter.lower() not in name.lower():
                    continue
            universities_to_test[name] = config
        
        if not universities_to_test:
            console.print(f"[red]No universities found matching filter: {university_filter}[/red]")
            return {}
        
        console.print(Panel(
            f"[bold]Testing {len(universities_to_test)} Universities[/bold]\n"
            f"Max programs per university: {self.max_programs}\n"
            f"Dry run: {self.dry_run}",
            title="University Scraper Test"
        ))
        
        for name, config in universities_to_test.items():
            result = await self.test_university(name, config)
            self.results[name] = result
            
            # Small delay between universities
            await asyncio.sleep(2)
        
        return self.results
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a summary report of all test results."""
        total = len(self.results)
        success = sum(1 for r in self.results.values() if r.status == "success")
        partial = sum(1 for r in self.results.values() if r.status == "partial")
        failed = sum(1 for r in self.results.values() if r.status == "failed")
        
        total_links = sum(r.links_discovered for r in self.results.values())
        total_scraped = sum(r.programs_scraped for r in self.results.values())
        total_duration = sum(r.duration_seconds for r in self.results.values())
        
        report = {
            "generated_at": datetime.now().isoformat(),
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
            "universities": {name: result.to_dict() for name, result in self.results.items()}
        }
        
        return report
    
    def print_summary(self):
        """Print a summary table of results."""
        console.print("\n")
        
        table = Table(title="University Test Results Summary")
        table.add_column("University", style="cyan", min_width=25)
        table.add_column("Status", justify="center")
        table.add_column("Links Found", justify="right")
        table.add_column("Scraped", justify="right")
        table.add_column("Duration", justify="right")
        table.add_column("Errors", justify="center")
        
        for name, result in sorted(self.results.items(), key=lambda x: x[1].status):
            status_style = {
                "success": "[green]✓ SUCCESS[/green]",
                "partial": "[yellow]⚠ PARTIAL[/yellow]",
                "failed": "[red]✗ FAILED[/red]",
                "pending": "[dim]PENDING[/dim]"
            }.get(result.status, result.status)
            
            table.add_row(
                name[:30],
                status_style,
                str(result.links_discovered),
                str(result.programs_scraped),
                f"{result.duration_seconds:.1f}s",
                str(len(result.errors)) if result.errors else "-"
            )
        
        console.print(table)
        
        # Print summary stats
        report = self.generate_report()
        summary = report['summary']
        
        console.print(Panel(
            f"[bold green]Success: {summary['success']}[/bold green] | "
            f"[bold yellow]Partial: {summary['partial']}[/bold yellow] | "
            f"[bold red]Failed: {summary['failed']}[/bold red]\n"
            f"Success Rate: {summary['success_rate']}\n"
            f"Total Links: {summary['total_links_discovered']} | "
            f"Total Scraped: {summary['total_programs_scraped']}\n"
            f"Total Duration: {summary['total_duration_seconds']:.1f}s",
            title="Summary"
        ))
        
        # Print failed universities with errors
        failed_universities = [r for r in self.results.values() if r.status == "failed"]
        if failed_universities:
            console.print("\n[bold red]Failed Universities:[/bold red]")
            for result in failed_universities:
                console.print(f"  [red]{result.name}[/red]")
                for error in result.errors[:3]:
                    console.print(f"    [dim]- {error}[/dim]")


async def main():
    parser = argparse.ArgumentParser(
        description="Test scraping for all universities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python tests/integration/test_all_universities.py                      # Test all universities
    python tests/integration/test_all_universities.py --university "Oxford"   # Test specific university
    python tests/integration/test_all_universities.py --max-programs 5       # Test with 5 programs per university
    python tests/integration/test_all_universities.py --dry-run             # Only discover links, don't scrape
    python tests/integration/test_all_universities.py --output report.json   # Save report to file
        """
    )
    
    parser.add_argument(
        "--university",
        type=str,
        help="Filter universities by name (partial match)"
    )
    parser.add_argument(
        "--max-programs",
        type=int,
        default=10,
        help="Maximum programs to scrape per university (default: 10)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only discover links, don't actually scrape programs"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save report to JSON file"
    )
    
    args = parser.parse_args()
    
    tester = UniversityTester(
        max_programs=args.max_programs,
        dry_run=args.dry_run
    )
    
    try:
        await tester.test_all(university_filter=args.university)
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
#!/usr/bin/env python
"""
Test integration wrapper for existing test_all_universities script (moved from root).
"""
from pathlib import Path
import sys
import os

# Ensure src is on path (project root detection)
script_dir = Path(__file__).resolve().parent
project_root = script_dir
while project_root != project_root.parent:
    if (project_root / 'pyproject.toml').exists() or (project_root / 'setup.py').exists() or (project_root / 'src').exists():
        break
    project_root = project_root.parent

src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

from .. import test_all_universities as original_test

if __name__ == '__main__':
    import asyncio
    asyncio.run(original_test.main())

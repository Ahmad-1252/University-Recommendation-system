"""Script to run the university data scraper."""

import os
import sys
import asyncio
import logging

# Setup path FIRST - before any src imports
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, 'src')
sys.path.insert(0, src_dir)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(script_dir, '.env'))

# Change working directory to src for relative file paths
os.chdir(src_dir)

# Now imports work normally (path is already set up)
from rich.console import Console
from rich.table import Table

from core.config import get_settings
from core.constants import UNIVERSITY_URLS, UNIVERSITY_COURSE_DIRECTORIES, PROGRAM_CATEGORIES, DEGREE_LEVELS
from scrapers.university_scraper import UniversityScraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()


async def scrape_universities(urls: list, concurrent: int = 3):
    """Scrape multiple university URLs."""
    settings = get_settings()
    scraper = UniversityScraper()
    
    console.print(f"\\n[bold green]🎓 University Data Extraction[/bold green]")
    console.print(f"[cyan]URLs to scrape: {len(urls)}[/cyan]")
    console.print(f"[cyan]Concurrent requests: {concurrent}[/cyan]\\n")
    
    # Temporarily adjust concurrent limit
    original_limit = settings.scraping.max_concurrent_requests
    settings.scraping.max_concurrent_requests = concurrent
    
    try:
        results = await scraper.scrape_multiple_and_save(urls)
        
        # Show results
        successful = sum(1 for success in results.values() if success)
        failed = len(results) - successful
        
        console.print(f"\\n[bold green]✅ Scraping Completed![/bold green]")
        console.print(f"[green]Successful: {successful}[/green]")
        console.print(f"[red]Failed: {failed}[/red]")
        
        if failed > 0:
            console.print("\\n[yellow]Failed URLs:[/yellow]")
            for url, success in results.items():
                if not success:
                    console.print(f"  [red]✗[/red] {url}")
        
        console.print("\\n[bold green]Successful URLs:[/bold green]")
        for url, success in results.items():
            if success:
                console.print(f"  [green]✓[/green] {url}")
                
        return results
        
    except Exception as e:
        console.print(f"[red]Scraping failed: {e}[/red]")
        logger.exception("Scraping error")
        return {}
    finally:
        settings.scraping.max_concurrent_requests = original_limit


async def scrape_all_programs(university: str = None, degree_level: str = None, 
                              category: str = None, concurrent: int = 3, max_programs: int = 50):
    """Scrape all programs from university course directories."""
    settings = get_settings()
    scraper = UniversityScraper()
    
    console.print(f"\\n[bold green]🎓 Comprehensive University Program Extraction[/bold green]")
    
    # Filter universities if specified
    universities = UNIVERSITY_COURSE_DIRECTORIES
    if university:
        universities = {k: v for k, v in universities.items() if university.lower() in k.lower()}
    
    console.print(f"[cyan]Universities to scrape: {len(universities)}[/cyan]")
    
    # Show what we're scraping
    if degree_level:
        console.print(f"[cyan]Degree Level Filter: {degree_level}[/cyan]")
    if category:
        console.print(f"[cyan]Category Filter: {category}[/cyan]")
    
    console.print(f"[cyan]Program Categories: {', '.join(PROGRAM_CATEGORIES.keys())}[/cyan]")
    console.print(f"[cyan]Max programs per directory: {max_programs}[/cyan]\\n")
    
    all_urls = []
    
    # Collect all directory URLs based on filters
    for uni_name, directories in universities.items():
        levels_to_scrape = ["undergraduate", "graduate", "phd", "all"]
        if degree_level:
            level_map = {
                "undergraduate": ["undergraduate"],
                "graduate": ["graduate"],
                "masters": ["graduate"],
                "phd": ["phd"]
            }
            levels_to_scrape = level_map.get(degree_level.lower(), [degree_level.lower()])
        
        for level in levels_to_scrape:
            if level in directories:
                all_urls.append({
                    "university": uni_name,
                    "level": level,
                    "url": directories[level],
                    "base_url": directories.get("base_url", ""),
                    "program_url_pattern": directories.get("program_url_pattern", ""),
                    "pagination": directories.get("pagination", None)
                })
    
    console.print(f"[cyan]Total directory URLs to process: {len(all_urls)}[/cyan]\\n")
    
    # Create results table
    table = Table(title="Comprehensive Scraping Results")
    table.add_column("University", style="cyan")
    table.add_column("Level", style="magenta")
    table.add_column("Programs Found", justify="right")
    table.add_column("Programs Saved", justify="right", style="green")
    table.add_column("Categories", style="yellow")
    
    total_programs = 0
    total_saved = 0
    
    for item in all_urls:
        try:
            console.print(f"\\n[yellow]📚 Discovering programs from {item['university']} - {item['level']}...[/yellow]")
            
            # Use the new comprehensive scraping method
            stats = await scraper.scrape_all_programs_and_save(
                directory_url=item['url'],
                base_url=item['base_url'],
                category_filter=category,
                max_programs=max_programs,
                program_url_pattern=item.get('program_url_pattern', ''),
                pagination=item.get('pagination', None)
            )
            
            programs_found = stats.get('programs_scraped', 0)
            programs_saved = stats.get('programs_saved', 0)
            categories = stats.get('categories', {})
            
            total_programs += programs_found
            total_saved += programs_saved
            
            # Format categories for display
            cat_str = ", ".join([f"{k}:{v}" for k, v in categories.items()][:3])
            if len(categories) > 3:
                cat_str += "..."
            
            table.add_row(
                item['university'], 
                item['level'], 
                str(programs_found),
                str(programs_saved),
                cat_str or "N/A"
            )
            
            console.print(f"[green]✓ Found {programs_found} programs, saved {programs_saved}[/green]")
                
        except Exception as e:
            logger.error(f"Error scraping {item['university']}: {e}")
            table.add_row(item['university'], item['level'], "Error", "0", str(e)[:30])
            console.print(f"[red]✗ Error: {e}[/red]")
    
    console.print("\\n")
    console.print(table)
    console.print(f"\\n[bold green]✅ Comprehensive Scraping Completed![/bold green]")
    console.print(f"[green]Total Programs Found: {total_programs}[/green]")
    console.print(f"[green]Total Programs Saved: {total_saved}[/green]")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Scrape university program data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_scraper.py                           # Discover and scrape 20 programs per university (default)
  python run_scraper.py --max-programs 50         # Scrape up to 50 programs per university
  python run_scraper.py --university "University of Oxford"
  python run_scraper.py --level graduate
  python run_scraper.py --category "Computer Science"
  python run_scraper.py --single-url              # Legacy mode: scrape 1 program per university
        """
    )
    parser.add_argument('--urls', nargs='*', help='Specific URLs to scrape (enables single-url mode)')
    parser.add_argument('--concurrent', type=int, default=3, help='Concurrent requests')
    parser.add_argument('--limit', type=int, help='Limit number of universities to process')
    
    # Multi-program scraping options (now default behavior)
    parser.add_argument('--single-url', action='store_true', 
                        help='Legacy mode: scrape only one program URL per university (from UNIVERSITY_URLS)')
    parser.add_argument('--university', type=str, 
                        help='Filter by university name (partial match)')
    parser.add_argument('--level', type=str, choices=['undergraduate', 'graduate', 'masters', 'phd', 'all'],
                        default='all',
                        help='Filter by degree level (default: all)')
    parser.add_argument('--category', type=str,
                        help='Filter by program category (e.g., Business, Medical, Education)')
    parser.add_argument('--max-programs', type=int, default=20,
                        help='Maximum programs to scrape per university (default: 20)')
    
    args = parser.parse_args()
    
    # Single-URL legacy mode (when --single-url flag is used OR specific URLs provided)
    if args.single_url or args.urls:
        if args.urls:
            urls = args.urls
        else:
            urls = list(UNIVERSITY_URLS.values())
            console.print(f"[cyan]Using {len(urls)} pre-configured university URLs (single-url mode)[/cyan]")
        
        if args.limit:
            urls = urls[:args.limit]
            console.print(f"[yellow]Limited to first {args.limit} URLs[/yellow]")
        
        # Run legacy single-URL scraper
        asyncio.run(scrape_universities(urls, args.concurrent))
        return
    
    # Default: Comprehensive multi-program scraping mode
    console.print(f"[cyan]🚀 Multi-program discovery mode (default)[/cyan]")
    console.print(f"[cyan]   Max programs per university: {args.max_programs}[/cyan]")
    
    asyncio.run(scrape_all_programs(
        university=args.university,
        degree_level=args.level if args.level != 'all' else None,
        category=args.category,
        concurrent=args.concurrent,
        max_programs=args.max_programs
    ))


if __name__ == '__main__':
    main()
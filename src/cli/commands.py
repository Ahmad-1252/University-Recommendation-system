"""CLI command handlers for the University Recommendation System."""

import logging
import asyncio
from typing import Optional
from pathlib import Path
import click
from rich.console import Console

from ..core.config import get_settings
from ..scrapers.university_scraper import UniversityScraper
from ..database.repositories import ProgramRepository
from ..analyzers.quality_analyzer import QualityAnalyzer
from ..services.validation_service import ValidationService
from .dashboard import Dashboard
from .data_viewer import DataViewer

logger = logging.getLogger(__name__)
console = Console()


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, verbose):
    """University Recommendation System CLI"""
    # Set up logging
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Store shared objects in context
    ctx.ensure_object(dict)
    ctx.obj['settings'] = get_settings()
    ctx.obj['repository'] = ProgramRepository()
    ctx.obj['scraper'] = UniversityScraper()
    ctx.obj['analyzer'] = QualityAnalyzer()
    ctx.obj['validator'] = ValidationService()


@cli.command()
@click.pass_context
def dashboard(ctx):
    """Show interactive dashboard"""
    """Show the main dashboard"""
    dash = Dashboard()
    dash.run_interactive()


@cli.command()
@click.pass_context
def view(ctx):
    """View and browse program data"""
    """View program data interactively"""
    viewer = DataViewer()
    viewer.run_interactive()


@cli.command()
@click.argument('query', required=False)
@click.option('--university', '-u', help='Filter by university name')
@click.option('--country', '-c', help='Filter by country')
@click.option('--degree', '-d', help='Filter by degree type')
@click.option('--limit', '-l', default=50, help='Maximum results to show')
@click.pass_context
def search(ctx, query, university, country, degree, limit):
    """Search programs by various criteria"""
    repository = ctx.obj['repository']

    try:
        programs = repository.search(
            query=query,
            country=country,
            degree_type=degree,
            limit=limit
        )

        if not programs:
            console.print(f"[yellow]No programs found matching criteria[/yellow]")
            return

        viewer = DataViewer()
        viewer.view_programs_table(programs, f"Search Results ({len(programs)} found)")

    except Exception as e:
        console.print(f"[red]Search failed: {e}[/red]")


@cli.command()
@click.argument('urls', nargs=-1)
@click.option('--file', '-f', type=click.Path(exists=True), help='File containing URLs (one per line)')
@click.option('--concurrent', default=5, help='Number of concurrent scraping tasks')
@click.pass_context
def scrape(ctx, urls, file, concurrent):
    """Scrape program data from URLs"""
    scraper = ctx.obj['scraper']
    settings = ctx.obj['settings']

    # Get URLs from arguments or file
    if file:
        with open(file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]

    if not urls:
        console.print("[red]No URLs provided. Use --file or provide URLs as arguments[/red]")
        return

    console.print(f"[green]Starting scrape of {len(urls)} URLs (concurrent: {concurrent})[/green]")

    # Temporarily adjust concurrent limit
    original_limit = settings.scraping.max_concurrent_requests
    settings.scraping.max_concurrent_requests = concurrent

    try:
        # Run scraping
        results = asyncio.run(scraper.scrape_multiple_and_save(urls))

        # Show results
        successful = sum(1 for success in results.values() if success)
        failed = len(results) - successful

        console.print(f"[green]Scraping completed: {successful} successful, {failed} failed[/green]")

        if failed > 0:
            console.print("[yellow]Failed URLs:[/yellow]")
            for url, success in results.items():
                if not success:
                    console.print(f"  • {url}")

    except Exception as e:
        console.print(f"[red]Scraping failed: {e}[/red]")
    finally:
        # Restore original limit
        settings.scraping.max_concurrent_requests = original_limit


@cli.command()
@click.argument('urls', nargs=-1)
@click.option('--file', '-f', type=click.Path(exists=True), help='File containing URLs to validate')
@click.pass_context
def validate(ctx, urls, file):
    """Validate URLs for program content"""
    validator = ctx.obj['validator']

    # Get URLs from arguments or file
    if file:
        with open(file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]

    if not urls:
        console.print("[red]No URLs provided. Use --file or provide URLs as arguments[/red]")
        return

    console.print(f"[green]Validating {len(urls)} URLs...[/green]")

    try:
        results = asyncio.run(validator.validate_urls_batch(urls))

        valid_count = sum(1 for is_valid, _ in results.values() if is_valid)
        invalid_count = len(results) - valid_count

        console.print(f"[green]Validation completed: {valid_count} valid, {invalid_count} invalid[/green]")

        if invalid_count > 0:
            console.print("\n[yellow]Invalid URLs:[/yellow]")
            for url, (is_valid, reason) in results.items():
                if not is_valid:
                    console.print(f"  • {url}: {reason}")

    except Exception as e:
        console.print(f"[red]Validation failed: {e}[/red]")


@cli.command()
@click.option('--output', '-o', default='data/exports', help='Output directory')
@click.option('--format', '-f', 'formats', multiple=True, default=['csv', 'json'],
              type=click.Choice(['csv', 'json', 'xlsx']), help='Export formats')
@click.pass_context
def export(ctx, output, formats):
    """Export program data to files"""
    repository = ctx.obj['repository']

    try:
        programs = repository.get_all_programs()

        if not programs:
            console.print("[yellow]No programs found to export[/yellow]")
            return

        # Create output directory
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)

        console.print(f"[green]Exporting {len(programs)} programs to {output_path}[/green]")

        # Export in requested formats
        for fmt in formats:
            try:
                if fmt == 'csv':
                    self._export_csv(programs, output_path / 'programs.csv')
                elif fmt == 'json':
                    self._export_json(programs, output_path / 'programs.json')
                elif fmt == 'xlsx':
                    self._export_xlsx(programs, output_path / 'programs.xlsx')

                console.print(f"[green]✓ Exported {fmt.upper()} format[/green]")

            except Exception as e:
                console.print(f"[red]Failed to export {fmt.upper()}: {e}[/red]")

    except Exception as e:
        console.print(f"[red]Export failed: {e}[/red]")


@cli.command()
@click.pass_context
def analyze(ctx):
    """Analyze data quality and generate reports"""
    analyzer = ctx.obj['analyzer']

    try:
        console.print("[green]Analyzing data quality...[/green]")

        report = analyzer.generate_quality_report()

        # Display key metrics
        summary = report['summary']
        console.print(f"""
[bold blue]Quality Analysis Summary:[/bold blue]
• Total Programs: {summary['total_programs']}
• Overall Quality Score: {summary['overall_quality_score']:.1%}
• Data Completeness: {summary['data_completeness']:.1%}
• Critical Issues: {summary['critical_issues']}
• Recommendations: {summary['recommendations_count']}
        """)

        # Show top recommendations
        if report['quality_analysis']['recommendations']:
            console.print("\n[bold green]Top Recommendations:[/bold green]")
            for rec in report['quality_analysis']['recommendations'][:5]:
                console.print(f"• {rec}")

    except Exception as e:
        console.print(f"[red]Analysis failed: {e}[/red]")


@cli.command()
@click.pass_context
def universities(ctx):
    """Show university coverage statistics"""
    analyzer = ctx.obj['analyzer']

    try:
        coverage = analyzer.analyze_universities_coverage()

        if 'error' in coverage:
            console.print(f"[red]{coverage['error']}[/red]")
            return

        console.print(f"""
[bold blue]University Coverage:[/bold blue]
• Total Programs: {coverage['total_programs']}
• Universities Covered: {coverage['universities_covered']}
• Countries Covered: {coverage['countries_covered']}

[bold green]Top Universities by Program Count:[/bold green]
        """)

        for uni, count in list(coverage['top_universities'].items())[:10]:
            console.print(f"• {uni}: {count} programs")

        console.print(f"\n[bold green]Programs by Country:[/bold green]")
        for country, count in list(coverage['country_distribution'].items())[:10]:
            console.print(f"• {country}: {count} programs")

    except Exception as e:
        console.print(f"[red]Failed to get university stats: {e}[/red]")


@cli.command()
@click.pass_context
def config(ctx):
    """Show current configuration"""
    settings = ctx.obj['settings']

    console.print(f"""
[bold blue]Current Configuration:[/bold blue]

[green]Database:[/green]
• Connection: {settings.database.connection_string.replace(settings.database.connection_string.split('@')[0], '***') if '@' in settings.database.connection_string else '***'}
• Database: {settings.database.database_name}
• Collection: {settings.database.collection_name}

[green]LLM Service:[/green]
• Model: {settings.llm.model_name}
• Timeout: {settings.llm.timeout}s
• Max Retries: {settings.llm.max_retries}

[green]Scraping:[/green]
• Timeout: {settings.scraping.timeout}s
• Max Concurrent: {settings.scraping.max_concurrent_requests}
• Rate Limit Delay: {settings.scraping.rate_limit_delay}s

[green]Logging:[/green]
• Level: {settings.logging.level}
• File: {settings.logging.file_path or 'console only'}
    """)


def _export_csv(self, programs, filepath):
    """Export programs to CSV"""
    import csv

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        if programs:
            # Get all field names from the first program
            fieldnames = list(programs[0].model_dump().keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for program in programs:
                writer.writerow(program.model_dump())


def _export_json(self, programs, filepath):
    """Export programs to JSON"""
    import json

    data = {
        'metadata': {
            'total_programs': len(programs),
            'export_timestamp': str(asyncio.get_event_loop().time())
        },
        'programs': [program.model_dump() for program in programs]
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _export_xlsx(self, programs, filepath):
    """Export programs to Excel"""
    try:
        import pandas as pd

        # Convert programs to list of dicts
        data = [program.model_dump() for program in programs]

        # Flatten nested objects for Excel
        flattened_data = []
        for program in data:
            flat_program = {}
            for key, value in program.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        flat_program[f"{key}_{sub_key}"] = sub_value
                elif isinstance(value, list):
                    flat_program[key] = ', '.join(str(item) for item in value)
                else:
                    flat_program[key] = value
            flattened_data.append(flat_program)

        df = pd.DataFrame(flattened_data)
        df.to_excel(filepath, index=False, engine='openpyxl')

    except ImportError:
        console.print("[yellow]pandas not installed, skipping Excel export[/yellow]")


if __name__ == '__main__':
    cli()
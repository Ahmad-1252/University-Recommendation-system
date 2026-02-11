#!/usr/bin/env python
"""
Import QS World University Rankings from Excel file into database.

Creates entries in:
1. qs_rankings table - Complete ranking data with all scores
2. universities table - Basic university info (updates existing or creates new)

Usage:
    python scripts/import_rankings.py                    # Full import
    python scripts/import_rankings.py --dry-run          # Preview without saving
    python scripts/import_rankings.py --limit 100        # Import first 100 only
"""

import argparse
import logging
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.panel import Panel

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from database.mongodb import mongo_session
from models.qs_ranking import QSRanking, QSRankingScores
from models.university import University, generate_university_id

console = Console()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def normalize_institution_name(name: str) -> str:
    """Normalize institution name for matching."""
    if not name:
        return ""
    # Remove extra whitespace, lowercase, remove special chars
    normalized = re.sub(r'\s+', ' ', name.strip().lower())
    # Remove common suffixes for matching
    normalized = re.sub(r'\s*\(.*?\)\s*$', '', normalized)
    return normalized


def parse_rank(rank_value) -> Tuple[int, str]:
    """
    Parse rank value that might be a range like '501-510'.
    
    Returns:
        Tuple of (numeric_rank, display_rank)
    """
    if pd.isna(rank_value):
        return None, None
    
    rank_str = str(rank_value).strip()
    
    # Handle range like "501-510"
    if '-' in rank_str:
        parts = rank_str.split('-')
        try:
            return int(parts[0]), rank_str
        except ValueError:
            return None, rank_str
    
    # Handle single number
    try:
        rank_int = int(float(rank_str))
        return rank_int, str(rank_int)
    except ValueError:
        return None, rank_str


def parse_score(value) -> Optional[float]:
    """Parse score value, handling NaN and non-numeric values."""
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_integer(value) -> Optional[int]:
    """Parse integer value, handling NaN and non-numeric values."""
    if pd.isna(value):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def map_status_to_type(status: str) -> Optional[str]:
    """Map QS status to university type."""
    if pd.isna(status):
        return None
    
    status_lower = str(status).lower()
    
    if 'public' in status_lower:
        return 'public'
    elif 'private' in status_lower and 'not for profit' in status_lower:
        return 'private_nonprofit'
    elif 'private' in status_lower and 'for profit' in status_lower:
        return 'private_forprofit'
    elif 'private' in status_lower:
        return 'private'
    
    return None


def map_research_intensity(research: str) -> Optional[str]:
    """Map QS research code to research intensity."""
    if pd.isna(research):
        return None
    
    mapping = {
        'VH': 'very high',
        'H': 'high',
        'M': 'medium',
        'L': 'low'
    }
    
    return mapping.get(str(research).upper())


def determine_tier(rank: Optional[int]) -> Optional[str]:
    """Determine university tier based on rank."""
    if rank is None:
        return None
    
    if rank <= 50:
        return 'top'
    elif rank <= 200:
        return 'good'
    else:
        return 'standard'


def read_excel_file(file_path: str) -> pd.DataFrame:
    """Read and clean the Excel file."""
    console.print(f"[cyan]Reading Excel file: {file_path}[/cyan]")
    
    # Read Excel, skip first row (title row)
    df = pd.read_excel(file_path, skiprows=1)
    
    # The first row after skipping becomes header, but columns have weird names
    # Let's rename based on expected structure
    expected_columns = [
        'index', 'rank', 'previous_rank', 'institution_name', 'country',
        'region', 'size', 'focus', 'research', 'status',
        'ar_score', 'ar_rank', 'er_score', 'er_rank',
        'fsr_score', 'fsr_rank', 'cpf_score', 'cpf_rank',
        'ifr_score', 'ifr_rank', 'isr_score', 'isr_rank',
        'isd_score', 'isd_rank', 'irn_score', 'irn_rank',
        'eo_score', 'eo_rank', 'sus_score', 'sus_rank',
        'overall_score'
    ]
    
    if len(df.columns) >= len(expected_columns):
        df.columns = expected_columns[:len(df.columns)]
    
    # Skip the header row that might have column descriptions
    df = df[df['index'].apply(lambda x: str(x).isdigit() if pd.notna(x) else False)]
    
    console.print(f"[green]✓ Loaded {len(df)} universities from Excel[/green]")
    return df


def create_qs_ranking(row: pd.Series, year: int) -> QSRanking:
    """Create QSRanking object from Excel row."""
    rank, rank_display = parse_rank(row.get('rank'))
    prev_rank, _ = parse_rank(row.get('previous_rank'))
    
    # Calculate rank change
    rank_change = None
    if rank and prev_rank:
        rank_change = prev_rank - rank  # Positive = improved
    
    # Create scores object
    scores = QSRankingScores(
        academic_reputation=parse_score(row.get('ar_score')),
        academic_reputation_rank=parse_integer(row.get('ar_rank')),
        employer_reputation=parse_score(row.get('er_score')),
        employer_reputation_rank=parse_integer(row.get('er_rank')),
        faculty_student_ratio=parse_score(row.get('fsr_score')),
        faculty_student_ratio_rank=parse_integer(row.get('fsr_rank')),
        citations_per_faculty=parse_score(row.get('cpf_score')),
        citations_per_faculty_rank=parse_integer(row.get('cpf_rank')),
        international_faculty=parse_score(row.get('ifr_score')),
        international_faculty_rank=parse_integer(row.get('ifr_rank')),
        international_students=parse_score(row.get('isr_score')),
        international_students_rank=parse_integer(row.get('isr_rank')),
        international_research_network=parse_score(row.get('irn_score')),
        international_research_network_rank=parse_integer(row.get('irn_rank')),
        employment_outcomes=parse_score(row.get('eo_score')),
        employment_outcomes_rank=parse_integer(row.get('eo_rank')),
        sustainability=parse_score(row.get('sus_score')),
        sustainability_rank=parse_integer(row.get('sus_rank')),
    )
    
    institution_name = str(row.get('institution_name', '')).strip()
    
    return QSRanking(
        ranking_year=year,
        rank=rank or 9999,  # Default for unranked
        rank_display=rank_display or str(rank) or 'NR',
        previous_rank=prev_rank,
        rank_change=rank_change,
        institution_name=institution_name,
        institution_name_normalized=normalize_institution_name(institution_name),
        country=str(row.get('country', '')).strip(),
        region=str(row.get('region', '')).strip(),
        size=str(row.get('size', '')).strip() if pd.notna(row.get('size')) else None,
        focus=str(row.get('focus', '')).strip() if pd.notna(row.get('focus')) else None,
        research_intensity=map_research_intensity(row.get('research')),
        status=map_status_to_type(row.get('status')),
        overall_score=parse_score(row.get('overall_score')),
        scores=scores
    )


def create_university(row: pd.Series) -> University:
    """Create University object from Excel row for the universities table."""
    rank, _ = parse_rank(row.get('rank'))
    institution_name = str(row.get('institution_name', '')).strip()
    country = str(row.get('country', '')).strip()
    
    return University(
        name=institution_name,
        country=country,
        city="",  # Not available in Excel
        qs_world_ranking=rank,
        tier=determine_tier(rank),
        type=map_status_to_type(row.get('status')),
        research_intensity=map_research_intensity(row.get('research')),
    )


def import_rankings(
    file_path: str,
    dry_run: bool = False,
    limit: Optional[int] = None,
    year: int = 2026
) -> Dict[str, int]:
    """
    Import rankings from Excel to database.
    
    Args:
        file_path: Path to Excel file
        dry_run: If True, don't actually save to database
        limit: Maximum number of records to import
        year: Ranking year
        
    Returns:
        Dictionary with import statistics
    """
    stats = {
        'total_rows': 0,
        'qs_rankings_inserted': 0,
        'qs_rankings_updated': 0,
        'universities_inserted': 0,
        'universities_updated': 0,
        'errors': 0
    }
    
    # Read Excel
    df = read_excel_file(file_path)
    
    if limit:
        df = df.head(limit)
    
    stats['total_rows'] = len(df)
    
    if dry_run:
        console.print(Panel("[yellow]DRY RUN MODE - No data will be saved[/yellow]"))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console
    ) as progress:
        task = progress.add_task("Importing rankings...", total=len(df))
        
        for idx, row in df.iterrows():
            try:
                # Create QS Ranking record
                qs_ranking = create_qs_ranking(row, year)
                
                # Create University record
                university = create_university(row)
                
                if not dry_run:
                    with mongo_session() as conn:
                        # Insert/update QS ranking
                        qs_result = conn.qs_rankings_collection.replace_one(
                            {
                                "ranking_year": qs_ranking.ranking_year,
                                "institution_name_normalized": qs_ranking.institution_name_normalized
                            },
                            qs_ranking.to_dict(),
                            upsert=True
                        )
                        
                        if qs_result.upserted_id:
                            stats['qs_rankings_inserted'] += 1
                        else:
                            stats['qs_rankings_updated'] += 1
                        
                        # Insert/update University (match by name)
                        uni_result = conn.universities_collection.update_one(
                            {"name": university.name},
                            {
                                "$set": {
                                    "qs_world_ranking": university.qs_world_ranking,
                                    "tier": university.tier,
                                    "type": university.type,
                                    "research_intensity": university.research_intensity,
                                    "country": university.country,
                                    "updated_at": datetime.utcnow()
                                },
                                "$setOnInsert": {
                                    "university_id": generate_university_id(university.name),
                                    "name": university.name,
                                    "city": "",
                                    "created_at": datetime.utcnow()
                                }
                            },
                            upsert=True
                        )
                        
                        if uni_result.upserted_id:
                            stats['universities_inserted'] += 1
                        elif uni_result.modified_count > 0:
                            stats['universities_updated'] += 1
                else:
                    # Dry run - just count
                    stats['qs_rankings_inserted'] += 1
                    stats['universities_inserted'] += 1
                
            except Exception as e:
                logger.error(f"Error processing row {idx}: {e}")
                stats['errors'] += 1
            
            progress.update(task, advance=1)
    
    return stats


def display_results(stats: Dict[str, int], dry_run: bool = False):
    """Display import results."""
    table = Table(title="Import Results" + (" (DRY RUN)" if dry_run else ""))
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="green")
    
    table.add_row("Total Rows Processed", str(stats['total_rows']))
    table.add_row("─" * 20, "─" * 10)
    table.add_row("QS Rankings Inserted", str(stats['qs_rankings_inserted']))
    table.add_row("QS Rankings Updated", str(stats['qs_rankings_updated']))
    table.add_row("Universities Inserted", str(stats['universities_inserted']))
    table.add_row("Universities Updated", str(stats['universities_updated']))
    table.add_row("─" * 20, "─" * 10)
    table.add_row("Errors", str(stats['errors']))
    
    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="Import QS Rankings from Excel")
    parser.add_argument(
        "--file",
        default="data/2026 QS World University Rankings 1.3 (For qs.com).xlsx",
        help="Path to Excel file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview import without saving to database"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of records to import"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2026,
        help="Ranking year (default: 2026)"
    )
    
    args = parser.parse_args()
    
    console.print(Panel(
        "[bold]QS World University Rankings Importer[/bold]\n"
        f"File: {args.file}\n"
        f"Year: {args.year}\n"
        f"Dry Run: {args.dry_run}",
        title="Configuration"
    ))
    
    if not os.path.exists(args.file):
        console.print(f"[red]Error: File not found: {args.file}[/red]")
        sys.exit(1)
    
    stats = import_rankings(
        file_path=args.file,
        dry_run=args.dry_run,
        limit=args.limit,
        year=args.year
    )
    
    display_results(stats, args.dry_run)
    
    if stats['errors'] > 0:
        console.print(f"[yellow]Warning: {stats['errors']} errors occurred during import[/yellow]")
    else:
        console.print("[green]✓ Import completed successfully![/green]")


if __name__ == "__main__":
    main()

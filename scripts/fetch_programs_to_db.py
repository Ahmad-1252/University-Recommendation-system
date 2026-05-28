"""
TopUniversities Program Pipeline — Fetch → Clean → Save to MongoDB
==================================================================
Fetches programs from TopUniversities.com (API + optional deep page scrape),
cleans the data into UniversityProgram Pydantic models, and saves to MongoDB.

Usage:
    # Quick: API-only (16 fields, fast)
    python scripts/fetch_programs_to_db.py --count 100

    # Full: API + deep page scrape (26 fields, slower)
    python scripts/fetch_programs_to_db.py --count 50 --deep

    # Filter by level
    python scripts/fetch_programs_to_db.py --count 200 --level masters

    # Save raw JSON alongside DB insert
    python scripts/fetch_programs_to_db.py --count 100 --json output/programs.json
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.mongodb import get_mongo_connection
from src.database.repositories import ProgramRepository
from src.models.university import (
    LanguageProficiency,
    Rankings,
    TuitionFees,
    UniversityProgram,
    generate_university_id,
)
from src.scrapers.topuniversities_scraper import TopUniversitiesScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Data Cleaning / Mapping
# ------------------------------------------------------------------


def parse_duration_years(duration_str: Optional[str]) -> Optional[float]:
    """
    Convert duration string to numeric years.

    Examples:
        "12 months" → 1.0
        "24 months" → 2.0
        "2 years"   → 2.0
        "18 months" → 1.5
        "48 months" → 4.0
        "9 months"  → 0.75
    """
    if not duration_str:
        return None
    text = duration_str.lower().strip()

    # Try months
    m = re.search(r"(\d+)\s*month", text)
    if m:
        months = int(m.group(1))
        return round(months / 12, 2)

    # Try years
    m = re.search(r"(\d+(?:\.\d+)?)\s*year", text)
    if m:
        return float(m.group(1))

    # Try weeks
    m = re.search(r"(\d+)\s*week", text)
    if m:
        return round(int(m.group(1)) / 52, 2)

    return None


def parse_tuition_fee(fee_str: Optional[str]) -> Dict[str, Any]:
    """
    Extract numeric fee and currency from a fee string.

    Examples:
        "43,800 GBP" → {"amount": 43800, "currency": "GBP"}
        "£9,250"     → {"amount": 9250, "currency": "GBP"}
        "$55,000"    → {"amount": 55000, "currency": "USD"}
    """
    if not fee_str:
        return {"amount": None, "currency": "USD"}

    text = fee_str.strip()

    # Detect currency
    currency = "USD"
    if "GBP" in text or "£" in text:
        currency = "GBP"
    elif "EUR" in text or "€" in text:
        currency = "EUR"
    elif "AUD" in text:
        currency = "AUD"
    elif "CAD" in text:
        currency = "CAD"
    elif "SGD" in text:
        currency = "SGD"
    elif "USD" in text or "$" in text:
        currency = "USD"

    # Extract number
    numbers = re.findall(r"[\d,]+(?:\.\d+)?", text)
    if numbers:
        # Take the largest number (likely the international fee)
        amounts = [int(n.replace(",", "").split(".")[0]) for n in numbers]
        return {"amount": max(amounts), "currency": currency}

    return {"amount": None, "currency": currency}


def parse_qs_ranking(rank_str: Optional[str]) -> Optional[int]:
    """
    Extract numeric ranking from string like '#3', '3', '51-100'.
    For ranges, returns the lower bound.
    """
    if not rank_str:
        return None
    text = rank_str.strip().lstrip("#")

    # Range: "51-100" → 51
    m = re.match(r"(\d+)\s*[-–]\s*\d+", text)
    if m:
        return int(m.group(1))

    m = re.match(r"(\d+)", text)
    if m:
        return int(m.group(1))

    return None


def parse_score_number(val: Optional[str]) -> Optional[float]:
    """Extract numeric value from score string like '304+', '3.7+', '7+'."""
    if not val:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", val.strip())
    return float(m.group(1)) if m else None


def scraped_to_program(raw: Dict[str, Any]) -> Optional[UniversityProgram]:
    """
    Convert a raw scraped dictionary into a validated UniversityProgram.

    Maps scraper fields to the Pydantic model, with:
    - Automatic degree_type normalization (MSc → Master of Science)
    - Automatic degree_level normalization (Masters → Masters)
    - Automatic program_category normalization (Computer Science → Computer Science)
    - Duration conversion (12 months → 1.0 years)
    - Structured tuition fees (domestic/international separate columns)
    - Structured admission scores (GRE, GPA, TOEFL, IELTS, PTE)
    - Ranking extraction (#3 → integer 3)
    """

    uni_name = (
        raw.get("university_name") or raw.get("uni_name") or raw.get("jsonld_provider")
    )
    prog_name = raw.get("program_name")
    country = raw.get("country")
    city = raw.get("city")

    # Skip records missing required fields
    if not uni_name or not prog_name or not country or not city:
        logger.warning(
            f"Skipping incomplete record: uni={uni_name}, prog={prog_name}, "
            f"country={country}, city={city}"
        )
        return None

    # --- Duration ---
    duration = parse_duration_years(raw.get("duration"))

    # --- Tuition Fees (structured: domestic/international separate) ---
    fee_currency = raw.get("fee_currency") or "USD"

    # Parse domestic fee
    domestic_fee = parse_tuition_fee(raw.get("fee_domestic"))
    # Parse international fee
    international_fee = parse_tuition_fee(raw.get("fee_international"))

    # Fallback to fee_domestic if international is missing, or summary if available
    if domestic_fee["amount"] is None and international_fee["amount"] is None:
        fallback = parse_tuition_fee(raw.get("tuition_fee_summary"))
        international_fee = fallback
        fee_currency = fallback.get("currency", fee_currency)

    tuition = TuitionFees(
        domestic_per_year=domestic_fee["amount"],
        international_per_year=international_fee["amount"],
        currency=fee_currency,
    )

    # --- Admission Scores (structured) ---
    toefl_val = parse_score_number(raw.get("toefl_score"))
    ielts_val = parse_score_number(raw.get("ielts_score"))
    pte_val = parse_score_number(raw.get("pte_score"))
    duolingo_val = parse_score_number(raw.get("duolingo_score"))
    gre_required = raw.get("gre_score") is not None

    language_req = LanguageProficiency(
        toefl_min=int(toefl_val) if toefl_val else None,
        ielts_min=ielts_val,
        pte_min=int(pte_val) if pte_val else None,
        duolingo_min=int(duolingo_val) if duolingo_val else None,
        gre_required=gre_required if gre_required else None,
    )

    # GPA requirement
    gpa_val = parse_score_number(raw.get("bachelor_gpa"))

    # --- Rankings ---
    qs_rank = parse_qs_ranking(raw.get("qs_subject_ranking"))
    rank_position = raw.get("rankings_position")
    if isinstance(rank_position, str):
        rank_position = parse_qs_ranking(rank_position)

    rankings = Rankings(
        qs_world_ranking=rank_position if isinstance(rank_position, int) else None,
        subject_ranking_cs=qs_rank if qs_rank else None,
    )

    # --- Degree type ---
    degree_type = (
        raw.get("degree_type")
        or raw.get("degree_level")
        or raw.get("study_level")
        or "Other"
    )

    # --- Program category ---
    category_source = (
        raw.get("main_subject")
        or raw.get("main_subject_area")
        or raw.get("subject_area")
        or prog_name
    )

    # --- Description ---
    description = (
        raw.get("description")
        or raw.get("jsonld_description")
        or raw.get("program_description")
        or ""
    )

    # --- Source URL ---
    source_url = raw.get("program_url") or raw.get("source_url")

    # --- Confidence score based on field completeness ---
    filled = sum(1 for v in raw.values() if v is not None and v != "")
    total_fields = max(len(raw), 38)  # 38 fields with structured extraction
    confidence = min(1.0, round(filled / total_fields, 2))

    try:
        program = UniversityProgram(
            university_id=generate_university_id(uni_name),
            university_name=uni_name,
            program_name=prog_name,
            degree_type=degree_type,  # auto-normalized by validator
            degree_level=raw.get("degree_level", "Masters"),  # auto-normalized
            program_category=category_source,  # auto-normalized
            country=country,
            city=city,
            duration_years=duration,
            program_description=description,
            tuition_fees=tuition,
            language_requirements=language_req,
            gpa_requirement_min=gpa_val if gpa_val and gpa_val <= 4.0 else None,
            rankings=rankings,
            source_url=source_url,
            confidence_score=confidence,
            last_updated=datetime.utcnow(),
        )
        return program
    except Exception as e:
        logger.warning(f"Validation failed for {prog_name} @ {uni_name}: {e}")
        return None


# ------------------------------------------------------------------
# Main Pipeline
# ------------------------------------------------------------------


async def fetch_and_save(
    count: Optional[int] = 100,
    level: Optional[str] = None,
    deep: bool = False,
    json_path: Optional[str] = None,
):
    """
    Main pipeline: Fetch → Clean → Save.

    Args:
        count: Number of programs to fetch
        level: Study level filter (bachelors / masters / None=all)
        deep: If True, do two-stage extraction (API + page scrape)
        json_path: Optional path to save raw JSON output
    """
    scraper = TopUniversitiesScraper()

    # ---- Stage 1: Fetch ----
    logger.info(f"{'='*60}")
    logger.info(f"Fetching {count} programs (level={level or 'all'}, deep={deep})")
    logger.info(f"{'='*60}")

    def on_progress(done, total):
        if done % 10 == 0 or done == total:
            logger.info(f"  Progress: {done}/{total}")

    if deep:
        raw_programs = await scraper.scrape_programs_with_details(
            max_programs=count,
            study_level=level,
            on_progress=on_progress,
        )
    else:
        if level:
            raw_programs = await scraper.scrape_programs_by_level(
                level=level,
                max_results=count,
                on_progress=on_progress,
            )
        else:
            raw_programs = await scraper.scrape_all_programs(
                max_results=count,
                on_progress=on_progress,
            )

    logger.info(f"Fetched {len(raw_programs)} raw programs")

    # ---- Optional: Save raw JSON (before cleaning) ----
    raw_json_path = getattr(args, "raw_json", None) if "args" in dir() else None
    if raw_json_path:
        os.makedirs(os.path.dirname(raw_json_path) or ".", exist_ok=True)
        with open(raw_json_path, "w", encoding="utf-8") as f:
            json.dump(raw_programs, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Raw JSON saved to {raw_json_path}")

    # ---- Stage 2: Clean & Validate ----
    logger.info(f"\nCleaning {len(raw_programs)} programs...")
    programs: List[UniversityProgram] = []
    skipped = 0

    for raw in raw_programs:
        program = scraped_to_program(raw)
        if program:
            programs.append(program)
        else:
            skipped += 1

    logger.info(f"Validated: {len(programs)} programs ({skipped} skipped)")

    if not programs:
        logger.error("No valid programs to save — check scraper output")
        return

    # ---- Optional: Save CLEANED JSON (after validation) ----
    if json_path:
        os.makedirs(os.path.dirname(json_path) or ".", exist_ok=True)
        # Serialize validated UniversityProgram models with all structured fields
        cleaned_data = [p.model_dump(mode="json") for p in programs]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Cleaned JSON saved to {json_path} ({len(cleaned_data)} records)")

    # ---- Stage 3: Save to MongoDB ----
    logger.info(f"\nSaving {len(programs)} programs to MongoDB...")
    try:
        repo = ProgramRepository()

        # Test connection first
        conn = get_mongo_connection()
        conn.health_check()
        logger.info("MongoDB connection healthy")

        results = repo.save_many(programs)
        logger.info(
            f"Database results: "
            f"{results['inserted']} inserted, "
            f"{results['updated']} updated, "
            f"{results['failed']} failed"
        )

        # Show DB stats
        stats = repo.get_statistics()
        logger.info("\nDatabase Statistics:")
        logger.info(f"  Total programs: {stats.get('total_programs', '?')}")
        logger.info(f"  Countries:      {stats.get('unique_countries', '?')}")
        logger.info(f"  Universities:   {stats.get('unique_universities', '?')}")

    except Exception as e:
        logger.error(f"Database save failed: {e}")
        logger.info("Programs were fetched and cleaned but NOT saved to DB.")
        logger.info("Make sure MongoDB is running on localhost:27017")
        raise

    # ---- Summary ----
    logger.info(f"\n{'='*60}")
    logger.info("PIPELINE COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"  Fetched:   {len(raw_programs)} raw programs")
    logger.info(f"  Validated: {len(programs)} clean programs")
    logger.info(f"  Skipped:   {skipped} incomplete records")
    logger.info(f"  Inserted:  {results['inserted']}")
    logger.info(f"  Updated:   {results['updated']}")
    logger.info(f"  Failed:    {results['failed']}")
    if json_path:
        logger.info(f"  JSON file: {json_path}")

    # Show sample record
    sample = programs[0]
    logger.info("\nSample saved record:")
    logger.info(f"  Program:      {sample.program_name}")
    logger.info(f"  University:   {sample.university_name}")
    logger.info(f"  Degree:       {sample.degree_type} ({sample.degree_level})")
    logger.info(f"  Category:     {sample.program_category}")
    logger.info(f"  Country:      {sample.country}, {sample.city}")
    logger.info(f"  Duration:     {sample.duration_years} years")
    logger.info(
        f"  Tuition:      dom={sample.tuition_fees.domestic_per_year}, intl={sample.tuition_fees.international_per_year} {sample.tuition_fees.currency}"
    )
    logger.info(f"  IELTS:        {sample.language_requirements.ielts_min}")
    logger.info(f"  TOEFL:        {sample.language_requirements.toefl_min}")
    logger.info(f"  GPA:          {sample.gpa_requirement_min}")
    logger.info(f"  Completeness: {sample.data_completeness:.0%}")
    logger.info(f"  Confidence:   {sample.confidence_score:.0%}")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch TopUniversities programs and save to MongoDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/fetch_programs_to_db.py --count 100
  python scripts/fetch_programs_to_db.py --count 50 --deep
  python scripts/fetch_programs_to_db.py --count 200 --level masters
  python scripts/fetch_programs_to_db.py --count 100 --json output/programs.json
        """,
    )
    parser.add_argument(
        "--count",
        "-c",
        type=int,
        default=100,
        help="Number of programs to fetch (default: 100)",
    )
    parser.add_argument(
        "--level", "-l", choices=["bachelors", "masters"], help="Filter by study level"
    )
    parser.add_argument(
        "--deep",
        "-d",
        action="store_true",
        help="Enable deep extraction (API + page scrape, 26 fields)",
    )
    parser.add_argument(
        "--json", "-j", type=str, default=None, help="Path to save raw JSON output"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch ALL available programs (overrides --count)",
    )

    args = parser.parse_args()

    final_count = None if args.all else args.count

    asyncio.run(
        fetch_and_save(
            count=final_count,
            level=args.level,
            deep=args.deep,
            json_path=args.json,
        )
    )


if __name__ == "__main__":
    main()

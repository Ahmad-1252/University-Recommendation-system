"""Import TopUniversities scraped data into the Recommendation System MongoDB.

Usage:
    # Dry run — validate and print stats without writing to DB
    python scripts/import_topuniversities.py --dry-run

    # Import universities only (fast — 6,864 records)
    python scripts/import_topuniversities.py --universities-only

    # Import universities + 1,000 programs
    python scripts/import_topuniversities.py

    # Import with custom paths
    python scripts/import_topuniversities.py \\
        --unis-jsonl "C:/path/to/universities.jsonl" \\
        --programs-json "C:/path/to/programs.json"

    # Print tier distribution after import
    python scripts/import_topuniversities.py --stats-only
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Path setup ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.topuni_transformer import transform_university, transform_program
from pipeline.tier_derivation import derive_tier_with_metadata, print_tier_stats
from src.database.repositories import UniversityRepository, ProgramRepository
from src.database.mongodb import get_mongo_connection, mongo_session
from src.models.university import University, UniversityProgram

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Default data paths ─────────────────────────────────────────────────────────
DEFAULT_UNIS_JSONL = (
    Path(r"C:\Users\Ayyan Laptop\Desktop\New folder\topuniversities")
    / "output" / "final_data" / "universities.jsonl"
)
DEFAULT_PROGRAMS_JSON = (
    Path(r"C:\Users\Ayyan Laptop\Desktop\New folder\topuniversities")
    / "output" / "sample_1000_programs" / "programs_1000.json"
)


# ── University import ─────────────────────────────────────────────────────────

def import_universities(
    jsonl_path: Path,
    dry_run: bool = False,
    batch_size: int = 200,
) -> dict:
    """Read universities.jsonl and upsert into MongoDB.

    Args:
        jsonl_path: Path to universities.jsonl from TopUniversities scraper.
        dry_run: If True, validate and print stats without writing to DB.
        batch_size: Number of records to process before printing progress.

    Returns:
        Summary dict with counts: total, inserted, updated, failed, skipped.
    """
    if not jsonl_path.exists():
        logger.error("File not found: %s", jsonl_path)
        return {}

    logger.info("Reading universities from: %s", jsonl_path)

    stats = {
        "total": 0,
        "transformed": 0,
        "inserted": 0,
        "updated": 0,
        "failed": 0,
        "skipped": 0,
    }
    tier_counts: dict[str, int] = defaultdict(int)
    tier_path_counts: dict[str, int] = defaultdict(int)
    failures: list[dict] = []

    repo = UniversityRepository() if not dry_run else None

    batch: list[dict] = []   # raw dicts ready for DB upsert
    uni_objects: list[dict] = []  # for tier stats in dry_run

    start = time.time()

    with jsonl_path.open(encoding="utf-8") as fh:
        for line_num, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue

            stats["total"] += 1

            try:
                raw = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning("Line %d: JSON parse error: %s", line_num, e)
                stats["failed"] += 1
                continue

            university = transform_university(raw)
            if university is None:
                stats["skipped"] += 1
                continue

            stats["transformed"] += 1

            # Tier accounting
            tier_meta = university.__dict__.get("tier_metadata", {})
            tier_counts[university.tier or "unknown"] += 1
            tier_path_counts[tier_meta.get("path", "unknown")] += 1

            if dry_run:
                uni_objects.append({"rankings": raw.get("rankings", [])})
                continue

            # Build the full dict to write (include extra metadata fields)
            doc = university.model_dump()
            doc["slug"] = university.__dict__.get("slug", "")
            doc["ranking_signals"] = university.__dict__.get("ranking_signals", [])
            doc["tier_metadata"] = university.__dict__.get("tier_metadata", {})
            doc["content_hash"] = university.__dict__.get("content_hash", "")
            doc["source_url"] = university.__dict__.get("source_url", "")
            doc["crawled_at"] = university.__dict__.get("crawled_at", "")
            doc["updated_at"] = datetime.now(timezone.utc).isoformat()
            doc["data_source"] = "topuniversities"

            batch.append(doc)

            if len(batch) >= batch_size:
                result = _flush_university_batch(batch, repo)
                stats["inserted"] += result["inserted"]
                stats["updated"] += result["updated"]
                stats["failed"] += result["failed"]
                failures.extend(result.get("failures", []))
                batch = []

                elapsed = time.time() - start
                logger.info(
                    "Progress: %d/%d  |  inserted=%d  updated=%d  failed=%d  (%.1fs)",
                    stats["total"], "?", stats["inserted"], stats["updated"],
                    stats["failed"], elapsed,
                )

    # Flush remaining
    if batch and not dry_run:
        result = _flush_university_batch(batch, repo)
        stats["inserted"] += result["inserted"]
        stats["updated"] += result["updated"]
        stats["failed"] += result["failed"]
        failures.extend(result.get("failures", []))

    elapsed = time.time() - start
    stats["tier_distribution"] = dict(tier_counts)
    stats["derivation_paths"] = dict(tier_path_counts)
    stats["elapsed_seconds"] = round(elapsed, 1)

    # Print summary
    _print_import_summary("Universities", stats, failures)

    if dry_run and uni_objects:
        print("\n── Tier Distribution (dry run) ──────────────────────────────────")
        print_tier_stats(uni_objects)

    return stats


def _flush_university_batch(batch: list[dict], repo: UniversityRepository) -> dict:
    """Upsert a batch of university dicts into MongoDB."""
    result = {"inserted": 0, "updated": 0, "failed": 0, "failures": []}
    try:
        with mongo_session() as conn:
            for doc in batch:
                try:
                    res = conn.universities_collection.replace_one(
                        {"university_id": doc["university_id"]},
                        doc,
                        upsert=True,
                    )
                    if res.acknowledged:
                        if res.upserted_id:
                            result["inserted"] += 1
                        else:
                            result["updated"] += 1
                    else:
                        result["failed"] += 1
                except Exception as e:
                    result["failed"] += 1
                    result["failures"].append({"name": doc.get("name"), "error": str(e)[:120]})
    except Exception as e:
        logger.error("Batch flush failed: %s", e)
        result["failed"] += len(batch)
    return result


# ── Program import ─────────────────────────────────────────────────────────────

def import_programs(
    programs_json: Path,
    dry_run: bool = False,
) -> dict:
    """Read programs JSON and upsert into MongoDB.

    Args:
        programs_json: Path to programs JSON file (array of program objects).
        dry_run: If True, validate and print stats without writing to DB.

    Returns:
        Summary dict with counts.
    """
    if not programs_json.exists():
        logger.error("File not found: %s", programs_json)
        return {}

    logger.info("Reading programs from: %s", programs_json)

    with programs_json.open(encoding="utf-8") as fh:
        try:
            raw_programs = json.load(fh)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse programs JSON: %s", e)
            return {}

    stats = {
        "total": len(raw_programs),
        "transformed": 0,
        "inserted": 0,
        "updated": 0,
        "failed": 0,
        "skipped": 0,
    }
    category_counts: dict[str, int] = defaultdict(int)
    failures: list[dict] = []

    start = time.time()

    for raw in raw_programs:
        prog_dict = transform_program(raw)
        if prog_dict is None:
            stats["skipped"] += 1
            continue

        stats["transformed"] += 1
        category_counts[prog_dict.get("program_category", "Other")] += 1

        if dry_run:
            continue

        # Upsert by source_url
        try:
            with mongo_session() as conn:
                prog_doc = prog_dict.copy()
                prog_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
                prog_doc["data_source"] = "topuniversities"

                res = conn.collection.replace_one(
                    {"source_url": prog_doc["source_url"]},
                    prog_doc,
                    upsert=True,
                )
                if res.acknowledged:
                    if res.upserted_id:
                        stats["inserted"] += 1
                    else:
                        stats["updated"] += 1
                else:
                    stats["failed"] += 1
        except Exception as e:
            stats["failed"] += 1
            failures.append({
                "name": prog_dict.get("program_name"),
                "error": str(e)[:120],
            })

    elapsed = time.time() - start
    stats["category_distribution"] = dict(category_counts)
    stats["elapsed_seconds"] = round(elapsed, 1)

    _print_import_summary("Programs", stats, failures)
    return stats


# ── Stats only ─────────────────────────────────────────────────────────────────

def print_db_stats() -> None:
    """Print current counts and tier distribution from MongoDB."""
    try:
        with mongo_session() as conn:
            uni_count = conn.universities_collection.count_documents({})
            prog_count = conn.collection.count_documents({})

            tier_pipeline = [
                {"$group": {"_id": "$tier", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ]
            tier_dist = list(conn.universities_collection.aggregate(tier_pipeline))

            source_pipeline = [
                {"$group": {"_id": "$data_source", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ]
            source_dist = list(conn.universities_collection.aggregate(source_pipeline))

            print("\n── MongoDB Current State ────────────────────────────────────────")
            print(f"  Universities : {uni_count:,}")
            print(f"  Programs     : {prog_count:,}")
            print("\n  Tier distribution:")
            for t in tier_dist:
                print(f"    {(t['_id'] or 'none'):12s}: {t['count']:,}")
            print("\n  By data source:")
            for s in source_dist:
                print(f"    {(s['_id'] or 'none'):20s}: {s['count']:,}")
            print("────────────────────────────────────────────────────────────────\n")
    except Exception as e:
        logger.error("Failed to connect to MongoDB: %s", e)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _print_import_summary(label: str, stats: dict, failures: list[dict]) -> None:
    elapsed = stats.get("elapsed_seconds", 0)
    print(f"\n{'─'*64}")
    print(f"  {label} Import Summary")
    print(f"{'─'*64}")
    print(f"  Total read     : {stats.get('total', 0):,}")
    print(f"  Transformed    : {stats.get('transformed', 0):,}")
    print(f"  Inserted       : {stats.get('inserted', 0):,}")
    print(f"  Updated        : {stats.get('updated', 0):,}")
    print(f"  Failed         : {stats.get('failed', 0):,}")
    print(f"  Skipped        : {stats.get('skipped', 0):,}")
    print(f"  Elapsed        : {elapsed:.1f}s")

    if "tier_distribution" in stats:
        print(f"\n  Tier distribution:")
        for tier, count in sorted(stats["tier_distribution"].items()):
            pct = 100 * count / max(stats.get("transformed", 1), 1)
            print(f"    {tier:12s}: {count:,} ({pct:.1f}%)")

    if "derivation_paths" in stats:
        print(f"\n  Derivation paths:")
        for path, count in sorted(stats["derivation_paths"].items()):
            pct = 100 * count / max(stats.get("transformed", 1), 1)
            print(f"    {path:30s}: {count:,} ({pct:.1f}%)")

    if "category_distribution" in stats:
        print(f"\n  Program categories:")
        for cat, count in sorted(
            stats["category_distribution"].items(), key=lambda x: -x[1]
        )[:10]:
            print(f"    {cat:30s}: {count:,}")

    if failures:
        print(f"\n  Sample failures (first 5):")
        for f in failures[:5]:
            print(f"    {f.get('name', '?')[:50]:50s}: {f.get('error', '')[:60]}")

    print(f"{'─'*64}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import TopUniversities scraped data into MongoDB"
    )
    parser.add_argument(
        "--unis-jsonl",
        default=str(DEFAULT_UNIS_JSONL),
        help="Path to universities.jsonl",
    )
    parser.add_argument(
        "--programs-json",
        default=str(DEFAULT_PROGRAMS_JSON),
        help="Path to programs JSON file",
    )
    parser.add_argument(
        "--universities-only",
        action="store_true",
        help="Only import universities (skip programs)",
    )
    parser.add_argument(
        "--programs-only",
        action="store_true",
        help="Only import programs (skip universities)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print stats without writing to DB",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Print current DB stats and exit",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="University batch size for progress logging (default: 200)",
    )
    args = parser.parse_args()

    if args.stats_only:
        print_db_stats()
        return

    mode = "DRY RUN" if args.dry_run else "LIVE"
    logger.info("Starting TopUniversities import — mode: %s", mode)

    if not args.programs_only:
        import_universities(
            jsonl_path=Path(args.unis_jsonl),
            dry_run=args.dry_run,
            batch_size=args.batch_size,
        )

    if not args.universities_only:
        import_programs(
            programs_json=Path(args.programs_json),
            dry_run=args.dry_run,
        )

    if not args.dry_run:
        print_db_stats()


if __name__ == "__main__":
    main()

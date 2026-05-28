"""Test script to scrape a single program page and print structured fields."""
import argparse
import asyncio
import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scrapers.topuniversities_scraper import TopUniversitiesScraper


async def main():
    parser = argparse.ArgumentParser(description="Test scraper on a single program URL")
    parser.add_argument(
        "url",
        nargs="?",
        default="https://www.topuniversities.com/universities/imperial-college-london/postgrad/msc-computing",
        help="The full URL of the TopUniversities program page",
    )
    args = parser.parse_args()

    url = args.url
    print(f"Testing extraction for:\n  {url}\n")

    scraper = TopUniversitiesScraper()
    detail = await scraper.scrape_program_detail(url)
    await scraper.close()

    # 1. Print Admission Scores
    SCORE_FIELDS = [
        "gre_score",
        "bachelor_gpa",
        "toefl_score",
        "ielts_score",
        "pte_score",
        "cambridge_cae_score",
        "duolingo_score",
        "sat_score",
        "gmat_score",
    ]

    print("=== ADMISSION SCORES ===")
    for f in SCORE_FIELDS:
        val = detail.get(f)
        status = f"✓ {val}" if val else "✗ not found"
        print(f"  {f:25s}: {status}")

    # 2. Print Fee Structure
    FEE_FIELDS = ["fee_domestic", "fee_international", "fee_currency"]
    print("\n=== FEE STRUCTURE ===")
    has_fee = False
    for f in FEE_FIELDS:
        val = detail.get(f)
        if val:
            has_fee = True
            print(f"  {f:25s}: ✓ {val}")
        else:
            print(f"  {f:25s}: ✗ not found")

    if not has_fee and detail.get("tuition_fee_detail"):
        print("\n  Raw fee block found instead:")
        print(f"  {detail.get('tuition_fee_detail')}")

    # 3. Dump all fields beautifully
    print("\n=== ALL EXTRACTED FIELDS ===")
    print(json.dumps(detail, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    # Ensure UTF-8 output on Windows
    # sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())

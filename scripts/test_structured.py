"""Test structured extraction against a known program with all fields."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scrapers.topuniversities_scraper import TopUniversitiesScraper


async def main():
    scraper = TopUniversitiesScraper()

    # Imperial College MSc Computing — known to have all fields
    url = "https://www.topuniversities.com/universities/imperial-college-london/postgrad/msc-computing"

    print(f"Testing: {url}\n")
    detail = await scraper.scrape_program_detail(url)

    # Admission scores
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

    # Fee structure
    FEE_FIELDS = ["fee_domestic", "fee_international", "fee_currency"]
    print("\n=== FEE STRUCTURE ===")
    for f in FEE_FIELDS:
        val = detail.get(f)
        status = f"✓ {val}" if val else "✗ not found"
        print(f"  {f:25s}: {status}")

    # All fields dump
    print(f"\n=== ALL {len(detail)} FIELDS ===")
    for k, v in sorted(detail.items()):
        if v is not None:
            val_str = str(v)[:80]
            print(f"  {k:30s}: {val_str}")

    filled = sum(1 for v in detail.values() if v is not None)
    print(f"\nTotal filled: {filled}/{len(detail)}")

    await scraper.close()


asyncio.run(main())

"""Dump structured fields to a file for clean reading."""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.scrapers.topuniversities_scraper import TopUniversitiesScraper


async def main():
    scraper = TopUniversitiesScraper()
    url = "https://www.topuniversities.com/universities/imperial-college-london/postgrad/msc-computing"
    detail = await scraper.scrape_program_detail(url)
    await scraper.close()

    with open("output/imperial_test.json", "w", encoding="utf-8") as f:
        json.dump(detail, f, indent=2, ensure_ascii=False)
    print(f"Saved to output/imperial_test.json ({len(detail)} fields)")


asyncio.run(main())

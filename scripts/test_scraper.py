import asyncio
import logging
import sys

from src.scrapers.topuniversities_scraper import TopUniversitiesScraper

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)


async def test():
    scraper = TopUniversitiesScraper()
    programs = await scraper.scrape_programs_with_details(max_programs=3)
    for p in programs:
        print("-------------")
        print(f"PROGRAM URL: {p.get('program_url')}")
        print(f"DURATION: {p.get('duration')}")
        print(f"DOMESTIC FEE: {p.get('fee_domestic')}")


asyncio.run(test())

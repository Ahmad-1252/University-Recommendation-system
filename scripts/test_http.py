import asyncio
import json
import os
import sys

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bs4 import BeautifulSoup

from src.scrapers.topuniversities_scraper import TopUniversitiesScraper


async def test():
    # We test on Nanyang Technological University Bachelor of Arts in Philosophy
    url = "https://www.topuniversities.com/universities/nanyang-technological-university-singapore-ntu-singapore/undergrad/bachelor-arts-philosophy"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    scraper = TopUniversitiesScraper()
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                detail = scraper._extract_page_fields(soup, url)
                # Keep only non-null values for cleaner output
                clean_detail = {k: v for k, v in detail.items() if v is not None}
                with open("test_out.json", "w", encoding="utf-8") as f:
                    json.dump(clean_detail, f, indent=2, ensure_ascii=False)
                print("WROTE clean_detail to test_out.json")
            else:
                print(f"Failed to fetch, status = {resp.status_code}")
        except Exception as e:
            print(f"Error: {e}")


asyncio.run(test())

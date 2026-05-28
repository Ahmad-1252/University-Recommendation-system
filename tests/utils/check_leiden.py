"""Check Leiden University URL patterns (moved to tests/utils)."""
import asyncio
import re

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig


async def check_links():
    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(
        wait_until="networkidle", delay_before_return_html=3.0
    )

    # Try different potential program listing URLs
    urls_to_try = [
        "https://studiegids.universiteitleiden.nl/en/",
        "https://studiegids.universiteitleiden.nl/en/studies",
        "https://www.universiteitleiden.nl/en/education/study-programmes",
    ]

    async with AsyncWebCrawler(config=browser_config) as crawler:
        for url in urls_to_try:
            print(f"\n=== Trying: {url} ===")
            try:
                result = await crawler.arun(url, config=run_config)
                links = re.findall(r'href="([^"]+)"', result.html)
                seen = set()
                for link in links:
                    if link not in seen:
                        seen.add(link)
                        # Look for program-like URLs
                        if any(
                            x in link.lower()
                            for x in [
                                "master",
                                "bachelor",
                                "computer",
                                "science",
                                "studies",
                                "course",
                            ]
                        ):
                            if not any(
                                x in link for x in ["css", "js", ".ico", ".png"]
                            ):
                                print(f"  {link}")
                print(f"  Total links: {len(seen)}")
            except Exception as e:
                print(f"  Error: {e}")


if __name__ == "__main__":
    asyncio.run(check_links())

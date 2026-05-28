#!/usr/bin/env python
"""Quick diagnostic to check TopUniversities.com page structure."""

import asyncio

from playwright.async_api import async_playwright


async def check_page_structure():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # visible browser
        page = await browser.new_page()

        print("Loading TopUniversities.com rankings page...")
        await page.goto(
            "https://www.topuniversities.com/world-university-rankings", timeout=60000
        )

        print("Waiting for page to load...")
        await page.wait_for_load_state("networkidle", timeout=30000)

        # Take screenshot
        await page.screenshot(path="topuni_screenshot.png")
        print("Screenshot saved to topuni_screenshot.png")

        # Get page content
        content = await page.content()

        # Check for various possible selectors
        print("\n=== Checking selectors ===")

        selectors_to_check = [
            "div[data-testid='rankings-list']",
            "div[data-testid='ranking-item']",
            ".ranking-card",
            ".university-card",
            "[class*='ranking']",
            "[class*='university']",
            "table",
            ".data-table",
            "article",
            "div[class*='list']",
        ]

        for selector in selectors_to_check:
            count = await page.locator(selector).count()
            print(f"{selector}: {count} elements")

        # Save HTML for inspection
        with open("topuni_page.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("\nPage HTML saved to topuni_page.html")

        print("\nPress Enter to close browser...")
        input()

        await browser.close()


if __name__ == "__main__":
    asyncio.run(check_page_structure())

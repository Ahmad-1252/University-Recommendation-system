"""Scraper for TopUniversities.com rankings and university data."""

import asyncio
import logging
import random
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, Browser

from scrapers.base_scraper import BaseScraper
from models.university import UniversityProgram
from core.exceptions import ScrapingError
from core.constants import TOPUNIVERSITIES_CONFIG

logger = logging.getLogger(__name__)

# User agents for rotation (anti-detection)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


class TopUniversitiesScraper(BaseScraper):
    """Scraper for TopUniversities.com to fetch rankings and university metadata."""
    
    def __init__(self):
        super().__init__(name="TopUniversitiesScraper")
        self.base_url = TOPUNIVERSITIES_CONFIG["base_url"]
        self.selectors = TOPUNIVERSITIES_CONFIG["selectors"]
        self.rate_limiting = TOPUNIVERSITIES_CONFIG["rate_limiting"]
        self.browser: Optional[Browser] = None
        self.playwright = None
        
    async def __aenter__(self):
        """Context manager entry."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def _get_random_user_agent(self) -> str:
        """Get a random user agent for anti-detection."""
        return random.choice(USER_AGENTS)
    
    async def _random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """Add random delay between actions for human-like behavior."""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)
    
    async def _create_page_with_context(self) -> Page:
        """Create a new page with randomized context for anti-detection."""
        context = await self.browser.new_context(
            user_agent=self._get_random_user_agent(),
            viewport={"width": 1920, "height": 1080},
            locale="en-US"
        )
        page = await context.new_page()
        return page
    
    async def scrape_program_data(self, url: str, skip_validation: bool = False) -> Optional[UniversityProgram]:
        """Not applicable for TopUniversities scraper. Use specialized methods instead."""
        raise NotImplementedError("TopUniversities scraper is designed for rankings data, not programs.")
    
    async def validate_url(self, url: str) -> bool:
        """Validate if URL is from TopUniversities.com."""
        return "topuniversities.com" in url.lower()
    
    async def scrape_world_rankings(
        self, 
        year: Optional[int] = None,
        max_results: int = 500
    ) -> List[Dict[str, Any]]:
        """
        Scrape world university rankings from TopUniversities.com.
        
        Args:
            year: Year for rankings (defaults to current year)
            max_results: Maximum number of universities to scrape
            
        Returns:
            List of dictionaries containing university ranking data
        """
        if not self.browser:
            async with self:
                return await self._scrape_rankings_page(year, max_results)
        else:
            return await self._scrape_rankings_page(year, max_results)
    
    async def _wait_for_rankings_load(self, page: Page) -> bool:
        """Wait for rankings to load with fallback selectors."""
        selectors_to_try = [
            self.selectors["ranking_list"],  # Primary: .ranking-result-table
            self.selectors["ranking_item_card"],  # Card view: .ind-item
            self.selectors.get("fallback_ranking_item", "[class*='ranking']"),
            "a.uni-link",  # University links always present
        ]
        
        for selector in selectors_to_try:
            try:
                await page.wait_for_selector(selector, timeout=10000)
                logger.info(f"Rankings loaded using selector: {selector}")
                return True
            except:
                continue
        
        logger.warning("Could not find rankings with any known selector")
        return False
    
    async def _scrape_rankings_page(self, year: Optional[int], max_results: int) -> List[Dict[str, Any]]:
        """Internal method to scrape rankings page."""
        results = []
        
        try:
            # Construct URL
            if year:
                url = f"{self.base_url}/world-university-rankings/{year}"
            else:
                url = f"{self.base_url}/world-university-rankings"
            
            logger.info(f"Scraping rankings from: {url}")
            
            page = await self._create_page_with_context()
            
            # Navigate with retry logic
            for attempt in range(self.rate_limiting["max_retries"]):
                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    break
                except Exception as e:
                    logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                    if attempt < self.rate_limiting["max_retries"] - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        raise
            
            await self._random_delay(2, 4)
            
            # Wait for rankings to load with fallback
            if not await self._wait_for_rankings_load(page):
                # Try scrolling to trigger lazy load
                await page.evaluate("window.scrollTo(0, 500)")
                await self._random_delay(2, 3)
                await self._wait_for_rankings_load(page)
            
            # Scroll to load more results
            await self._scroll_to_load_content(page, max_results)
            
            # Get page content
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Try multiple selectors for ranking items
            ranking_items = self._find_ranking_items(soup)
            
            logger.info(f"Found {len(ranking_items)} ranking items")
            
            for item in ranking_items[:max_results]:
                try:
                    ranking_data = self._parse_ranking_item(item)
                    if ranking_data:
                        results.append(ranking_data)
                except Exception as e:
                    logger.error(f"Error parsing ranking item: {e}")
                    continue
            
            await page.context.close()
            logger.info(f"Scraped {len(results)} university rankings")
            
        except Exception as e:
            logger.error(f"Error scraping rankings: {e}")
            raise ScrapingError(f"Failed to scrape TopUniversities rankings: {e}")
        
        return results
    
    def _find_ranking_items(self, soup: BeautifulSoup) -> List:
        """Find ranking items using multiple selector strategies."""
        # Try primary selectors first
        selectors_to_try = [
            self.selectors["ranking_item"],  # ._qs-ranking-data-row.row
            self.selectors["ranking_item_card"],  # .ind-item
            self.selectors.get("fallback_ranking_item"),
            "[class*='ranking'][class*='row']",
            ".row:has(a.uni-link)",  # Rows containing university links
        ]
        
        for selector in selectors_to_try:
            if selector:
                items = soup.select(selector)
                if items:
                    logger.info(f"Found {len(items)} items using selector: {selector}")
                    return items
        
        # Last resort: find all containers with university links
        logger.warning("Using fallback: finding items by university links")
        uni_links = soup.select("a.uni-link")
        items = []
        for link in uni_links:
            # Get parent container
            parent = link.find_parent(class_=re.compile(r'(row|item|card)', re.I))
            if parent and parent not in items:
                items.append(parent)
        
        return items
    
    async def _scroll_to_load_content(self, page: Page, target_count: int):
        """Scroll page to trigger lazy loading of content."""
        previous_count = 0
        attempts = 0
        max_attempts = 10
        
        while attempts < max_attempts:
            # Scroll to bottom with human-like behavior
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self._random_delay(1.5, 3)
            
            # Check if more content loaded using multiple selectors
            current_count = 0
            for selector in [self.selectors["ranking_item"], self.selectors["ranking_item_card"], "a.uni-link"]:
                try:
                    count = await page.locator(selector).count()
                    current_count = max(current_count, count)
                except:
                    pass
            
            if current_count >= target_count:
                break
                
            if current_count == previous_count:
                # No new content loaded, try clicking "Load More" or pagination
                try:
                    # Try load more button
                    load_more = page.locator(self.selectors["load_more_button"])
                    if await load_more.is_visible():
                        await load_more.click()
                        await self._random_delay(2, 3)
                        continue
                except:
                    pass
                
                try:
                    # Try next page button
                    next_btn = page.locator(self.selectors["next_page_button"])
                    if await next_btn.is_visible():
                        await next_btn.click()
                        await self._random_delay(2, 3)
                        continue
                except:
                    break
            
            previous_count = current_count
            attempts += 1
    
    def _parse_ranking_item(self, item) -> Optional[Dict[str, Any]]:
        """Parse a single ranking item from the page."""
        try:
            # Extract rank - try multiple selectors
            rank = None
            rank_selectors = [
                self.selectors["ranking_position"],  # ._univ-rank .td-wrap-in
                self.selectors["ranking_position_card"],  # .overall-rank-value
                "._univ-rank",
                ".rank",
                "[class*='rank']"
            ]
            
            for selector in rank_selectors:
                rank_elem = item.select_one(selector)
                if rank_elem:
                    rank_text = rank_elem.get_text(strip=True)
                    # Parse rank (handle ranges like "501-510")
                    match = re.search(r'(\d+)', rank_text)
                    if match:
                        rank = int(match.group(1))
                        break
            
            # Extract university name - try multiple selectors
            university_name = None
            name_selectors = [
                self.selectors["university_name"],  # a.uni-link
                self.selectors.get("fallback_university_name"),
                "a[href*='/universities/']",
                "h2", "h3", ".university-name"
            ]
            
            for selector in name_selectors:
                if selector:
                    name_elem = item.select_one(selector)
                    if name_elem:
                        university_name = name_elem.get_text(strip=True)
                        if university_name:
                            break
            
            if not university_name:
                return None
            
            # Extract location
            location_elem = item.select_one(self.selectors["location"])
            if not location_elem:
                location_elem = item.select_one(".location, .country, [class*='location']")
            
            location = location_elem.get_text(strip=True) if location_elem else None
            
            # Parse country and city
            country, city = self._parse_location(location)
            
            # Extract score - try multiple selectors
            score = None
            score_selectors = [
                self.selectors["overall_score"],
                self.selectors.get("fallback_score"),
                "[class*='score']",
                ".score"
            ]
            
            for selector in score_selectors:
                if selector:
                    score_elem = item.select_one(selector)
                    if score_elem:
                        score_text = score_elem.get_text(strip=True)
                        try:
                            # Handle "Overall Score: 97.2" format
                            match = re.search(r'(\d+\.?\d*)', score_text)
                            if match:
                                score = float(match.group(1))
                                break
                        except:
                            pass
            
            # Extract profile URL
            link_elem = item.select_one("a[href*='/universities/']")
            if not link_elem:
                link_elem = item.select_one("a.uni-link")
            
            profile_url = None
            if link_elem and link_elem.get('href'):
                href = link_elem['href']
                profile_url = href if href.startswith('http') else f"{self.base_url}{href}"
            
            return {
                "rank": rank,
                "university_name": university_name,
                "country": country,
                "city": city,
                "score": score,
                "profile_url": profile_url,
                "source": "TopUniversities",
                "scraped_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing ranking item: {e}")
            return None
    
    def _parse_location(self, location: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        """Parse location string into country and city."""
        if not location:
            return None, None
        
        # Common format: "City, Country" or just "Country"
        parts = [p.strip() for p in location.split(',')]
        
        if len(parts) == 2:
            city, country = parts
            return country, city
        elif len(parts) == 1:
            return parts[0], None
        else:
            return None, None
    
    async def scrape_subject_rankings(
        self, 
        subject: str,
        year: Optional[int] = None,
        max_results: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Scrape subject-specific rankings.
        
        Args:
            subject: Subject name (e.g., "computer-science", "business")
            year: Year for rankings
            max_results: Maximum results to return
            
        Returns:
            List of ranking dictionaries
        """
        results = []
        
        try:
            if not self.browser:
                async with self:
                    return await self._scrape_subject_rankings_page(subject, year, max_results)
            else:
                return await self._scrape_subject_rankings_page(subject, year, max_results)
                
        except Exception as e:
            logger.error(f"Error scraping subject rankings for {subject}: {e}")
            return results
    
    async def _scrape_subject_rankings_page(
        self, 
        subject: str, 
        year: Optional[int], 
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Internal method to scrape subject rankings."""
        results = []
        
        try:
            # Construct URL
            if year:
                url = f"{self.base_url}/university-rankings/university-subject-rankings/{year}/{subject}"
            else:
                url = f"{self.base_url}/university-rankings/university-subject-rankings/{subject}"
            
            logger.info(f"Scraping subject rankings from: {url}")
            
            page = await self._create_page_with_context()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            await self._random_delay(2, 4)
            
            # Wait for content to load with fallback
            await self._wait_for_rankings_load(page)
            await self._scroll_to_load_content(page, max_results)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            ranking_items = self._find_ranking_items(soup)
            
            for item in ranking_items[:max_results]:
                try:
                    ranking_data = self._parse_ranking_item(item)
                    if ranking_data:
                        ranking_data['subject'] = subject
                        results.append(ranking_data)
                except Exception as e:
                    logger.error(f"Error parsing subject ranking item: {e}")
                    continue
            
            await page.context.close()
            logger.info(f"Scraped {len(results)} universities for {subject}")
            
        except Exception as e:
            logger.error(f"Error scraping subject rankings page: {e}")
        
        return results
    
    async def scrape_university_profile(self, university_url: str) -> Dict[str, Any]:
        """
        Scrape detailed university profile from TopUniversities.com.
        
        Args:
            university_url: URL to university profile page
            
        Returns:
            Dictionary containing university profile data
        """
        if not self.browser:
            async with self:
                return await self._scrape_profile_page(university_url)
        else:
            return await self._scrape_profile_page(university_url)
    
    async def _scrape_profile_page(self, university_url: str) -> Dict[str, Any]:
        """Internal method to scrape university profile."""
        profile_data = {}
        
        try:
            logger.info(f"Scraping university profile: {university_url}")
            
            page = await self._create_page_with_context()
            await page.goto(university_url, wait_until="networkidle", timeout=30000)
            
            await self._random_delay(2, 3)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract university name
            name_elem = soup.select_one("h1")
            if name_elem:
                profile_data['university_name'] = name_elem.get_text(strip=True)
            
            # Extract overview/description
            desc_elem = soup.select_one(".university-overview, .description, [data-testid='overview']")
            if desc_elem:
                profile_data['description'] = desc_elem.get_text(strip=True)
            
            # Extract rankings
            rankings = {}
            ranking_sections = soup.select(".ranking-score, [data-testid='ranking-score']")
            for section in ranking_sections:
                rank_type = section.select_one(".rank-label, .ranking-type")
                rank_value = section.select_one(".rank-value, .score")
                
                if rank_type and rank_value:
                    rankings[rank_type.get_text(strip=True)] = rank_value.get_text(strip=True)
            
            profile_data['rankings'] = rankings
            
            # Extract contact info
            website_elem = soup.select_one("a[href*='http']:has-text('Visit website'), .website-link")
            if website_elem:
                profile_data['website'] = website_elem.get('href')
            
            # Extract location
            location_elem = soup.select_one(".location-info, [data-testid='location']")
            if location_elem:
                location_text = location_elem.get_text(strip=True)
                country, city = self._parse_location(location_text)
                profile_data['country'] = country
                profile_data['city'] = city
            
            # Extract student numbers
            students_elem = soup.select_one(".student-count, [data-testid='student-count']")
            if students_elem:
                students_text = students_elem.get_text(strip=True)
                # Try to extract number
                match = re.search(r'([\d,]+)', students_text)
                if match:
                    try:
                        profile_data['total_students'] = int(match.group(1).replace(',', ''))
                    except:
                        pass
            
            await page.context.close()
            logger.info(f"Successfully scraped profile for {profile_data.get('university_name', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"Error scraping university profile: {e}")
            raise ScrapingError(f"Failed to scrape university profile: {e}")
        
        return profile_data
    
    async def search_university(self, university_name: str) -> Optional[str]:
        """
        Search for a university on TopUniversities.com and return its profile URL.
        
        Args:
            university_name: Name of the university to search for
            
        Returns:
            Profile URL if found, None otherwise
        """
        if not self.browser:
            async with self:
                return await self._search_university_page(university_name)
        else:
            return await self._search_university_page(university_name)
    
    async def _search_university_page(self, university_name: str) -> Optional[str]:
        """Internal method to search for university."""
        try:
            search_url = f"{self.base_url}/find-your-university"
            
            page = await self._create_page_with_context()
            await page.goto(search_url, wait_until="networkidle", timeout=30000)
            
            await self._random_delay(1, 2)
            
            # Look for search input
            search_input = page.locator("input[type='search'], input[placeholder*='Search']")
            if await search_input.count() > 0:
                await search_input.first.fill(university_name)
                await self._random_delay(0.5, 1)
                await page.keyboard.press('Enter')
                await page.wait_for_load_state('networkidle')
                
                await self._random_delay(1, 2)
                
                # Look for first result link
                result_link = page.locator(f"a[href*='/universities/']:has-text('{university_name[:20]}')")
                if await result_link.count() > 0:
                    href = await result_link.first.get_attribute('href')
                    await page.context.close()
                    
                    if href:
                        return href if href.startswith('http') else f"{self.base_url}{href}"
            
            await page.context.close()
            
        except Exception as e:
            logger.error(f"Error searching for university {university_name}: {e}")
        
        return None

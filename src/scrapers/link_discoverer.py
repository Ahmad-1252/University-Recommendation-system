"""Link discovery logic for finding university program pages."""

import asyncio
import logging
import re
from typing import Dict, List, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

from src.core.config import get_settings
from src.core.constants import DEGREE_LEVELS, PROGRAM_CATEGORIES

logger = logging.getLogger(__name__)


class LinkDiscoverer:
    """Discovers relevant links from university websites."""

    def __init__(self):
        self.settings = get_settings()
        self.timeout = self.settings.scraping.timeout

        # Keywords that indicate program pages - expanded for all fields
        self.program_keywords = set()
        for category, keywords in PROGRAM_CATEGORIES.items():
            self.program_keywords.update(keywords)

        # Add degree level keywords
        for level, keywords in DEGREE_LEVELS.items():
            self.program_keywords.update(keywords)

        # Additional program-related keywords
        self.program_keywords.update(
            {
                "program",
                "programme",
                "course",
                "degree",
                "study",
                "major",
                "curriculum",
                "admission",
                "apply",
                "enrol",
                "enroll",
            }
        )

        # URL patterns to avoid
        self.exclude_patterns = {
            "facebook.com",
            "twitter.com",
            "linkedin.com",
            "instagram.com",
            "youtube.com",
            "calendar",
            "events",
            "news",
            "blog",
            "staff",
            "faculty-profile",
            "alumni",
            "login",
            "register",
            "privacy",
            "terms",
            "cookie",
            "accessibility",
            "sitemap",
            "careers",
            "jobs",
            "vacancies",
            "#",
            "javascript:",
            "mailto:",
            "tel:",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".zip",
        }

    async def discover_all_program_links(
        self,
        directory_url: str,
        base_url: str = None,
        category_filter: str = None,
        program_url_pattern: str = None,
        pagination: dict = None,
    ) -> List[Dict[str, str]]:
        """
        Discover ALL program links from a university course directory page.

        Args:
            directory_url: URL of the course listing/directory page
            base_url: Base URL for resolving relative links
            category_filter: Optional filter for specific program category
            program_url_pattern: Regex pattern to match valid program URLs (e.g., "/detail/[a-z]")
            pagination: Pagination config dict with 'type', 'pattern', 'max_pages'

        Returns:
            List of dicts with program_name, program_url, and detected_category
        """
        logger.info(f"Discovering all program links from {directory_url}")
        if program_url_pattern:
            logger.info(f"Using program URL pattern: {program_url_pattern}")
        if pagination:
            logger.info(f"Using pagination: {pagination}")

        if not base_url:
            parsed = urlparse(directory_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

        discovered_programs = []

        # Compile the pattern if provided
        compiled_pattern = None
        if program_url_pattern:
            try:
                compiled_pattern = re.compile(program_url_pattern, re.IGNORECASE)
            except re.error as e:
                logger.warning(
                    f"Invalid program URL pattern '{program_url_pattern}': {e}"
                )

        try:
            async with AsyncWebCrawler() as crawler:
                # Handle pagination if configured
                if pagination:
                    pagination_type = pagination.get("type", "query")
                    max_pages = pagination.get("max_pages", 10)
                    pattern = pagination.get("pattern", "?page={page}")

                    if pagination_type == "hash":
                        # Hash-based pagination (e.g., #page=1)
                        for page_num in range(1, max_pages + 1):
                            if page_num == 1:
                                page_url = directory_url
                            else:
                                page_url = directory_url.rstrip("/") + pattern.format(
                                    page=page_num
                                )

                            logger.info(f"Fetching page {page_num}: {page_url}")

                            # Use JavaScript to trigger hash-based pagination
                            js_code = ""
                            if page_num > 1:
                                js_code = f"""
                                if (window.location.hash !== '{pattern.format(page=page_num)}') {{
                                    window.location.hash = 'page={page_num}';
                                }}
                                await new Promise(r => setTimeout(r, 2000));
                                """

                            from crawl4ai import CrawlerRunConfig

                            run_config = CrawlerRunConfig(
                                js_code=js_code, delay_before_return_html=3
                            )

                            result = await crawler.arun(
                                url=page_url, config=run_config, timeout=self.timeout
                            )

                            if not result.success:
                                logger.warning(f"Failed to fetch page {page_num}")
                                break

                            html_content = (
                                result.html if hasattr(result, "html") else ""
                            )
                            soup = BeautifulSoup(html_content, "html.parser")

                            page_programs = self._extract_programs_from_soup(
                                soup,
                                base_url,
                                compiled_pattern,
                                category_filter,
                                discovered_programs,
                            )

                            new_programs = [
                                p
                                for p in page_programs
                                if not any(
                                    ep["program_url"] == p["program_url"]
                                    for ep in discovered_programs
                                )
                            ]

                            logger.info(
                                f"Page {page_num}: Found {len(page_programs)} programs ({len(new_programs)} new)"
                            )

                            if not new_programs and page_num > 1:
                                logger.info(
                                    f"No new programs on page {page_num}, stopping pagination"
                                )
                                break

                            discovered_programs.extend(new_programs)

                    elif pagination_type == "query":
                        # Query-string pagination (e.g., ?page=1 or ?offset=20)
                        for page_num in range(1, max_pages + 1):
                            if page_num == 1:
                                page_url = directory_url
                            else:
                                # Handle pattern with {page} or {offset}
                                if "{offset}" in pattern:
                                    # Offset-based pagination (e.g., ?offset=20)
                                    page_size = pagination.get("page_size", 20)
                                    offset = (page_num - 1) * page_size
                                    page_suffix = pattern.format(offset=offset)
                                else:
                                    page_suffix = pattern.format(page=page_num)

                                # Append to URL correctly
                                if "?" in directory_url:
                                    page_url = (
                                        directory_url + "&" + page_suffix.lstrip("?&")
                                    )
                                else:
                                    page_url = directory_url + page_suffix

                            logger.info(f"Fetching page {page_num}: {page_url}")

                            result = await crawler.arun(
                                url=page_url, timeout=self.timeout
                            )

                            if not result.success:
                                logger.warning(f"Failed to fetch page {page_num}")
                                break

                            html_content = (
                                result.html if hasattr(result, "html") else ""
                            )
                            soup = BeautifulSoup(html_content, "html.parser")

                            page_programs = self._extract_programs_from_soup(
                                soup,
                                base_url,
                                compiled_pattern,
                                category_filter,
                                discovered_programs,
                            )

                            new_programs = [
                                p
                                for p in page_programs
                                if not any(
                                    ep["program_url"] == p["program_url"]
                                    for ep in discovered_programs
                                )
                            ]

                            logger.info(
                                f"Page {page_num}: Found {len(page_programs)} programs ({len(new_programs)} new)"
                            )

                            if not new_programs and page_num > 1:
                                logger.info(
                                    f"No new programs on page {page_num}, stopping pagination"
                                )
                                break

                            discovered_programs.extend(new_programs)

                            # Rate limiting between pages
                            await asyncio.sleep(1)

                    elif pagination_type == "next_button":
                        # JavaScript click-based pagination (for "Next" buttons)
                        next_selector = pagination.get(
                            "next_selector", 'a.next, button.next, [aria-label="Next"]'
                        )

                        for page_num in range(1, max_pages + 1):
                            if page_num == 1:
                                page_url = directory_url
                                js_code = ""
                            else:
                                page_url = directory_url
                                js_code = f"""
                                const nextBtn = document.querySelector('{next_selector}');
                                if (nextBtn) {{
                                    nextBtn.click();
                                    await new Promise(r => setTimeout(r, 2000));
                                }}
                                """

                            logger.info(f"Fetching page {page_num}")

                            from crawl4ai import CrawlerRunConfig

                            run_config = CrawlerRunConfig(
                                js_code=js_code, delay_before_return_html=3
                            )

                            result = await crawler.arun(
                                url=page_url, config=run_config, timeout=self.timeout
                            )

                            if not result.success:
                                logger.warning(f"Failed to fetch page {page_num}")
                                break

                            html_content = (
                                result.html if hasattr(result, "html") else ""
                            )
                            soup = BeautifulSoup(html_content, "html.parser")

                            page_programs = self._extract_programs_from_soup(
                                soup,
                                base_url,
                                compiled_pattern,
                                category_filter,
                                discovered_programs,
                            )

                            new_programs = [
                                p
                                for p in page_programs
                                if not any(
                                    ep["program_url"] == p["program_url"]
                                    for ep in discovered_programs
                                )
                            ]

                            logger.info(
                                f"Page {page_num}: Found {len(page_programs)} programs ({len(new_programs)} new)"
                            )

                            if not new_programs and page_num > 1:
                                logger.info(
                                    f"No new programs on page {page_num}, stopping pagination"
                                )
                                break

                            discovered_programs.extend(new_programs)
                else:
                    # Single page scraping (original behavior)
                    result = await crawler.arun(url=directory_url, timeout=self.timeout)

                    if not result.success:
                        logger.error(f"Failed to fetch directory page: {directory_url}")
                        return []

                    # First try to use result.links which includes JS-rendered links
                    if hasattr(result, "links") and result.links:
                        all_result_links = result.links.get(
                            "internal", []
                        ) + result.links.get("external", [])
                        if all_result_links:
                            discovered_programs = (
                                self._extract_programs_from_result_links(
                                    all_result_links,
                                    base_url,
                                    compiled_pattern,
                                    category_filter,
                                    [],
                                )
                            )

                    # Fall back to BeautifulSoup if no programs found via result.links
                    if not discovered_programs:
                        html_content = result.html if hasattr(result, "html") else ""
                        soup = BeautifulSoup(html_content, "html.parser")

                        discovered_programs = self._extract_programs_from_soup(
                            soup, base_url, compiled_pattern, category_filter, []
                        )

                logger.info(f"Discovered {len(discovered_programs)} program links")

        except Exception as e:
            logger.error(f"Error discovering programs from {directory_url}: {e}")

        return discovered_programs

    def _extract_programs_from_result_links(
        self,
        links: list,
        base_url: str,
        compiled_pattern,
        category_filter: str,
        existing_programs: list,
    ) -> List[Dict[str, str]]:
        """Extract program links from crawl4ai result.links (includes JS-rendered content)."""
        discovered_programs = []

        logger.info(f"Found {len(links)} total links on page")

        for link_info in links:
            href = link_info.get("href", "")
            text = link_info.get("text", "").strip() if link_info.get("text") else ""

            if not href:
                continue
            if any(pattern in href.lower() for pattern in self.exclude_patterns):
                continue

            absolute_url = (
                urljoin(base_url, href) if not href.startswith("http") else href
            )

            # PRIMARY CHECK: If we have a program URL pattern, use it
            if compiled_pattern:
                if compiled_pattern.search(absolute_url):
                    program_name = (
                        text
                        if text and len(text) > 3
                        else self._extract_program_name_from_url(absolute_url)
                    )

                    if program_name:
                        detected_category = self._detect_category(
                            program_name, absolute_url
                        )

                        if (
                            category_filter
                            and detected_category.lower() != category_filter.lower()
                        ):
                            continue

                        degree_level = self._detect_degree_level(
                            program_name, absolute_url
                        )

                        program_info = {
                            "program_name": program_name,
                            "program_url": absolute_url,
                            "category": detected_category,
                            "degree_level": degree_level,
                        }

                        if not any(
                            p["program_url"] == absolute_url
                            for p in discovered_programs
                        ):
                            if not any(
                                p["program_url"] == absolute_url
                                for p in existing_programs
                            ):
                                discovered_programs.append(program_info)
                continue

            # FALLBACK: No pattern provided, use heuristic matching
            if not text or len(text) < 3 or len(text) > 200:
                continue

            if self._is_program_link(absolute_url, text):
                detected_category = self._detect_category(text, absolute_url)

                if (
                    category_filter
                    and detected_category.lower() != category_filter.lower()
                ):
                    continue

                degree_level = self._detect_degree_level(text, absolute_url)

                program_info = {
                    "program_name": text,
                    "program_url": absolute_url,
                    "category": detected_category,
                    "degree_level": degree_level,
                }

                if not any(
                    p["program_url"] == absolute_url for p in discovered_programs
                ):
                    if not any(
                        p["program_url"] == absolute_url for p in existing_programs
                    ):
                        discovered_programs.append(program_info)

        return discovered_programs

    def _extract_programs_from_soup(
        self,
        soup: BeautifulSoup,
        base_url: str,
        compiled_pattern,
        category_filter: str,
        existing_programs: list,
    ) -> List[Dict[str, str]]:
        """Extract program links from parsed HTML soup."""
        discovered_programs = []

        all_links = soup.find_all("a", href=True)
        logger.info(f"Found {len(all_links)} total links on page")

        for link in all_links:
            href = link.get("href", "")
            text = link.get_text(strip=True)

            if not href:
                continue
            if any(pattern in href.lower() for pattern in self.exclude_patterns):
                continue

            absolute_url = urljoin(base_url, href)

            # PRIMARY CHECK: If we have a program URL pattern, use it
            if compiled_pattern:
                if compiled_pattern.search(absolute_url):
                    program_name = (
                        text
                        if text and len(text) > 3
                        else self._extract_program_name_from_url(absolute_url)
                    )

                    if program_name:
                        detected_category = self._detect_category(
                            program_name, absolute_url
                        )

                        if (
                            category_filter
                            and detected_category.lower() != category_filter.lower()
                        ):
                            continue

                        degree_level = self._detect_degree_level(
                            program_name, absolute_url
                        )

                        program_info = {
                            "program_name": program_name,
                            "program_url": absolute_url,
                            "category": detected_category,
                            "degree_level": degree_level,
                        }

                        if not any(
                            p["program_url"] == absolute_url
                            for p in discovered_programs
                        ):
                            if not any(
                                p["program_url"] == absolute_url
                                for p in existing_programs
                            ):
                                discovered_programs.append(program_info)
                continue

            # FALLBACK: No pattern provided, use heuristic matching
            if not text or len(text) < 3 or len(text) > 200:
                continue

            if self._is_program_link(absolute_url, text):
                detected_category = self._detect_category(text, absolute_url)

                if (
                    category_filter
                    and detected_category.lower() != category_filter.lower()
                ):
                    continue

                degree_level = self._detect_degree_level(text, absolute_url)

                program_info = {
                    "program_name": text,
                    "program_url": absolute_url,
                    "category": detected_category,
                    "degree_level": degree_level,
                }

                if not any(
                    p["program_url"] == absolute_url for p in discovered_programs
                ):
                    if not any(
                        p["program_url"] == absolute_url for p in existing_programs
                    ):
                        discovered_programs.append(program_info)

        return discovered_programs

    def _extract_program_name_from_url(self, url: str) -> str:
        """Extract a readable program name from a URL slug."""
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.rstrip("/").split("/") if p]

        if not path_parts:
            return ""

        # Get the last meaningful segment
        slug = path_parts[-1].replace(".html", "").replace(".htm", "")

        # Convert slug to title (e.g., "aerospace-bachelor-of-science-bsc" -> "Aerospace Bachelor of Science BSc")
        words = slug.replace("-", " ").replace("_", " ").split()

        # Capitalize properly
        title_words = []
        for word in words:
            if word.upper() in [
                "BSC",
                "MSC",
                "MBA",
                "PHD",
                "BA",
                "MA",
                "MENG",
                "BENG",
                "LLM",
                "LLB",
            ]:
                title_words.append(word.upper())
            elif word.lower() in ["of", "and", "in", "for", "the", "with"]:
                title_words.append(word.lower())
            else:
                title_words.append(word.capitalize())

        return " ".join(title_words)

    def _is_program_link(self, url: str, link_text: str) -> bool:
        """Check if a link is likely a program/course link."""
        url_lower = url.lower()
        text_lower = link_text.lower()

        # ========== PRIORITY PATTERN: TUM /detail/ URLs ==========
        # TUM program pages have /detail/{program-slug} pattern
        # These links often have generic text like "read more" so we check URL first
        if "/detail/" in url_lower and "/degree-programs/" in url_lower:
            # Validate it's a real program slug (not just /detail/ alone)
            detail_match = re.search(r"/detail/([a-z0-9-]+)/?$", url_lower)
            if detail_match:
                program_slug = detail_match.group(1)
                # Must be a reasonable program name slug (hyphenated, >5 chars)
                if len(program_slug) > 5 and "-" in program_slug:
                    return True

        # Skip common non-program links by text
        skip_texts = [
            "home",
            "back",
            "next",
            "previous",
            "page",
            "more",
            "see all",
            "read more",
            "learn more",
            "click here",
            "view all",
            "contact",
            "enquire",
            "apply now",
            "apply online",
            "download",
            "print",
            "menu",
            "skip",
            "search",
            "login",
            "sign in",
            "subscribe",
            "follow us",
            "share",
            "tweet",
            "facebook",
            "twitter",
            "linkedin",
            "instagram",
            "youtube",
            "email",
            "phone",
            "address",
            "map",
            "privacy",
            "terms",
            "cookies",
            "accessibility",
            "sitemap",
            "about us",
            "about the",
            "our mission",
            "our values",
            "staff",
            "faculty",
            "alumni",
            "news",
            "events",
            "blog",
            "careers",
            "jobs",
            "vacancies",
            "work with us",
            "support researchers",
            "engage with us",
            "recognition",
            "partnerships",
            "collaboration",
            "funding",
            "grants",
            "where do i start",
            "getting started",
            "open days",
            "changes to",
            "departments",
            "research courses",
            "taught courses",
            "how to apply",
            "fees",
            "scholarships",
            "visa",
            "accommodation",
            "international",
            "student portal",
            "media information",
            "newsfeed",
            "contact",
        ]
        if any(skip in text_lower for skip in skip_texts):
            return False

        # STRICT URL path filtering - reject URLs that are clearly NOT program pages
        non_program_url_sections = [
            "/the-eth-zurich/",
            "/portrait/",
            "/sustainability/",
            "/working-teaching",
            "/vocational-education",
            "/quality-management/",
            "/educational-development/",
            "/ai-in-education/",
            "/information-material/",
            "/continuing-education",
            "/research/",
            "/news/",
            "/events/",
            "/open-science/",
            "/doctorate.",
            "/utils/",
            "/footer/",
            "/login/",
            "/search/",
            "/contact/",
            "/media/",
            "/about/",
            "/staff/",
            "/alumni/",
            "/careers/",
            "/jobs/",
            "/vacancies/",
            "/student-life/",
            "/wellbeing/",
            "/support/",
            "/finance/",
            "/prospective-students",
            "/application/",
            "/beginning-your",
            "/admissions/",
            "/funding/",
            "/scholarships/",
            "/fees/",
            # Section path patterns
            "getting-started",
            "taught-courses",
            "research-courses",
            "open-days",
            "changes-to",
            "departments",
            "how-to-apply",
            "fees-and-funding",
            "international-applicants",
            "advice-",
            "why-oxford",
            "sport-arts",
            "disability",
            "colleges",
            "entry-requirements",
            "general-information",
            "choosing-a",
            "masterprogrammas",
            "masters-programmes.",
            "bachelors-programmes.",
            "/d-arch/",
            "/d-baug/",
            "/d-biol/",
            "/d-bsse/",
            "/d-chab/",
            "/d-eaps/",
            "/d-gess/",
            "/d-hest/",
            "/d-infk/",
            "/d-itet/",
            "/d-math/",
            "/d-matl/",
            "/d-mavt/",
            "/d-mtec/",
            "/d-phys/",
            "/d-usys/",
        ]
        if any(pattern in url_lower for pattern in non_program_url_sections):
            return False

        # Reject generic listing pages (URLs that end with these)
        generic_url_endings = [
            "degree-programmes.html",
            "degree-programs.html",
            "bachelors-degree-programmes.html",
            "masters-degree-programmes.html",
            "/programmes.html",
            "/programs.html",
            "/courses.html",
            "/bachelors.html",
            "/masters.html",
            "/undergraduate.html",
            "/graduate.html",
            "/postgraduate.html",
            "/index.html",
        ]
        if any(url_lower.endswith(ending) for ending in generic_url_endings):
            return False

        # === POSITIVE MATCHING PATTERNS ===

        # PATTERN 0: TUM Germany style - /detail/{program-slug}
        # e.g., /en/studies/degree-programs/detail/informatics-master-of-science-msc
        if "/detail/" in url_lower:
            # Extract the program slug after /detail/
            detail_match = re.search(r"/detail/([a-z0-9-]+)/?$", url_lower)
            if detail_match:
                program_slug = detail_match.group(1)
                # Ensure it's not a generic page
                if len(program_slug) > 5 and "-" in program_slug:
                    return True

        # PATTERN 1: ETH Zurich & similar - nested program structure
        # /degree-programmes/{category}/{specific-program}.html
        eth_program_pattern = re.search(
            r"/degree-programmes?/[^/]+/([a-z0-9-]+)\.html$", url_lower
        )
        if eth_program_pattern:
            program_slug = eth_program_pattern.group(1)
            # Exclude category overview pages
            category_slugs = [
                "engineering-sciences",
                "natural-sciences-and-mathematics",
                "architecture-and-civil-engineering",
                "management-and-social-sciences",
                "system-oriented-natural-sciences",
            ]
            if program_slug not in category_slugs:
                return True

        # PATTERN 2: Oxford/UK style - degree prefix in URL
        # /msc-computer-science, /dphil-chemistry, /pgdip-theology
        degree_prefixes = [
            r"/msc-[a-z]",
            r"/ma-[a-z]",
            r"/mba[/-]?",
            r"/mth-[a-z]",
            r"/mst-[a-z]",
            r"/bsc-[a-z]",
            r"/ba-[a-z]",
            r"/beng-[a-z]",
            r"/meng-[a-z]",
            r"/phd-[a-z]",
            r"/dphil-[a-z]",
            r"/dphil\b",
            r"/phd\b",
            r"/llm-[a-z]",
            r"/llb-[a-z]",
            r"/med-[a-z]",
            r"/md-[a-z]",
            r"/mph-[a-z]",
            r"/mph\b",
            r"/mphil-[a-z]",
            r"/mres-[a-z]",
            r"/pgcert-[a-z]",
            r"/pgdip-[a-z]",
            r"/postgrad-[a-z]",
            r"/mlitt-[a-z]",
            r"/mmus-[a-z]",
            r"/march-[a-z]",
            r"/msci-[a-z]",
            r"/mmath-[a-z]",
            r"/mchem-[a-z]",
            r"/mphys-[a-z]",
        ]
        if any(re.search(pattern, url_lower) for pattern in degree_prefixes):
            return True

        # PATTERN 3: URL path structure analysis
        parsed = urlparse(url_lower)
        path_parts = [p for p in parsed.path.rstrip("/").split("/") if p]

        if len(path_parts) >= 2:
            last_segment = path_parts[-1].replace(".html", "").replace(".htm", "")
            parent_segment = path_parts[-2]

            # Skip generic list endings
            generic_endings = [
                "courses",
                "programmes",
                "programs",
                "degrees",
                "undergraduate",
                "postgraduate",
                "graduate",
                "taught",
                "research",
                "admissions",
                "study",
                "index",
                "listing",
                "list",
                "all",
                "a-z",
                "course-listing",
                "masters-programmes",
                "bachelors-programmes",
                "phd-programmes",
                "masters",
                "bachelors",
                "overview",
            ]
            if last_segment in generic_endings:
                return False

            # URL last segment starts with degree code (e.g., msc-advanced-computing)
            degree_codes = [
                "msc",
                "ma",
                "mba",
                "mth",
                "mst",
                "bsc",
                "ba",
                "beng",
                "meng",
                "phd",
                "dphil",
                "llm",
                "llb",
                "med",
                "md",
                "mph",
                "mphil",
                "mres",
                "pgcert",
                "pgdip",
                "mlitt",
                "mmus",
                "march",
                "msci",
                "mmath",
                "mchem",
                "mphys",
            ]

            for code in degree_codes:
                if last_segment.startswith(f"{code}-") or last_segment == code:
                    return True

            # PATTERN 4: Degree directory + program slug (like Utrecht /masters/{program})
            degree_directories = [
                "masters",
                "bachelors",
                "undergraduate",
                "postgraduate",
                "graduate",
                "phd",
                "doctoral",
                "research-degrees",
                "master",
                "bachelor",
                "master-s",
                "bachelor-s",
            ]

            if parent_segment in degree_directories:
                # Last segment should be specific program name
                if "-" in last_segment and len(last_segment) > 5:
                    # Make sure query params don't indicate a filter page
                    if "?" not in url_lower:
                        non_program_text = [
                            "contact",
                            "info",
                            "about",
                            "apply",
                            "faq",
                            "news",
                            "events",
                            "all-programmes",
                            "overview",
                            "all-courses",
                            "course-listing",
                        ]
                        if not any(npt in text_lower for npt in non_program_text):
                            return True

            # PATTERN 4b: Imperial UK style - /study/courses/{type}/{year}/{program}/
            # e.g., /study/courses/postgraduate-taught/2026/advanced-computing/
            if len(path_parts) >= 4:
                if "courses" in path_parts:
                    courses_idx = path_parts.index("courses")
                    if courses_idx + 2 < len(path_parts):
                        course_type = path_parts[courses_idx + 1]
                        year_or_category = path_parts[courses_idx + 2]
                        # Check if year_or_category is a year (2024, 2025, 2026) or course name
                        if (
                            year_or_category.isdigit()
                            and len(path_parts) > courses_idx + 3
                        ):
                            program_slug = path_parts[courses_idx + 3]
                        else:
                            program_slug = year_or_category

                        # Ensure it's not a generic page
                        if program_slug not in generic_endings and "-" in program_slug:
                            # Additional check - avoid admin/info pages
                            admin_paths = [
                                "offer-holders",
                                "application-process",
                                "teachers-conference",
                                "imperial-on-tour",
                                "information-by-region",
                                "executive-education",
                            ]
                            if program_slug not in admin_paths:
                                return True

            # PATTERN 5: Check link text for academic program indicators
            # Only if URL has a reasonable course-like slug
            if "-" in last_segment and len(last_segment) > 8 and len(text_lower) > 10:
                # Text should contain subject keywords
                subject_keywords = [
                    "science",
                    "arts",
                    "engineering",
                    "business",
                    "medicine",
                    "law",
                    "education",
                    "computer",
                    "computing",
                    "data",
                    "software",
                    "network",
                    "information",
                    "management",
                    "finance",
                    "accounting",
                    "marketing",
                    "economics",
                    "nursing",
                    "pharmacy",
                    "healthcare",
                    "clinical",
                    "medical",
                    "teaching",
                    "curriculum",
                    "mathematics",
                    "physics",
                    "chemistry",
                    "biology",
                    "psychology",
                    "history",
                    "philosophy",
                    "literature",
                    "linguistics",
                    "sociology",
                    "politics",
                    "international",
                    "environmental",
                    "sustainability",
                    "energy",
                    "architecture",
                    "theology",
                    "archaeology",
                    "anthropology",
                    "geography",
                    "music",
                    "biotechnology",
                    "bioinformatics",
                    "robotics",
                    "quantum",
                    "nuclear",
                    "materials",
                    "mechanical",
                    "electrical",
                    "civil",
                    "cyber",
                    "security",
                ]

                # Also require text to NOT be navigation-like
                if any(kw in text_lower for kw in subject_keywords):
                    # Additional check: text should look like a program title
                    if not any(
                        skip in text_lower for skip in ["department", "d-", "faculty"]
                    ):
                        return True

        return False

    def _detect_category(self, text: str, url: str) -> str:
        """Detect the program category from text and URL."""
        combined = f"{text} {url}".lower()

        for category, keywords in PROGRAM_CATEGORIES.items():
            if any(kw in combined for kw in keywords):
                return category

        return "Other"

    def _detect_degree_level(self, text: str, url: str) -> str:
        """Detect the degree level from text and URL."""
        combined = f"{text} {url}".lower()

        # Check in order of specificity
        if any(
            kw in combined
            for kw in ["phd", "doctor", "doctoral", "dphil", "research degree"]
        ):
            return "PhD"
        if any(
            kw in combined
            for kw in [
                "master",
                "msc",
                "ma",
                "mba",
                "meng",
                "mphil",
                "postgraduate taught",
            ]
        ):
            return "Masters"
        if any(
            kw in combined for kw in ["bachelor", "bsc", "ba", "beng", "undergraduate"]
        ):
            return "Undergraduate"
        if any(kw in combined for kw in ["graduate", "postgraduate"]):
            return "Graduate"

        return "Unknown"

    async def discover_program_links(
        self, base_url: str, max_pages: int = 10, max_depth: int = 2
    ) -> List[str]:
        """
        Discover program-related links from a university website.

        Args:
            base_url: Base URL of the university website
            max_pages: Maximum number of pages to crawl
            max_depth: Maximum crawl depth

        Returns:
            List of discovered program URLs
        """
        logger.info(f"Starting link discovery from {base_url}")

        discovered_links: Set[str] = set()
        visited_urls: Set[str] = set()

        async with AsyncWebCrawler() as crawler:
            await self._crawl_recursive(
                crawler,
                base_url,
                discovered_links,
                visited_urls,
                max_pages,
                max_depth,
                current_depth=0,
            )

        program_links = list(discovered_links)
        logger.info(f"Discovered {len(program_links)} program links")
        return program_links

    async def _crawl_recursive(
        self,
        crawler: AsyncWebCrawler,
        url: str,
        discovered_links: Set[str],
        visited_urls: Set[str],
        max_pages: int,
        max_depth: int,
        current_depth: int,
    ) -> None:
        """Recursively crawl pages to discover links."""

        if current_depth > max_depth or len(visited_urls) >= max_pages:
            return

        if url in visited_urls:
            return

        visited_urls.add(url)

        try:
            # Crawl the page
            result = await crawler.arun(url=url, timeout=self.timeout)

            if not result.success:
                logger.warning(f"Failed to crawl {url}")
                return

            # Extract links from the page
            soup = result.soup
            if not soup:
                return

            links = soup.find_all("a", href=True)
            page_links = []

            for link in links:
                href = link.get("href")
                if href:
                    absolute_url = urljoin(url, href)
                    if self._is_relevant_link(absolute_url, url):
                        page_links.append(absolute_url)

            # Filter for program links
            for link_url in page_links:
                if self._is_program_page(link_url):
                    discovered_links.add(link_url)

            # Recursively crawl relevant internal links
            internal_links = [
                link for link in page_links[:5] if self._is_internal_link(link, url)
            ]

            for internal_link in internal_links:
                await self._crawl_recursive(
                    crawler,
                    internal_link,
                    discovered_links,
                    visited_urls,
                    max_pages,
                    max_depth,
                    current_depth + 1,
                )

        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")

    def _is_relevant_link(self, url: str, base_url: str) -> bool:
        """Check if a link is relevant for crawling."""
        try:
            parsed = urlparse(url)

            # Skip non-HTTP URLs
            if parsed.scheme not in ["http", "https"]:
                return False

            # Skip external links (unless they're university subdomains)
            if not self._is_internal_link(url, base_url):
                return False

            # Skip excluded patterns
            url_lower = url.lower()
            if any(pattern in url_lower for pattern in self.exclude_patterns):
                return False

            # Skip file downloads
            if any(
                url_lower.endswith(ext)
                for ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx"]
            ):
                return False

            return True

        except Exception:
            return False

    def _is_internal_link(self, url: str, base_url: str) -> bool:
        """Check if a link is internal to the university website."""
        try:
            base_domain = urlparse(base_url).netloc
            link_domain = urlparse(url).netloc

            # Allow subdomains of the base domain
            return link_domain.endswith(base_domain) or base_domain.endswith(
                link_domain
            )

        except Exception:
            return False

    def _is_program_page(self, url: str) -> bool:
        """Check if a URL likely contains program information."""
        url_lower = url.lower()

        # Check for program-related keywords in URL
        keyword_matches = sum(
            1 for keyword in self.program_keywords if keyword in url_lower
        )

        # Check for common program page patterns
        pattern_matches = 0
        program_patterns = [
            "/program",
            "/course",
            "/study",
            "/degree",
            "/masters",
            "/phd",
            "/undergraduate",
            "/graduate",
            "/academic",
            "/admission",
        ]

        for pattern in program_patterns:
            if pattern in url_lower:
                pattern_matches += 1

        # Consider it a program page if it has multiple keyword matches or pattern matches
        return keyword_matches >= 2 or pattern_matches >= 1

    async def validate_program_urls(self, urls: List[str]) -> List[str]:
        """
        Validate that URLs are accessible and contain program information.

        Args:
            urls: List of URLs to validate

        Returns:
            List of valid program URLs
        """
        logger.info(f"Validating {len(urls)} program URLs")

        valid_urls = []

        async with AsyncWebCrawler() as crawler:
            # Process in batches to avoid overwhelming the server
            batch_size = 5

            for i in range(0, len(urls), batch_size):
                batch = urls[i : i + batch_size]

                tasks = []
                for url in batch:
                    tasks.append(self._validate_single_url(crawler, url))

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for url, result in zip(batch, results):
                    if isinstance(result, Exception):
                        logger.warning(f"Validation failed for {url}: {result}")
                    elif result:
                        valid_urls.append(url)

                # Rate limiting
                await asyncio.sleep(1)

        logger.info(f"Validated {len(valid_urls)} out of {len(urls)} URLs")
        return valid_urls

    async def _validate_single_url(self, crawler: AsyncWebCrawler, url: str) -> bool:
        """Validate a single URL."""
        try:
            result = await crawler.arun(
                url=url,
                timeout=self.timeout,
                only_text=True,  # We only need text content for validation
            )

            if not result.success:
                return False

            content = result.markdown or ""
            content_lower = content.lower()

            # Check if content contains program-related keywords
            program_indicators = [
                "computer science",
                "masters",
                "bachelor",
                "phd",
                "admission requirements",
                "tuition",
                "application deadline",
            ]

            matches = sum(
                1 for indicator in program_indicators if indicator in content_lower
            )

            return matches >= 2

        except Exception as e:
            logger.debug(f"URL validation error for {url}: {e}")
            return False

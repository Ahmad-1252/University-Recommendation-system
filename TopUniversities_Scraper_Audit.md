# TopUniversities Scraper Audit Report

## 1. Scraper Overview

The `TopUniversitiesScraper` (`src/scrapers/topuniversities_scraper.py`) is the core engine responsible for extracting world university rankings, subject-specific rankings, university profiles, and detailed program data from TopUniversities.com.

Originally built as a pure Playwright HTML scraper (as documented in older integration guides), the system has evolved into a massively scalable **hybrid API + Headless Browser** architecture (1,400+ lines of code) specifically optimized for high-volume data extraction.

## 2. Architecture & Extraction Methods

### A. Primary Strategy: Internal JSON APIs

The scraper intercepts and utilizes TopUniversities' internal undocumented JSON endpoints:

- **Rankings API** (`/sites/default/files/qs-rankings-data/en/`): For World and Subject rankings.
- **Programs API** (`/pd/endpoint`): For discovery of up to ~143,000 global programs.

This approach bypasses HTML parsing entirely for bulk data, resulting in tremendous speed improvements and significantly lower block rates. Uses `httpx.AsyncClient` for highly concurrent, async network IO.

### B. Fallback Strategy: Playwright Headless Browser

Used exclusively for deep profile pages (`/universities/*`) that heavily rely on JavaScript rendering for dynamic content (tabs, charts).

- The scraper implements a lazy-loading trigger (scrolling) and context-managed browser sessions.

### C. Advanced Deep Scraping

The `scrape_programs_with_details` method performs a Two-Stage Extraction:

1. Fast API discovery of program URLs.
2. Direct HTTP fetching of specific program pages using `BeautifulSoup` to parse 26 distinct fields (tuition fees, duration, entry requirements, metrics).

## 3. Data Processing & Normalization

The scraper doesn't just fetch raw HTML; it contains sophisticated, defensive data cleaning logic directly tied to the database requirements:

- **Pipeline script (`scripts/fetch_programs_to_db.py`)**: Converts scraped dictionaries into Pydantic `UniversityProgram` models.
- **Degree Normalization**: Uses regex to clean program names, strip zero-width characters, and map variations (e.g., "MSc", "MA") to standard "Master of Science".
- **Tuition Parsing**: `parse_tuition_fee()` extracts numeric amounts and currency codes from messy strings (e.g., "£9,250", "43,800 GBP").
- **Duration Parsing**: Converts textual durations ("18 months", "2 years") into numeric floats (1.5, 2.0).

## 4. Anti-Bot & Rate Limiting

TopUniversities utilizes WAF protection (such as Cloudflare/AWS WAF). The scraper implements several defense mechanisms:

- **User-Agent Rotation**: A pool of modern Chrome Windows/Mac user agents.
- **Connection Pooling**: Reuses HTTP/2 connections to look like legitimate persistent browser traffic.
- **Dynamic Rate Limiting**: `_rate_limit_delay(fast=True/False)` supports a "Turbo Mode" (0.05s - 0.15s) for API calls and a fallback mode matching the site's `robots.txt` directive (10s + jitter) to avoid IP bans.
- **Semaphore Concurrency**: API pagination is throttled using `asyncio.Semaphore` to prevent overwhelming the target server.

## 5. Execution Pipelines & Integration

- Integrated tightly with MongoDB (`src/database/repositorities/ProgramRepository`).
- CLI Execution (`fetch_programs_to_db.py`) allows granular controls: `--max`, `--level`, `--deep` (enables BeautifulSoup deep page scrape), and `--json` to save raw outputs.
- Contains real-time progress callbacks for CLI visuals.

## 6. Code Quality & Scalability

- **Quality**: ⭐⭐⭐⭐⭐. The code is exceptionally well-structured, strongly typed using Python `typing` module, and heavily documented with docstrings explaining edge cases and parsing decisions. Context managers (`__aenter__`, `__aexit__`) ensure resources are cleanly released.
- **Scalability**: High. The shift from Playwright to internal APIs for the bulk of program discovery enables the system to realistically index ~150,000 programs in hours, not weeks.

## 7. Risk Assessment

1. **Undocumented API Dependency (Medium-High Risk)**
   - The primary extraction engine relies on `/pd/endpoint` and `/sites/default/files/qs-rankings-data/...`. If TopUniversities alters their frontend architecture or API routing, the scraper will fail immediately.
2. **BeautifulSoup Deep Scrape Selectors (Medium Risk)**
   - The deep program extraction maps dozens of CSS classes. Websites frequently update their UI, which will silently break specific field extraction (e.g., tuition fees showing as null). (Evidence: Historical test reports show selector breakage is the #1 failure mode).
3. **IP Blocking on Deep Scrape (Low-Medium Risk)**
   - While API fetches are fast, doing 143,000 deep HTTP requests to program pages, even with Semaphore delays, is highly likely to trigger WAF blocks without residential proxy rotation. Currently, no explicit proxy mapping code was observed in the HTTP client constructor.

## 8. Recommended Improvements

1. **Proxy Rotation Integration**: Add residential or rotating datacenter proxy support to `_get_http_client()` to ensure the `--deep` script can run uninterrupted over 100,000+ requests.
2. **Selector Health Checks**: Run a daily "canary" test on 5 fixed URLs to ensure all 26 CSS selectors in `_extract_page_fields` return valid data. Alert immediately if `None` is returned for critical fields.
3. **Decouple Normalization**: Move the intense string parsing (`parse_tuition_fee`, `parse_duration`) completely into `src/utils` or a dedicated data-cleaning service, keeping the scraper strictly responsible for DOM extraction.

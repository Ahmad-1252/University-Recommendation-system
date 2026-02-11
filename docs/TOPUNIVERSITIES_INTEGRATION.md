# TopUniversities.com Integration

This document describes the integration of TopUniversities.com as a data source for university rankings and metadata.

## Overview

The TopUniversities.com integration provides:
- **World university rankings** (QS World Rankings)
- **Subject-specific rankings** (Computer Science, Business, etc.)
- **University profile data** (location, student counts, etc.)
- **Automatic ranking enrichment** for existing universities in the database

## Architecture

### New Components

1. **TopUniversitiesScraper** (`src/scrapers/topuniversities_scraper.py`)
   - Playwright-based scraper for dynamic content
   - Scrapes world rankings, subject rankings, and university profiles
   - Handles pagination and lazy-loaded content
   - Search functionality for finding universities

2. **RankingService** (`src/services/ranking_service.py`)
   - Centralized service for managing rankings
   - Caching layer with 7-day TTL
   - Batch update capabilities
   - Supports multiple ranking sources

3. **Enhanced EnrichmentService** (`src/services/enrichment_service.py`)
   - Integrated with RankingService
   - Enriches programs and universities with fresh rankings
   - Prioritizes TopUniversities data over static metadata

4. **Configuration** (`src/core/constants.py`)
   - `TOPUNIVERSITIES_CONFIG`: URLs, selectors, rate limiting
   - `UNIVERSITY_NAME_MAPPING`: Maps internal names to TopUniversities names

### Data Flow

```
TopUniversities.com
        ↓
TopUniversitiesScraper
        ↓
RankingService (with caching)
        ↓
EnrichmentService
        ↓
Database (MongoDB)
```

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
python -m playwright install chromium
```

## Usage

### 1. Test the Integration

Run the test suite to verify everything works:

```bash
python scripts/test_topuniversities.py
```

This will test:
- World rankings scraping
- University search
- Subject rankings
- Ranking service caching
- University object updates

### 2. Enrich Existing Universities

Update all universities in your database with fresh rankings:

```bash
# Update all universities
python scripts/enrich_with_topuniversities.py

# Update specific university
python scripts/enrich_with_topuniversities.py --university "Oxford"

# Force fresh data fetch (ignore cache)
python scripts/enrich_with_topuniversities.py --force-refresh

# Save report to file
python scripts/enrich_with_topuniversities.py --output reports/enrichment_report.json
```

### 3. Programmatic Usage

#### Fetch World Rankings

```python
from services.ranking_service import RankingService

async def get_rankings():
    service = RankingService()
    
    # Fetch top 100 universities
    rankings = await service.fetch_world_rankings(max_results=100)
    
    for rank in rankings[:10]:
        print(f"{rank['rank']}. {rank['university_name']} - {rank['country']}")
```

#### Update Single University

```python
from services.ranking_service import RankingService
from database.repositories import UniversityRepository
from database.mongodb import MongoDBConnection

async def update_university(university_name: str):
    # Setup database
    db = MongoDBConnection()
    await db.connect()
    repo = UniversityRepository(db)
    
    # Get university
    universities = await repo.find_by_name(university_name)
    if not universities:
        print("University not found")
        return
    
    university = universities[0]
    
    # Update rankings
    service = RankingService()
    updated = await service.update_university_rankings(university)
    
    # Save
    await repo.save(updated)
    
    print(f"Updated {updated.name}: QS Rank = {updated.qs_world_ranking}")
    
    await db.disconnect()
```

#### Enrich Programs During Scraping

```python
from services.enrichment_service import EnrichmentService
from services.ranking_service import RankingService
from scrapers.university_scraper import UniversityScraper

async def scrape_with_enrichment(url: str):
    # Setup services
    ranking_service = RankingService()
    enrichment_service = EnrichmentService(ranking_service=ranking_service)
    scraper = UniversityScraper()
    
    # Scrape program
    program = await scraper.scrape_program_data(url)
    
    # Enrich with rankings
    enriched_program = await enrichment_service.enrich_program_data(program)
    
    print(f"Program: {enriched_program.program_name}")
    print(f"University: {enriched_program.university_name}")
    print(f"QS Rank: {enriched_program.rankings.qs_world_ranking}")
```

## Configuration

### TopUniversities Configuration

Edit `src/core/constants.py` to customize:

```python
TOPUNIVERSITIES_CONFIG = {
    "base_url": "https://www.topuniversities.com",
    "urls": {
        "world_rankings": "...",
        "subject_rankings": "...",
        # ...
    },
    "selectors": {
        "ranking_item": "div[data-testid='ranking-item']",
        # ... CSS selectors for scraping
    },
    "rate_limiting": {
        "delay_seconds": 2,  # Delay between requests
        "max_retries": 3,
        "timeout_seconds": 30
    }
}
```

### University Name Mapping

If TopUniversities uses different names than your database:

```python
UNIVERSITY_NAME_MAPPING = {
    "UCL": "UCL (University College London)",
    "Imperial College London": "Imperial College London",
    # Add mappings as needed
}
```

## API Reference

### TopUniversitiesScraper

```python
class TopUniversitiesScraper(BaseScraper):
    async def scrape_world_rankings(
        self, 
        year: Optional[int] = None,
        max_results: int = 500
    ) -> List[Dict[str, Any]]
    
    async def scrape_subject_rankings(
        self,
        subject: str,  # e.g., "computer-science"
        year: Optional[int] = None,
        max_results: int = 200
    ) -> List[Dict[str, Any]]
    
    async def scrape_university_profile(
        self,
        university_url: str
    ) -> Dict[str, Any]
    
    async def search_university(
        self,
        university_name: str
    ) -> Optional[str]  # Returns profile URL
```

### RankingService

```python
class RankingService:
    async def fetch_world_rankings(
        self,
        year: Optional[int] = None,
        max_results: int = 500,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]
    
    async def fetch_subject_rankings(
        self,
        subject: str,
        year: Optional[int] = None,
        max_results: int = 200,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]
    
    async def update_university_rankings(
        self,
        university: University,
        force_refresh: bool = False
    ) -> University
    
    async def batch_update_rankings(
        self,
        universities: List[University],
        force_refresh: bool = False
    ) -> List[University]
    
    async def get_university_ranking(
        self,
        university_name: str,
        source: str = RankingSource.TOPUNIVERSITIES
    ) -> Optional[Dict[str, Any]]
```

## Data Model Updates

### University Model

The `University` model now has enhanced ranking support:

```python
class University(BaseModel):
    # Existing rankings
    qs_world_ranking: Optional[int]
    the_world_ranking: Optional[int]
    us_news_ranking: Optional[int]
    arwu_ranking: Optional[int]
    
    # Subject rankings (expandable)
    subject_rankings: Dict[str, int]
    
    # Metadata
    updated_at: datetime
```

### UniversityProgram Model

Programs inherit university rankings through enrichment:

```python
class UniversityProgram(BaseModel):
    rankings: Rankings  # Includes QS, THE, US News
    
    # Rankings object
    class Rankings(BaseModel):
        qs_world_ranking: Optional[int]
        the_world_ranking: Optional[int]
        us_news_ranking: Optional[int]
        subject_ranking: Optional[int]
```

## Performance & Caching

### Cache Strategy

- **Cache TTL**: 7 days (rankings update annually)
- **Cache Key Format**: `{dataset}_{subject}_{year}`
- **Cache Storage**: In-memory dictionary (can be extended to Redis)

### Rate Limiting

- **Delay between requests**: 2 seconds
- **Max concurrent requests**: Limited by Playwright browser instances
- **Timeout**: 30 seconds per page

### Optimization Tips

1. **Use cache**: Set `use_cache=True` for repeated queries
2. **Batch updates**: Use `batch_update_rankings()` for multiple universities
3. **Specify max_results**: Limit results to what you need
4. **Schedule updates**: Run enrichment weekly/monthly, not in real-time

## Troubleshooting

### Issue: Playwright not installed

```bash
python -m playwright install chromium
```

### Issue: Selectors not working

TopUniversities.com may update their website structure. Update selectors in `TOPUNIVERSITIES_CONFIG`:

```python
"selectors": {
    "ranking_item": "div[data-testid='ranking-item']",  # Update if changed
    # ...
}
```

### Issue: University not found

Add mapping in `UNIVERSITY_NAME_MAPPING`:

```python
UNIVERSITY_NAME_MAPPING = {
    "Your University Name": "TopUniversities Name",
}
```

### Issue: Slow scraping

- Reduce `max_results` parameter
- Ensure cache is enabled (`use_cache=True`)
- Increase rate limiting delay if getting blocked

## Future Enhancements

1. **Redis Integration**: Replace in-memory cache with Redis for persistence
2. **Scheduled Updates**: Automatic weekly ranking updates via cron
3. **More Ranking Sources**: Add THE, US News, ARWU scrapers
4. **University Profiles**: Scrape full profiles with facilities, faculty counts, etc.
5. **Historical Rankings**: Track ranking changes over time
6. **API Endpoints**: Expose rankings via FastAPI endpoints

## Examples

See:
- `scripts/test_topuniversities.py` - Test suite
- `scripts/enrich_with_topuniversities.py` - Batch enrichment script

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review test script for working examples
3. Check logs for detailed error messages
4. Verify Playwright installation and browser drivers

## License

Same as parent project.

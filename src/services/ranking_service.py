"""Service for managing and caching university rankings from multiple sources."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from core.config import get_settings
from models.university import University
from scrapers.topuniversities_scraper import TopUniversitiesScraper

logger = logging.getLogger(__name__)


class RankingSource:
    """Enumeration of ranking sources."""

    QS = "QS"
    THE = "THE"
    US_NEWS = "US_News"
    TOPUNIVERSITIES = "TopUniversities"
    ARWU = "ARWU"


class RankingService:
    """Service for fetching and managing university rankings."""

    def __init__(self):
        self.settings = get_settings()
        self.scraper = TopUniversitiesScraper()
        self.cache: Dict[str, Dict] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        self.cache_ttl = timedelta(days=7)  # Rankings update infrequently

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self.cache_expiry:
            return False
        return datetime.now() < self.cache_expiry[cache_key]

    def _set_cache(self, cache_key: str, data: Dict):
        """Set cache with expiry."""
        self.cache[cache_key] = data
        self.cache_expiry[cache_key] = datetime.now() + self.cache_ttl

    async def fetch_world_rankings(
        self, year: Optional[int] = None, max_results: int = 500, use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Fetch world university rankings from TopUniversities.com.

        Args:
            year: Year for rankings (None for latest)
            max_results: Maximum number of universities
            use_cache: Whether to use cached results

        Returns:
            List of ranking dictionaries
        """
        cache_key = f"world_rankings_{year or 'latest'}"

        if use_cache and self._is_cache_valid(cache_key):
            logger.info(f"Using cached rankings: {cache_key}")
            return self.cache[cache_key]

        logger.info(f"Fetching fresh world rankings for year {year or 'latest'}")

        try:
            async with self.scraper:
                rankings = await self.scraper.scrape_world_rankings(year, max_results)

            self._set_cache(cache_key, rankings)
            return rankings

        except Exception as e:
            logger.error(f"Error fetching world rankings: {e}")

            # Return cached data if available, even if expired
            if cache_key in self.cache:
                logger.info("Returning expired cache due to fetch failure")
                return self.cache[cache_key]

            return []

    async def fetch_subject_rankings(
        self,
        subject: str,
        year: Optional[int] = None,
        max_results: int = 200,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Fetch subject-specific rankings.

        Args:
            subject: Subject name (e.g., "computer-science")
            year: Year for rankings
            max_results: Maximum results
            use_cache: Whether to use cached results

        Returns:
            List of ranking dictionaries
        """
        cache_key = f"subject_rankings_{subject}_{year or 'latest'}"

        if use_cache and self._is_cache_valid(cache_key):
            logger.info(f"Using cached subject rankings: {cache_key}")
            return self.cache[cache_key]

        logger.info(f"Fetching fresh subject rankings for {subject}")

        try:
            async with self.scraper:
                rankings = await self.scraper.scrape_subject_rankings(
                    subject, year, max_results
                )

            self._set_cache(cache_key, rankings)
            return rankings

        except Exception as e:
            logger.error(f"Error fetching subject rankings: {e}")

            if cache_key in self.cache:
                return self.cache[cache_key]

            return []

    async def get_university_ranking(
        self, university_name: str, source: str = RankingSource.TOPUNIVERSITIES
    ) -> Optional[Dict[str, Any]]:
        """
        Get ranking for a specific university.

        Args:
            university_name: Name of the university
            source: Ranking source

        Returns:
            Ranking dictionary if found
        """
        # Fetch world rankings
        rankings = await self.fetch_world_rankings()

        # Normalize university name for matching
        normalized_search = self._normalize_name(university_name)

        for ranking in rankings:
            normalized_rank_name = self._normalize_name(
                ranking.get("university_name", "")
            )
            if (
                normalized_search in normalized_rank_name
                or normalized_rank_name in normalized_search
            ):
                return ranking

        return None

    def _normalize_name(self, name: str) -> str:
        """Normalize university name for matching."""
        if not name:
            return ""

        # Remove common prefixes/suffixes
        name = name.lower().strip()
        name = name.replace("university of", "")
        name = name.replace("the ", "")
        name = name.replace(",", "")
        name = name.strip()

        return name

    async def update_university_rankings(
        self, university: University, force_refresh: bool = False
    ) -> University:
        """
        Update a university's rankings from TopUniversities.com.

        Args:
            university: University object to update
            force_refresh: Force fresh data fetch

        Returns:
            Updated University object
        """
        logger.info(f"Updating rankings for {university.name}")

        try:
            # Fetch world rankings
            rankings = await self.fetch_world_rankings(use_cache=not force_refresh)

            # Find this university in rankings
            ranking_data = None
            normalized_name = self._normalize_name(university.name)

            for rank in rankings:
                if (
                    self._normalize_name(rank.get("university_name", ""))
                    == normalized_name
                ):
                    ranking_data = rank
                    break

            # Also check alternate names
            if not ranking_data and university.alternate_names:
                for alt_name in university.alternate_names:
                    normalized_alt = self._normalize_name(alt_name)
                    for rank in rankings:
                        if (
                            self._normalize_name(rank.get("university_name", ""))
                            == normalized_alt
                        ):
                            ranking_data = rank
                            break
                    if ranking_data:
                        break

            if ranking_data:
                # Update QS ranking (TopUniversities is owned by QS)
                if ranking_data.get("rank"):
                    university.qs_world_ranking = ranking_data["rank"]

                # Update location if not set
                if not university.country and ranking_data.get("country"):
                    university.country = ranking_data["country"]
                if not university.city and ranking_data.get("city"):
                    university.city = ranking_data["city"]

                logger.info(
                    f"Updated {university.name} with rank {ranking_data.get('rank')}"
                )
            else:
                logger.warning(f"No ranking found for {university.name}")

        except Exception as e:
            logger.error(f"Error updating rankings for {university.name}: {e}")

        return university

    async def batch_update_rankings(
        self, universities: List[University], force_refresh: bool = False
    ) -> List[University]:
        """
        Batch update rankings for multiple universities.

        Args:
            universities: List of University objects
            force_refresh: Force fresh data fetch

        Returns:
            List of updated University objects
        """
        logger.info(f"Batch updating rankings for {len(universities)} universities")

        # Fetch rankings once
        rankings = await self.fetch_world_rankings(use_cache=not force_refresh)

        # Create lookup map
        ranking_map = {}
        for rank in rankings:
            normalized = self._normalize_name(rank.get("university_name", ""))
            if normalized:
                ranking_map[normalized] = rank

        updated_universities = []

        for university in universities:
            try:
                # Try primary name
                normalized = self._normalize_name(university.name)
                ranking_data = ranking_map.get(normalized)

                # Try alternate names
                if not ranking_data and university.alternate_names:
                    for alt_name in university.alternate_names:
                        normalized_alt = self._normalize_name(alt_name)
                        ranking_data = ranking_map.get(normalized_alt)
                        if ranking_data:
                            break

                if ranking_data:
                    if ranking_data.get("rank"):
                        university.qs_world_ranking = ranking_data["rank"]
                    if not university.country and ranking_data.get("country"):
                        university.country = ranking_data["country"]
                    if not university.city and ranking_data.get("city"):
                        university.city = ranking_data["city"]

                    logger.info(
                        f"Updated {university.name} with rank {ranking_data.get('rank')}"
                    )

                updated_universities.append(university)

            except Exception as e:
                logger.error(f"Error updating {university.name}: {e}")
                updated_universities.append(university)

        return updated_universities

    async def get_subject_ranking_for_university(
        self, university_name: str, subject: str
    ) -> Optional[int]:
        """
        Get subject-specific ranking for a university.

        Args:
            university_name: Name of the university
            subject: Subject name (e.g., "computer-science")

        Returns:
            Ranking position if found
        """
        rankings = await self.fetch_subject_rankings(subject)

        normalized_search = self._normalize_name(university_name)

        for ranking in rankings:
            normalized_rank_name = self._normalize_name(
                ranking.get("university_name", "")
            )
            if (
                normalized_search in normalized_rank_name
                or normalized_rank_name in normalized_search
            ):
                return ranking.get("rank")

        return None

    async def get_rankings_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about cached rankings.

        Returns:
            Dictionary with cache statistics
        """
        summary = {"cached_datasets": len(self.cache), "datasets": []}

        for key, expiry in self.cache_expiry.items():
            is_valid = datetime.now() < expiry
            dataset_info = {
                "key": key,
                "valid": is_valid,
                "expires_at": expiry.isoformat(),
                "count": len(self.cache.get(key, [])),
            }
            summary["datasets"].append(dataset_info)

        return summary

    def clear_cache(self):
        """Clear all cached rankings."""
        self.cache.clear()
        self.cache_expiry.clear()
        logger.info("Cleared rankings cache")

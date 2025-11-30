"""Repository pattern implementation for data access."""

import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from database.mongodb import get_mongo_connection, mongo_session
from models.university import UniversityProgram, University
from core.exceptions import DuplicateDataError, QueryError

logger = logging.getLogger(__name__)

# Thread pool for running sync DB operations
_db_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="db_worker")


async def run_in_executor(func, *args, **kwargs):
    """
    Run a synchronous function in a thread pool executor.
    
    This prevents blocking the async event loop when calling sync DB operations.
    
    Args:
        func: The synchronous function to run
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the function call
    """
    loop = asyncio.get_running_loop()
    if kwargs:
        func = partial(func, **kwargs)
    return await loop.run_in_executor(_db_executor, func, *args)


def safe_regex(value: str) -> dict:
    """
    Create a safe MongoDB regex filter by escaping special characters.
    
    This prevents NoSQL injection via regex patterns like ReDoS attacks.
    
    Args:
        value: The string to search for
        
    Returns:
        MongoDB regex query dict with escaped value
    """
    if not value:
        return {}
    escaped = re.escape(value)
    return {"$regex": escaped, "$options": "i"}


class ProgramRepository:
    """Repository for UniversityProgram data operations."""

    def __init__(self):
        self.connection = get_mongo_connection()

    def save(self, program: UniversityProgram) -> bool:
        """
        Save a university program to the database.

        Args:
            program: UniversityProgram instance to save

        Returns:
            bool: True if saved successfully, False otherwise

        Raises:
            DuplicateDataError: If program with same URL already exists
        """
        try:
            with mongo_session() as conn:
                program_dict = program.model_dump()
                program_dict["last_updated"] = datetime.utcnow()

                # Use upsert to update if exists, insert if not
                result = conn.collection.replace_one(
                    {"source_url": program.source_url},
                    program_dict,
                    upsert=True
                )

                success = result.acknowledged
                if success:
                    operation = "updated" if result.modified_count > 0 else "inserted"
                    logger.info(f"Program {operation}: {program.program_name}")
                return success

        except Exception as e:
            logger.error(f"Failed to save program {program.program_name}: {e}")
            return False

    def save_many(self, programs: List[UniversityProgram]) -> Dict[str, int]:
        """
        Save multiple programs to the database.
        Creates universities first if they don't exist.

        Args:
            programs: List of UniversityProgram instances

        Returns:
            Dict with counts of inserted, updated, and failed operations
        """
        results = {"inserted": 0, "updated": 0, "failed": 0}

        # First, extract and save universities, get mapping of names to IDs
        university_id_map = self._create_universities_from_programs(programs)
        
        # Update programs with correct university_ids
        for program in programs:
            if program.university_name in university_id_map:
                program.university_id = university_id_map[program.university_name]

        for program in programs:
            try:
                with mongo_session() as conn:
                    program_dict = program.model_dump()
                    program_dict["last_updated"] = datetime.utcnow()

                    result = conn.collection.replace_one(
                        {"source_url": program.source_url},
                        program_dict,
                        upsert=True
                    )

                    if result.acknowledged:
                        if result.upserted_id:
                            results["inserted"] += 1
                        else:
                            results["updated"] += 1
                    else:
                        results["failed"] += 1

            except Exception as e:
                logger.error(f"Failed to save program {program.program_name}: {e}")
                results["failed"] += 1

        logger.info(f"Batch save completed: {results}")
        return results

    def _create_universities_from_programs(self, programs: List[UniversityProgram]) -> Dict[str, str]:
        """
        Extract university information from programs and create university records.

        Args:
            programs: List of programs to extract universities from

        Returns:
            Dictionary mapping university names to their IDs
        """
        from collections import defaultdict

        # Group programs by university to avoid duplicates
        university_data = defaultdict(dict)

        for program in programs:
            uni_key = program.university_name
            if uni_key not in university_data:
                # Create university from program data
                university = University(
                    name=program.university_name,
                    country=program.country,
                    city=program.city,
                    # Add any other fields that might be available in program data
                    # For now, we'll create minimal university records
                    # These can be enriched later by dedicated university scrapers
                )
                university_data[uni_key] = university

        # Save universities
        university_id_map = {}
        universities = list(university_data.values())
        if universities:
            university_repo = UniversityRepository()
            results = university_repo.save_many(universities)
            logger.info(f"Created/updated {results['inserted'] + results['updated']} universities from programs")
            
            # Build mapping of names to IDs
            for university in universities:
                university_id_map[university.name] = university.university_id

        return university_id_map

    def get_by_url(self, url: str) -> Optional[UniversityProgram]:
        """
        Get a program by its source URL.

        Args:
            url: Source URL of the program

        Returns:
            UniversityProgram instance or None if not found
        """
        try:
            with mongo_session() as conn:
                data = conn.collection.find_one({"source_url": url})
                return UniversityProgram(**data) if data else None
        except Exception as e:
            logger.error(f"Failed to get program by URL {url}: {e}")
            raise QueryError(f"Query failed: {e}") from e

    def get_by_university(self, university_name: str) -> List[UniversityProgram]:
        """
        Get all programs from a specific university.

        Args:
            university_name: Name of the university

        Returns:
            List of UniversityProgram instances
        """
        try:
            with mongo_session() as conn:
                cursor = conn.collection.find({"university_name": university_name})
                return [UniversityProgram(**doc) for doc in cursor]
        except Exception as e:
            logger.error(f"Failed to get programs for university {university_name}: {e}")
            raise QueryError(f"Query failed: {e}") from e

    def search(self,
               query: Optional[str] = None,
               country: Optional[str] = None,
               degree_type: Optional[str] = None,
               min_gpa: Optional[float] = None,
               max_tuition: Optional[int] = None,
               limit: int = 50) -> List[UniversityProgram]:
        """
        Search programs with various filters.

        Args:
            query: Text search in program name or description
            country: Filter by country
            degree_type: Filter by degree type
            min_gpa: Minimum GPA requirement
            max_tuition: Maximum tuition fee
            limit: Maximum number of results

        Returns:
            List of matching UniversityProgram instances
        """
        try:
            with mongo_session() as conn:
                mongo_query = {}

                # Text search
                if query:
                    mongo_query["$text"] = {"$search": query}

                # Country filter
                if country:
                    mongo_query["country"] = country

                # Degree type filter
                if degree_type:
                    mongo_query["degree_type"] = degree_type

                # GPA filter
                if min_gpa is not None:
                    mongo_query["gpa_requirement_min"] = {"$lte": min_gpa}

                # Tuition filter
                if max_tuition is not None:
                    mongo_query["tuition_fees.international_per_year"] = {"$lte": max_tuition}

                cursor = conn.collection.find(mongo_query).limit(limit)
                return [UniversityProgram(**doc) for doc in cursor]

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise QueryError(f"Search failed: {e}") from e

    def get_all_programs(self, limit: Optional[int] = None) -> List[UniversityProgram]:
        """
        Get all programs from the database.

        Args:
            limit: Maximum number of programs to return

        Returns:
            List of all UniversityProgram instances
        """
        try:
            with mongo_session() as conn:
                cursor = conn.collection.find()
                if limit:
                    cursor = cursor.limit(limit)
                return [UniversityProgram(**doc) for doc in cursor]
        except Exception as e:
            logger.error(f"Failed to get all programs: {e}")
            raise QueryError(f"Query failed: {e}") from e

    def get_recent_programs(self, days: int = 7) -> List[UniversityProgram]:
        """
        Get programs updated within the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of recently updated programs
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            with mongo_session() as conn:
                cursor = conn.collection.find({"last_updated": {"$gte": cutoff_date}})
                return [UniversityProgram(**doc) for doc in cursor]
        except Exception as e:
            logger.error(f"Failed to get recent programs: {e}")
            raise QueryError(f"Query failed: {e}") from e

    def delete_by_url(self, url: str) -> bool:
        """
        Delete a program by its source URL.

        Args:
            url: Source URL of the program to delete

        Returns:
            bool: True if deleted successfully
        """
        try:
            with mongo_session() as conn:
                result = conn.collection.delete_one({"source_url": url})
                success = result.deleted_count > 0
                if success:
                    logger.info(f"Deleted program with URL: {url}")
                return success
        except Exception as e:
            logger.error(f"Failed to delete program {url}: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with various statistics
        """
        try:
            with mongo_session() as conn:
                total_count = conn.collection.count_documents({})

                # Count by country
                countries = list(conn.collection.aggregate([
                    {"$group": {"_id": "$country", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}}
                ]))

                # Count by degree type
                degree_types = list(conn.collection.aggregate([
                    {"$group": {"_id": "$degree_type", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}}
                ]))

                # Average completeness and confidence
                stats = conn.collection.aggregate([
                    {"$group": {
                        "_id": None,
                        "avg_completeness": {"$avg": "$data_completeness"},
                        "avg_confidence": {"$avg": "$confidence_score"},
                        "min_tuition": {"$min": "$tuition_fees.international_per_year"},
                        "max_tuition": {"$max": "$tuition_fees.international_per_year"},
                        "avg_tuition": {"$avg": "$tuition_fees.international_per_year"}
                    }}
                ]).next()

                return {
                    "total_programs": total_count,
                    "countries": countries,
                    "degree_types": degree_types,
                    "avg_completeness": stats.get("avg_completeness", 0),
                    "avg_confidence": stats.get("avg_confidence", 0),
                    "tuition_range": {
                        "min": stats.get("min_tuition"),
                        "max": stats.get("max_tuition"),
                        "avg": stats.get("avg_tuition")
                    }
                }

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}

    async def count(self) -> int:
        """
        Get total count of programs.

        Returns:
            Total number of programs
        """
        return await run_in_executor(self._count_sync)

    def _count_sync(self) -> int:
        """Synchronous implementation of count."""
        try:
            with mongo_session() as conn:
                return conn.collection.count_documents({})
        except Exception as e:
            logger.error(f"Failed to count programs: {e}")
            return 0

    async def get_distinct_program_types(self) -> List[str]:
        """
        Get distinct program types.

        Returns:
            List of distinct program types
        """
        return await run_in_executor(self._get_distinct_program_types_sync)

    def _get_distinct_program_types_sync(self) -> List[str]:
        """Synchronous implementation of get_distinct_program_types."""
        try:
            with mongo_session() as conn:
                return list(conn.collection.distinct("degree_type"))
        except Exception as e:
            logger.error(f"Failed to get distinct program types: {e}")
            return []

    async def get_last_updated(self) -> Optional[datetime]:
        """
        Get the last updated timestamp.

        Returns:
            Last updated datetime or None
        """
        return await run_in_executor(self._get_last_updated_sync)

    def _get_last_updated_sync(self) -> Optional[datetime]:
        """Synchronous implementation of get_last_updated."""
        try:
            with mongo_session() as conn:
                result = conn.collection.find_one(
                    {},
                    sort=[("last_updated", -1)]
                )
                return result.get("last_updated") if result else None
        except Exception as e:
            logger.error(f"Failed to get last updated: {e}")
            return None

    async def get_by_id(self, program_id: str) -> Optional[UniversityProgram]:
        """
        Get a program by its ID.

        Args:
            program_id: Program ID

        Returns:
            UniversityProgram instance or None
        """
        return await run_in_executor(self._get_by_id_sync, program_id)

    def _get_by_id_sync(self, program_id: str) -> Optional[UniversityProgram]:
        """Synchronous implementation of get_by_id."""
        try:
            with mongo_session() as conn:
                data = conn.collection.find_one({"_id": program_id})
                return UniversityProgram(**data) if data else None
        except Exception as e:
            logger.error(f"Failed to get program by ID {program_id}: {e}")
            return None

    async def search_programs(self,
                            university_name: Optional[str] = None,
                            program_name: Optional[str] = None,
                            degree_level: Optional[str] = None,
                            field_of_study: Optional[str] = None,
                            country: Optional[str] = None,
                            limit: int = 20,
                            offset: int = 0) -> List[UniversityProgram]:
        """
        Search programs with filters.

        Args:
            university_name: Filter by university name
            program_name: Filter by program name
            degree_level: Filter by degree level
            field_of_study: Filter by field of study
            country: Filter by country
            limit: Maximum results
            offset: Results offset

        Returns:
            List of matching programs
        """
        return await run_in_executor(
            self._search_programs_sync,
            university_name, program_name, degree_level, field_of_study, country, limit, offset
        )

    def _search_programs_sync(self,
                             university_name: Optional[str] = None,
                             program_name: Optional[str] = None,
                             degree_level: Optional[str] = None,
                             field_of_study: Optional[str] = None,
                             country: Optional[str] = None,
                             limit: int = 20,
                             offset: int = 0) -> List[UniversityProgram]:
        """Synchronous implementation of search_programs."""
        try:
            with mongo_session() as conn:
                mongo_query = {}

                if university_name:
                    mongo_query["university_name"] = safe_regex(university_name)
                if program_name:
                    mongo_query["program_name"] = safe_regex(program_name)
                if degree_level:
                    mongo_query["degree_type"] = degree_level
                if field_of_study:
                    mongo_query["field_of_study"] = safe_regex(field_of_study)
                if country:
                    mongo_query["country"] = country

                cursor = conn.collection.find(mongo_query).skip(offset).limit(limit)
                return [UniversityProgram(**doc) for doc in cursor]

        except Exception as e:
            logger.error(f"Failed to search programs: {e}")
            raise QueryError(f"Search failed: {e}") from e

    # University-related methods
    async def get_distinct_countries(self) -> List[str]:
        """
        Get distinct countries.

        Returns:
            List of distinct countries
        """
        return await run_in_executor(self._get_distinct_countries_sync)

    def _get_distinct_countries_sync(self) -> List[str]:
        """Synchronous implementation of get_distinct_countries."""
        try:
            with mongo_session() as conn:
                return list(conn.collection.distinct("country"))
        except Exception as e:
            logger.error(f"Failed to get distinct countries: {e}")
            return []

    async def search_universities(self,
                                query: Optional[str] = None,
                                country: Optional[str] = None,
                                program_type: Optional[str] = None,
                                limit: int = 20,
                                offset: int = 0) -> List[Dict[str, Any]]:
        """
        Search universities with filters.

        Args:
            query: Search query for university name
            country: Filter by country
            program_type: Filter by program type
            limit: Maximum results
            offset: Results offset

        Returns:
            List of university info dictionaries
        """
        return await run_in_executor(
            self._search_universities_sync,
            query, country, program_type, limit, offset
        )

    def _search_universities_sync(self,
                                 query: Optional[str] = None,
                                 country: Optional[str] = None,
                                 program_type: Optional[str] = None,
                                 limit: int = 20,
                                 offset: int = 0) -> List[Dict[str, Any]]:
        """Synchronous implementation of search_universities."""
        try:
            with mongo_session() as conn:
                # Group by university to get unique universities
                pipeline = []

                # Match stage
                match_conditions = {}
                if country:
                    match_conditions["country"] = country
                if program_type:
                    match_conditions["degree_type"] = program_type
                if query:
                    match_conditions["university_name"] = safe_regex(query)

                if match_conditions:
                    pipeline.append({"$match": match_conditions})

                # Group by university
                pipeline.extend([
                    {"$group": {
                        "_id": {
                            "name": "$university_name",
                            "country": "$country",
                            "website": "$university_website"
                        },
                        "program_count": {"$sum": 1},
                        "program_types": {"$addToSet": "$degree_type"},
                        "last_updated": {"$max": "$last_updated"}
                    }},
                    {"$project": {
                        "university_name": "$_id.name",
                        "country": "$_id.country",
                        "website": "$_id.website",
                        "program_count": 1,
                        "program_types": 1,
                        "last_updated": 1,
                        "_id": 0
                    }},
                    {"$sort": {"university_name": 1}},
                    {"$skip": offset},
                    {"$limit": limit}
                ])

                cursor = conn.collection.aggregate(pipeline)
                return list(cursor)

        except Exception as e:
            logger.error(f"Failed to search universities: {e}")
            raise QueryError(f"Search failed: {e}") from e

    async def get_university_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get university info by name.

        Args:
            name: University name

        Returns:
            University info dictionary or None
        """
        try:
            universities = await self.search_universities(query=name, limit=1)
            return universities[0] if universities else None
        except Exception as e:
            logger.error(f"Failed to get university {name}: {e}")
            return None


class UniversityRepository:
    """Repository for University data operations."""

    def __init__(self):
        self.connection = get_mongo_connection()

    def save(self, university: University) -> bool:
        """
        Save a university to the database.

        Args:
            university: University instance to save

        Returns:
            bool: True if saved successfully, False otherwise

        Raises:
            DuplicateDataError: If university with same ID already exists
        """
        try:
            with mongo_session() as conn:
                university_dict = university.model_dump()
                university_dict["updated_at"] = datetime.utcnow()

                # Use upsert to update if exists, insert if not
                result = conn.universities_collection.replace_one(
                    {"university_id": university.university_id},
                    university_dict,
                    upsert=True
                )

                success = result.acknowledged
                if success:
                    operation = "updated" if result.modified_count > 0 else "inserted"
                    logger.info(f"University {operation}: {university.name}")
                return success

        except Exception as e:
            logger.error(f"Failed to save university {university.name}: {e}")
            return False

    def save_many(self, universities: List[University]) -> Dict[str, int]:
        """
        Save multiple universities to the database.

        Args:
            universities: List of University instances

        Returns:
            Dict with counts of inserted, updated, and failed operations
        """
        results = {"inserted": 0, "updated": 0, "failed": 0}

        for university in universities:
            try:
                with mongo_session() as conn:
                    university_dict = university.model_dump()
                    university_dict["updated_at"] = datetime.utcnow()

                    result = conn.universities_collection.replace_one(
                        {"university_id": university.university_id},
                        university_dict,
                        upsert=True
                    )

                    if result.acknowledged:
                        if result.upserted_id:
                            results["inserted"] += 1
                        else:
                            results["updated"] += 1
                    else:
                        results["failed"] += 1

            except Exception as e:
                logger.error(f"Failed to save university {university.name}: {e}")
                results["failed"] += 1

        logger.info(f"Batch university save completed: {results}")
        return results

    def get_by_id(self, university_id: str) -> Optional[University]:
        """
        Get a university by its ID.

        Args:
            university_id: University ID

        Returns:
            University instance or None if not found
        """
        try:
            with mongo_session() as conn:
                data = conn.universities_collection.find_one({"university_id": university_id})
                return University(**data) if data else None
        except Exception as e:
            logger.error(f"Failed to get university by ID {university_id}: {e}")
            raise QueryError(f"Query failed: {e}") from e

    def get_by_name(self, name: str) -> Optional[University]:
        """
        Get a university by its name.

        Args:
            name: University name

        Returns:
            University instance or None if not found
        """
        try:
            with mongo_session() as conn:
                data = conn.universities_collection.find_one({"name": name})
                return University(**data) if data else None
        except Exception as e:
            logger.error(f"Failed to get university by name {name}: {e}")
            raise QueryError(f"Query failed: {e}") from e

    def search(self,
               query: Optional[str] = None,
               country: Optional[str] = None,
               tier: Optional[str] = None,
               type_filter: Optional[str] = None,
               min_ranking: Optional[int] = None,
               max_ranking: Optional[int] = None,
               limit: int = 50) -> List[University]:
        """
        Search universities with various filters.

        Args:
            query: Text search in university name
            country: Filter by country
            tier: Filter by university tier
            type_filter: Filter by university type (public/private)
            min_ranking: Minimum QS ranking
            max_ranking: Maximum QS ranking
            limit: Maximum number of results

        Returns:
            List of matching University instances
        """
        try:
            with mongo_session() as conn:
                mongo_query = {}

                # Text search in name
                if query:
                    mongo_query["$or"] = [
                        {"name": safe_regex(query)},
                        {"alternate_names": {"$in": [safe_regex(query)["$regex"]]}}
                    ]

                # Country filter
                if country:
                    mongo_query["country"] = country

                # Tier filter
                if tier:
                    mongo_query["tier"] = tier

                # Type filter
                if type_filter:
                    mongo_query["type"] = type_filter

                # Ranking filters
                if min_ranking is not None or max_ranking is not None:
                    ranking_filter = {}
                    if min_ranking is not None:
                        ranking_filter["$lte"] = min_ranking
                    if max_ranking is not None:
                        ranking_filter["$gte"] = max_ranking
                    mongo_query["qs_world_ranking"] = ranking_filter

                cursor = conn.universities_collection.find(mongo_query).limit(limit)
                return [University(**doc) for doc in cursor]

        except Exception as e:
            logger.error(f"University search failed: {e}")
            raise QueryError(f"Search failed: {e}") from e

    def get_all_universities(self, limit: Optional[int] = None) -> List[University]:
        """
        Get all universities from the database.

        Args:
            limit: Maximum number of universities to return

        Returns:
            List of all University instances
        """
        try:
            with mongo_session() as conn:
                cursor = conn.universities_collection.find()
                if limit:
                    cursor = cursor.limit(limit)
                return [University(**doc) for doc in cursor]
        except Exception as e:
            logger.error(f"Failed to get all universities: {e}")
            raise QueryError(f"Query failed: {e}") from e

    def get_universities_by_country(self, country: str) -> List[University]:
        """
        Get all universities from a specific country.

        Args:
            country: Country name

        Returns:
            List of University instances
        """
        try:
            with mongo_session() as conn:
                cursor = conn.universities_collection.find({"country": country})
                return [University(**doc) for doc in cursor]
        except Exception as e:
            logger.error(f"Failed to get universities for country {country}: {e}")
            raise QueryError(f"Query failed: {e}") from e

    def delete_by_id(self, university_id: str) -> bool:
        """
        Delete a university by its ID.

        Args:
            university_id: University ID to delete

        Returns:
            bool: True if deleted successfully
        """
        try:
            with mongo_session() as conn:
                result = conn.universities_collection.delete_one({"university_id": university_id})
                success = result.deleted_count > 0
                if success:
                    logger.info(f"Deleted university with ID: {university_id}")
                return success
        except Exception as e:
            logger.error(f"Failed to delete university {university_id}: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get university database statistics.

        Returns:
            Dictionary with various statistics
        """
        try:
            with mongo_session() as conn:
                total_count = conn.universities_collection.count_documents({})

                # Count by country
                countries = list(conn.universities_collection.aggregate([
                    {"$group": {"_id": "$country", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}}
                ]))

                # Count by tier
                tiers = list(conn.universities_collection.aggregate([
                    {"$group": {"_id": "$tier", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}}
                ]))

                # Ranking statistics
                ranking_stats = conn.universities_collection.aggregate([
                    {"$group": {
                        "_id": None,
                        "avg_qs_ranking": {"$avg": "$qs_world_ranking"},
                        "min_qs_ranking": {"$min": "$qs_world_ranking"},
                        "max_qs_ranking": {"$max": "$qs_world_ranking"},
                        "avg_students": {"$avg": "$total_students"},
                        "total_endowment": {"$sum": "$endowment_usd"}
                    }}
                ])

                stats_result = next(ranking_stats, {})

                return {
                    "total_universities": total_count,
                    "countries": countries,
                    "tiers": tiers,
                    "ranking_stats": {
                        "avg_qs": stats_result.get("avg_qs_ranking"),
                        "min_qs": stats_result.get("min_qs_ranking"),
                        "max_qs": stats_result.get("max_qs_ranking")
                    },
                    "avg_students": stats_result.get("avg_students"),
                    "total_endowment_usd": stats_result.get("total_endowment")
                }

        except Exception as e:
            logger.error(f"Failed to get university statistics: {e}")
            return {}

    async def count(self) -> int:
        """
        Get total count of universities.

        Returns:
            Total number of universities
        """
        return await run_in_executor(self._count_sync)

    def _count_sync(self) -> int:
        """Synchronous implementation of count."""
        try:
            with mongo_session() as conn:
                return conn.universities_collection.count_documents({})
        except Exception as e:
            logger.error(f"Failed to count universities: {e}")
            return 0

    async def get_distinct_countries(self) -> List[str]:
        """
        Get distinct countries from universities.

        Returns:
            List of distinct countries
        """
        return await run_in_executor(self._get_distinct_countries_sync)

    def _get_distinct_countries_sync(self) -> List[str]:
        """Synchronous implementation of get_distinct_countries."""
        try:
            with mongo_session() as conn:
                return list(conn.universities_collection.distinct("country"))
        except Exception as e:
            logger.error(f"Failed to get distinct countries: {e}")
            return []

    async def get_top_ranked(self, limit: int = 10) -> List[University]:
        """
        Get top ranked universities.

        Args:
            limit: Maximum number of universities to return

        Returns:
            List of top ranked universities
        """
        return await run_in_executor(self._get_top_ranked_sync, limit)

    def _get_top_ranked_sync(self, limit: int = 10) -> List[University]:
        """Synchronous implementation of get_top_ranked."""
        try:
            with mongo_session() as conn:
                cursor = conn.universities_collection.find(
                    {"qs_world_ranking": {"$ne": None}}
                ).sort("qs_world_ranking", 1).limit(limit)
                return [University(**doc) for doc in cursor]
        except Exception as e:
            logger.error(f"Failed to get top ranked universities: {e}")
            return []

    def update_university_from_programs(self, university_id: str, extracted_data: Dict[str, Any]) -> bool:
        """
        Update university record with additional data extracted from program pages.
        Only updates fields that are currently empty/None in the existing record.

        Args:
            university_id: The university ID to update
            extracted_data: Dictionary with extracted university data

        Returns:
            bool: True if updated successfully
        """
        try:
            with mongo_session() as conn:
                # Get existing university data
                existing = conn.universities_collection.find_one({"university_id": university_id})
                
                if not existing:
                    logger.warning(f"University not found for update: {university_id}")
                    return False

                # Build update dict - only update fields that are empty/None/default
                update_fields = {}
                
                # Define fields that can be enriched from program scraping
                enrichable_fields = [
                    "description", "motto", "website", "admissions_url", "email", "phone",
                    "address", "state_province", "latitude", "longitude", "campus_type",
                    "founding_year", "total_students", "international_students", "faculty_count",
                    "student_faculty_ratio", "endowment_usd", "average_tuition_domestic",
                    "average_tuition_international", "qs_world_ranking", "the_world_ranking",
                    "us_news_ranking", "arwu_ranking", "type", "tier", "research_intensity",
                    "libraries_count", "logo_url", "mascot"
                ]
                
                # List fields that should be merged (appended) rather than replaced
                list_fields = [
                    "alternate_names", "research_centers", "sports_facilities", "housing_options",
                    "accreditations", "memberships", "student_organizations", "support_services",
                    "international_support", "colors"
                ]
                
                # Dict fields that should be merged
                dict_fields = ["subject_rankings", "social_media"]

                for field in enrichable_fields:
                    if field in extracted_data and extracted_data[field] is not None:
                        # Check if existing field is empty/None/default
                        existing_value = existing.get(field)
                        if existing_value is None or existing_value == "" or existing_value == 0:
                            update_fields[field] = extracted_data[field]

                # Handle list fields - merge unique values
                for field in list_fields:
                    if field in extracted_data and extracted_data[field]:
                        existing_list = existing.get(field, []) or []
                        new_items = extracted_data[field]
                        if isinstance(new_items, str):
                            new_items = [new_items]
                        # Merge unique values
                        merged = list(set(existing_list + new_items))
                        if merged != existing_list:
                            update_fields[field] = merged

                # Handle dict fields - merge keys
                for field in dict_fields:
                    if field in extracted_data and extracted_data[field]:
                        existing_dict = existing.get(field, {}) or {}
                        new_dict = extracted_data[field]
                        # Merge, preferring new values for existing keys
                        merged = {**existing_dict, **new_dict}
                        if merged != existing_dict:
                            update_fields[field] = merged

                if not update_fields:
                    logger.debug(f"No new data to update for university: {university_id}")
                    return True  # Nothing to update, but not a failure

                # Add timestamp
                update_fields["updated_at"] = datetime.utcnow()

                # Perform update
                result = conn.universities_collection.update_one(
                    {"university_id": university_id},
                    {"$set": update_fields}
                )

                if result.modified_count > 0:
                    logger.info(f"Updated university {university_id} with {len(update_fields)} fields")
                    return True
                else:
                    logger.debug(f"No changes made to university {university_id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to update university {university_id}: {e}")
            return False

    def enrich_university_from_aggregated_data(self, university_name: str, aggregated_data: Dict[str, Any]) -> bool:
        """
        Enrich university record with aggregated data from multiple program pages.

        Args:
            university_name: Name of the university
            aggregated_data: Aggregated data extracted from program pages

        Returns:
            bool: True if enrichment was successful
        """
        from models.university import generate_university_id
        
        university_id = generate_university_id(university_name)
        return self.update_university_from_programs(university_id, aggregated_data)
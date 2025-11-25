"""Repository pattern implementation for data access."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .mongodb import get_mongo_connection, mongo_session
from ..models.university import UniversityProgram
from ..core.exceptions import DuplicateDataError, QueryError

logger = logging.getLogger(__name__)


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

        Args:
            programs: List of UniversityProgram instances

        Returns:
            Dict with counts of inserted, updated, and failed operations
        """
        results = {"inserted": 0, "updated": 0, "failed": 0}

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

    def clear_all(self) -> bool:
        """
        Clear all programs from the database (use with caution).

        Returns:
            bool: True if cleared successfully
        """
        try:
            with mongo_session() as conn:
                result = conn.collection.delete_many({})
                success = result.acknowledged
                if success:
                    logger.warning(f"Cleared {result.deleted_count} programs from database")
                return success
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
            return False
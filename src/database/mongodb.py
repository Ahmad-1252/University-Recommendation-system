"""MongoDB connection and operations for the University Recommendation System."""

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional, Any
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, DuplicateKeyError, OperationFailure

from core.config import get_settings
from core.exceptions import ConnectionError, DuplicateDataError, QueryError
from models.university import UniversityProgram

logger = logging.getLogger(__name__)


class MongoDBConnection:
    """MongoDB connection manager with proper error handling and connection pooling."""

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[MongoClient] = None
        self._database: Optional[Database] = None
        self._collection: Optional[Collection] = None

    @property
    def client(self) -> MongoClient:
        """Get MongoDB client, connecting if necessary."""
        if self._client is None:
            self._connect()
        return self._client

    @property
    def database(self) -> Database:
        """Get MongoDB database."""
        if self._database is None:
            self._database = self.client[self.settings.database.database_name]
        return self._database

    @property
    def collection(self) -> Collection:
        """Get MongoDB collection for programs."""
        if self._collection is None:
            self._collection = self.database[self.settings.database.collection_name]
            self._ensure_program_indexes()
        return self._collection

    @property
    def universities_collection(self) -> Collection:
        """Get MongoDB collection for universities."""
        if not hasattr(self, '_universities_collection') or self._universities_collection is None:
            self._universities_collection = self.database["universities"]
            self._ensure_university_indexes()
        return self._universities_collection

    def _connect(self) -> None:
        """Establish connection to MongoDB."""
        try:
            self._client = MongoClient(
                self.settings.database.connection_string,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=10,
                minPoolSize=2
            )
            # Test the connection
            self._client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise ConnectionError(f"MongoDB connection failed: {e}") from e

    def _ensure_program_indexes(self) -> None:
        """Create necessary database indexes for programs collection."""
        try:
            # Unique index on source_url to prevent duplicates
            self._collection.create_index(
                [("source_url", ASCENDING)],
                unique=True,
                name="unique_source_url"
            )

            # Index on university_name for filtering
            self._collection.create_index(
                [("university_name", ASCENDING)],
                name="university_name_index"
            )

            # Index on country for geographical filtering
            self._collection.create_index(
                [("country", ASCENDING)],
                name="country_index"
            )

            # Index on degree_type for program type filtering
            self._collection.create_index(
                [("degree_type", ASCENDING)],
                name="degree_type_index"
            )

            # Compound index for ranking queries
            self._collection.create_index(
                [("rankings.qs_world_ranking", ASCENDING)],
                name="qs_ranking_index"
            )

            # Index on last_updated for freshness queries
            self._collection.create_index(
                [("last_updated", DESCENDING)],
                name="last_updated_index"
            )

            # Index on confidence_score for quality filtering
            self._collection.create_index(
                [("confidence_score", DESCENDING)],
                name="confidence_score_index"
            )

            logger.info("Database indexes created successfully")
        except OperationFailure as e:
            logger.warning(f"Failed to create program indexes: {e}")

    def _ensure_university_indexes(self) -> None:
        """Create necessary database indexes for universities collection."""
        try:
            universities_collection = self._universities_collection

            # Unique index on university_id
            universities_collection.create_index(
                [("university_id", ASCENDING)],
                unique=True,
                name="unique_university_id"
            )

            # Index on name for searching
            universities_collection.create_index(
                [("name", ASCENDING)],
                name="university_name_index"
            )

            # Index on country for geographical filtering
            universities_collection.create_index(
                [("country", ASCENDING)],
                name="university_country_index"
            )

            # Index on QS ranking for ranking queries
            universities_collection.create_index(
                [("qs_world_ranking", ASCENDING)],
                name="qs_ranking_index"
            )

            # Index on THE ranking
            universities_collection.create_index(
                [("the_world_ranking", ASCENDING)],
                name="the_ranking_index"
            )

            # Index on US News ranking
            universities_collection.create_index(
                [("us_news_ranking", ASCENDING)],
                name="us_news_ranking_index"
            )

            # Index on tier for filtering
            universities_collection.create_index(
                [("tier", ASCENDING)],
                name="tier_index"
            )

            # Index on type (public/private)
            universities_collection.create_index(
                [("type", ASCENDING)],
                name="type_index"
            )

            # Index on last_updated for freshness queries
            universities_collection.create_index(
                [("updated_at", DESCENDING)],
                name="university_updated_index"
            )

            # Compound index for country + ranking queries
            universities_collection.create_index(
                [("country", ASCENDING), ("qs_world_ranking", ASCENDING)],
                name="country_qs_ranking_index"
            )

            logger.info("University database indexes created successfully")
        except OperationFailure as e:
            logger.warning(f"Failed to create university indexes: {e}")

    def close(self) -> None:
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
            self._collection = None
            if hasattr(self, '_universities_collection'):
                self._universities_collection = None
            logger.info("MongoDB connection closed")

    def health_check(self) -> bool:
        """Check if the database connection is healthy."""
        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            return False


# Global connection instance
_mongo_connection: Optional[MongoDBConnection] = None


def get_mongo_connection() -> MongoDBConnection:
    """Get global MongoDB connection instance."""
    global _mongo_connection
    if _mongo_connection is None:
        _mongo_connection = MongoDBConnection()
    return _mongo_connection


@contextmanager
def mongo_session():
    """Context manager for MongoDB operations."""
    connection = get_mongo_connection()
    try:
        yield connection
    except Exception as e:
        logger.error(f"MongoDB operation failed: {e}")
        raise
    finally:
        # Connection is kept alive for reuse
        pass
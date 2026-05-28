"""Unit tests for database layer."""
from unittest.mock import MagicMock, patch

import pytest

from src.database.mongodb import MongoDBConnection
from src.database.repositories import ProgramRepository
from src.models.university import DegreeType, UniversityProgram


class TestMongoDBConnection:
    """Test MongoDB connection management."""

    @patch("src.database.mongodb.MongoClient")
    @patch("src.database.mongodb.get_settings")
    def test_connection_initialization(self, mock_settings, mock_client):
        """Test MongoDB connection initialization."""
        mock_db_instance = MagicMock()
        mock_client.return_value = mock_db_instance
        mock_db_instance.admin.command.return_value = {"ok": 1}

        mock_settings.return_value.database.connection_string = "mongodb://test:27017"
        mock_settings.return_value.database.database_name = "test_db"
        mock_settings.return_value.database.collection_name = "test_collection"

        connection = MongoDBConnection()
        connection._connect()  # Should not raise an exception

    @patch("src.database.mongodb.MongoClient")
    @patch("src.database.mongodb.get_settings")
    def test_connection_health_check_success(self, mock_settings, mock_client):
        """Test successful health check."""
        mock_db_instance = MagicMock()
        mock_client.return_value = mock_db_instance
        mock_db_instance.admin.command.return_value = {"ok": 1}

        mock_settings.return_value.database.connection_string = "mongodb://test:27017"
        mock_settings.return_value.database.database_name = "test_db"
        mock_settings.return_value.database.collection_name = "test_collection"

        connection = MongoDBConnection()
        result = connection.health_check()
        assert result is True

    @patch("src.database.mongodb.MongoClient")
    @patch("src.database.mongodb.get_settings")
    def test_connection_health_check_failure(self, mock_settings, mock_client):
        """Test failed health check."""
        mock_client.side_effect = Exception("Connection failed")

        mock_settings.return_value.database.connection_string = "mongodb://test:27017"
        mock_settings.return_value.database.database_name = "test_db"
        mock_settings.return_value.database.collection_name = "test_collection"

        connection = MongoDBConnection()
        result = connection.health_check()
        assert result is False

    @patch("src.database.mongodb.MongoClient")
    @patch("src.database.mongodb.get_settings")
    def test_close_connection(self, mock_settings, mock_client):
        """Test connection closing."""
        mock_db_instance = MagicMock()
        mock_client.return_value = mock_db_instance

        mock_settings.return_value.database.connection_string = "mongodb://test:27017"
        mock_settings.return_value.database.database_name = "test_db"
        mock_settings.return_value.database.collection_name = "test_collection"

        connection = MongoDBConnection()
        connection.close()  # Should not raise an exception


class TestProgramRepository:
    """Test program repository operations."""

    @pytest.fixture
    def sample_program(self):
        """Create sample university program."""
        return UniversityProgram(
            university_name="Test University",
            program_name="Test Program",
            degree_type=DegreeType.MASTER_OF_SCIENCE,
            country="Test Country",
            city="Test City",
            source_url="https://test.edu",
            confidence_score=0.85,
        )

    @pytest.fixture
    def mock_connection(self):
        """Create mock database connection."""
        connection = MagicMock()
        connection.collection = MagicMock()
        return connection

    @pytest.fixture
    def repository(self, mock_connection):
        """Create program repository."""
        with patch("src.database.repositories.mongo_session") as mock_session:
            mock_session.return_value.__enter__.return_value = mock_connection
            mock_session.return_value.__exit__.return_value = None
            return ProgramRepository()

    def test_save_program(self, mock_connection, sample_program):
        """Test saving a program."""
        mock_result = MagicMock()
        mock_result.acknowledged = True
        mock_result.modified_count = 0
        mock_connection.collection.replace_one.return_value = mock_result

        with patch("src.database.repositories.mongo_session") as mock_session:
            mock_session.return_value.__enter__.return_value = mock_connection
            mock_session.return_value.__exit__.return_value = None
            repository = ProgramRepository()
            result = repository.save(sample_program)

        assert result is True

    def test_get_by_url(self, mock_connection, sample_program):
        """Test getting program by URL."""
        mock_connection.collection.find_one.return_value = sample_program.model_dump()

        with patch("src.database.repositories.mongo_session") as mock_session:
            mock_session.return_value.__enter__.return_value = mock_connection
            mock_session.return_value.__exit__.return_value = None
            repository = ProgramRepository()
            result = repository.get_by_url("https://test.edu")

        assert result is not None
        assert result.university_name == "Test University"

    def test_get_by_university(self, mock_connection, sample_program):
        """Test getting programs by university."""
        mock_cursor = MagicMock()
        mock_cursor.__iter__.return_value = [sample_program.model_dump()]
        mock_connection.collection.find.return_value = mock_cursor

        with patch("src.database.repositories.mongo_session") as mock_session:
            mock_session.return_value.__enter__.return_value = mock_connection
            mock_session.return_value.__exit__.return_value = None
            repository = ProgramRepository()
            results = repository.get_by_university("Test University")

        assert len(results) == 1
        assert results[0].university_name == "Test University"

    def test_search_programs(self, mock_connection, sample_program):
        """Test searching programs."""
        mock_cursor = MagicMock()
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__.return_value = [sample_program.model_dump()]
        mock_connection.collection.find.return_value = mock_cursor

        with patch("src.database.repositories.mongo_session") as mock_session:
            mock_session.return_value.__enter__.return_value = mock_connection
            mock_session.return_value.__exit__.return_value = None
            repository = ProgramRepository()
            results = repository.search(country="Test Country", limit=10)

        assert len(results) == 1
        assert results[0].university_name == "Test University"

    def test_get_all_programs(self, mock_connection, sample_program):
        """Test getting all programs."""
        mock_cursor = MagicMock()
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__.return_value = [sample_program.model_dump()]
        mock_connection.collection.find.return_value = mock_cursor

        with patch("src.database.repositories.mongo_session") as mock_session:
            mock_session.return_value.__enter__.return_value = mock_connection
            mock_session.return_value.__exit__.return_value = None
            repository = ProgramRepository()
            results = repository.get_all_programs(limit=100)

        assert len(results) == 1

    def test_delete_by_url(self, mock_connection):
        """Test deleting a program."""
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_connection.collection.delete_one.return_value = mock_result

        with patch("src.database.repositories.mongo_session") as mock_session:
            mock_session.return_value.__enter__.return_value = mock_connection
            mock_session.return_value.__exit__.return_value = None
            repository = ProgramRepository()
            result = repository.delete_by_url("https://test.edu")

        assert result is True

    def test_get_statistics(self, mock_connection):
        """Test getting database statistics."""
        # Mock count_documents
        mock_connection.collection.count_documents.return_value = 42

        # Mock aggregate results - need to return cursors
        mock_countries_cursor = MagicMock()
        mock_countries_cursor.__iter__.return_value = [{"_id": "USA", "count": 10}]

        mock_degree_types_cursor = MagicMock()
        mock_degree_types_cursor.__iter__.return_value = [{"_id": "MS", "count": 20}]

        mock_stats_cursor = MagicMock()
        mock_stats_cursor.next.return_value = {
            "avg_completeness": 0.8,
            "avg_confidence": 0.9,
            "min_tuition": 10000,
            "max_tuition": 50000,
            "avg_tuition": 30000,
        }

        mock_connection.collection.aggregate.side_effect = [
            mock_countries_cursor,  # countries
            mock_degree_types_cursor,  # degree_types
            mock_stats_cursor,  # stats
        ]

        with patch("src.database.repositories.mongo_session") as mock_session:
            mock_session.return_value.__enter__.return_value = mock_connection
            mock_session.return_value.__exit__.return_value = None
            repository = ProgramRepository()
            stats = repository.get_statistics()

        assert stats["total_programs"] == 42
        assert len(stats["countries"]) == 1
        assert stats["avg_completeness"] == 0.8

    def test_clear_all(self, mock_connection):
        """Test clearing all programs."""
        mock_result = MagicMock()
        mock_result.acknowledged = True
        mock_result.deleted_count = 10
        mock_connection.collection.delete_many.return_value = mock_result

        with patch("src.database.repositories.mongo_session") as mock_session:
            mock_session.return_value.__enter__.return_value = mock_connection
            mock_session.return_value.__exit__.return_value = None
            repository = ProgramRepository()
            result = repository.clear_all()

        assert result is True

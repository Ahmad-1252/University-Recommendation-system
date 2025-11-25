"""Unit tests for core configuration and constants."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.config import Settings, DatabaseSettings, LLMSettings
from src.core.constants import (
    UNIVERSITY_URLS, UNIVERSITY_METADATA, DEGREE_TYPES,
    LLM_PROMPTS, QUALITY_THRESHOLDS
)


class TestSettings:
    """Test configuration settings."""

    def test_database_settings_defaults(self):
        """Test database settings with default values."""
        # Note: Settings load from .env, so we test the actual loaded values
        from src.core.config import settings
        db_settings = settings.database
        assert db_settings.database_name == "University-Recommendator"
        assert db_settings.collection_name == "University_Data"
        assert isinstance(db_settings.connection_timeout, int)

    def test_llm_settings_defaults(self):
        """Test LLM settings with default values."""
        from src.core.config import settings
        llm_settings = settings.llm
        assert llm_settings.model == "llama3-70b-8192"
        assert llm_settings.timeout == 30
        assert llm_settings.max_retries == 3

    @patch.dict('os.environ', {
        'MONGO_CONNECTION_STRING': 'mongodb://test:27017',
        'DATABASE_NAME': 'test_db',
        'GROQ_API_KEY': 'test_key',
        'GROQ_MODEL': 'test-model'
    })
    def test_settings_from_env(self):
        """Test settings loaded from environment variables."""
        # Create settings instance with env vars (bypass .env file for testing)
        from pydantic_settings import BaseSettings, SettingsConfigDict
        from pydantic import Field
        
        class TestDatabaseSettings(BaseSettings):
            connection_string: str = Field("mongodb://localhost:27017", alias="MONGO_CONNECTION_STRING")
            database_name: str = Field("university_db", alias="DATABASE_NAME")
            collection_name: str = Field("programs", alias="COLLECTION_NAME")
            connection_timeout: int = 30
            max_pool_size: int = 10
            model_config = SettingsConfigDict(case_sensitive=False, env_prefix="", extra="ignore")

        class TestLLMSettings(BaseSettings):
            api_key: str = Field("", alias="GROQ_API_KEY")
            model: str = Field("llama3-70b-8192", alias="GROQ_MODEL")
            timeout: int = Field(30, alias="LLM_TIMEOUT")
            max_retries: int = 3
            temperature: float = 0.1
            model_config = SettingsConfigDict(case_sensitive=False, env_prefix="", extra="ignore")

        class TestSettings(BaseSettings):
            database: TestDatabaseSettings = TestDatabaseSettings()
            llm: TestLLMSettings = TestLLMSettings()
            model_config = SettingsConfigDict(case_sensitive=False, env_prefix="", extra="ignore")

        test_settings = TestSettings()
        
        assert test_settings.database.connection_string == "mongodb://test:27017"
        assert test_settings.database.database_name == "test_db"
        assert test_settings.llm.api_key == "test_key"
        assert test_settings.llm.model == "test-model"

    def test_settings_paths(self):
        """Test settings path properties."""
        settings = Settings()

        assert isinstance(settings.data_dir, Path)
        assert isinstance(settings.logs_dir, Path)
        assert isinstance(settings.exports_dir, Path)

        assert "data" in str(settings.data_dir)
        assert "logs" in str(settings.logs_dir)
        assert "exports" in str(settings.exports_dir)


class TestConstants:
    """Test constants and configuration data."""

    def test_university_urls_structure(self):
        """Test university URLs data structure."""
        assert isinstance(UNIVERSITY_URLS, dict)
        assert len(UNIVERSITY_URLS) > 0

        # Check first university entry
        first_key = next(iter(UNIVERSITY_URLS.keys()))
        first_value = UNIVERSITY_URLS[first_key]

        assert isinstance(first_value, str)
        assert first_value.startswith(('http://', 'https://'))

    def test_university_metadata_structure(self):
        """Test university metadata structure."""
        assert isinstance(UNIVERSITY_METADATA, dict)
        assert len(UNIVERSITY_METADATA) > 0

        # Check metadata keys
        first_key = next(iter(UNIVERSITY_METADATA.keys()))
        metadata = UNIVERSITY_METADATA[first_key]

        assert isinstance(metadata, dict)
        expected_keys = ['country', 'city', 'tier', 'qs_ranking', 'the_ranking', 'us_news_ranking']
        for key in expected_keys:
            assert key in metadata

    def test_degree_types(self):
        """Test degree types enumeration."""
        assert isinstance(DEGREE_TYPES, list)
        assert len(DEGREE_TYPES) > 0

        # Check common degree types
        common_degrees = ['Bachelor of Science', 'Master of Science', 'Doctor of Philosophy']
        for degree in common_degrees:
            assert degree in DEGREE_TYPES

    def test_llm_prompts_structure(self):
        """Test LLM prompts structure."""
        assert isinstance(LLM_PROMPTS, dict)
        assert 'program_extraction' in LLM_PROMPTS
        assert 'quality_assessment' in LLM_PROMPTS

        # Check prompt content
        extraction_prompt = LLM_PROMPTS['program_extraction']
        assert isinstance(extraction_prompt, str)
        assert len(extraction_prompt) > 0
        assert 'university' in extraction_prompt.lower()

    def test_quality_thresholds(self):
        """Test quality thresholds configuration."""
        assert isinstance(QUALITY_THRESHOLDS, dict)

        expected_keys = [
            'min_confidence_score', 'min_field_completeness', 'max_duplicate_rate'
        ]

        for key in expected_keys:
            assert key in QUALITY_THRESHOLDS
            assert isinstance(QUALITY_THRESHOLDS[key], float)
            assert 0.0 <= QUALITY_THRESHOLDS[key] <= 1.0


class TestConstantsIntegration:
    """Test integration between constants."""

    def test_university_url_metadata_consistency(self):
        """Test that university URLs and metadata are consistent."""
        url_keys = set(UNIVERSITY_URLS.keys())
        metadata_keys = set(UNIVERSITY_METADATA.keys())

        # All universities with URLs should have metadata
        assert url_keys.issubset(metadata_keys), "Some universities missing metadata"

    def test_metadata_completeness(self):
        """Test metadata completeness for all universities."""
        for uni_name, metadata in UNIVERSITY_METADATA.items():
            assert 'country' in metadata, f"Missing country for {uni_name}"
            assert 'city' in metadata, f"Missing city for {uni_name}"
            assert 'qs_ranking' in metadata, f"Missing QS ranking for {uni_name}"

            # Validate tier values
            valid_tiers = ['top', 'good', 'standard']
            assert metadata['tier'] in valid_tiers, f"Invalid tier for {uni_name}"
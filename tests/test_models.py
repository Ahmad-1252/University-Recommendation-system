"""Unit tests for university data models."""
import pytest
from datetime import datetime
from typing import List, Optional

from src.models.university import (
    UniversityProgram, DegreeType, LanguageProficiency,
    TuitionFees, Rankings, UniversityTier
)


class TestDegreeType:
    """Test DegreeType enum."""

    def test_degree_type_values(self):
        """Test degree type enum values."""
        assert DegreeType.BACHELOR_OF_SCIENCE.value == "Bachelor of Science"
        assert DegreeType.MASTER_OF_SCIENCE.value == "Master of Science"
        assert DegreeType.DOCTOR_OF_PHILOSOPHY.value == "Doctor of Philosophy"

    def test_degree_type_list(self):
        """Test degree type list contains all values."""
        degree_values = [dt.value for dt in DegreeType]
        assert "Bachelor of Science" in degree_values
        assert "Master of Science" in degree_values
        assert "Doctor of Philosophy" in degree_values


class TestLanguageProficiency:
    """Test LanguageProficiency model."""

    def test_valid_language_proficiency(self):
        """Test valid language proficiency creation."""
        lang = LanguageProficiency(
            toefl_min=100,
            ielts_min=7.0,
            gre_required=False
        )
        assert lang.toefl_min == 100
        assert lang.ielts_min == 7.0
        assert lang.gre_required is False

    def test_language_proficiency_defaults(self):
        """Test language proficiency with defaults."""
        lang = LanguageProficiency()
        assert lang.toefl_min is None
        assert lang.ielts_min is None
        assert lang.gre_required is None

    def test_language_proficiency_validation(self):
        """Test language proficiency validation."""
        # Valid TOEFL range
        lang = LanguageProficiency(toefl_min=120)
        assert lang.toefl_min == 120

        # Valid IELTS range
        lang = LanguageProficiency(ielts_min=6.5)
        assert lang.ielts_min == 6.5


class TestTuitionFees:
    """Test TuitionFees model."""

    def test_valid_tuition_fees(self):
        """Test valid tuition fees creation."""
        fees = TuitionFees(
            domestic_per_year=50000,
            international_per_year=60000,
            currency="USD"
        )
        assert fees.domestic_per_year == 50000
        assert fees.international_per_year == 60000
        assert fees.currency == "USD"

    def test_tuition_fees_defaults(self):
        """Test tuition fees with defaults."""
        fees = TuitionFees()
        assert fees.domestic_per_year is None
        assert fees.international_per_year is None
        assert fees.currency == "USD"

    def test_tuition_fees_validation(self):
        """Test tuition fees validation."""
        # Valid positive amounts
        fees = TuitionFees(domestic_per_year=1000, international_per_year=2000)
        assert fees.domestic_per_year == 1000
        assert fees.international_per_year == 2000


class TestRankings:
    """Test Rankings model."""

    def test_valid_rankings(self):
        """Test valid rankings creation."""
        rankings = Rankings(
            qs_world_ranking=10,
            the_world_ranking=15,
            us_news_ranking=12
        )
        assert rankings.qs_world_ranking == 10
        assert rankings.the_world_ranking == 15
        assert rankings.us_news_ranking == 12

    def test_rankings_defaults(self):
        """Test rankings with defaults."""
        rankings = Rankings()
        assert rankings.qs_world_ranking is None
        assert rankings.the_world_ranking is None
        assert rankings.us_news_ranking is None

    def test_rankings_validation(self):
        """Test rankings validation."""
        # Valid positive rankings
        rankings = Rankings(qs_world_ranking=1, the_world_ranking=2)
        assert rankings.qs_world_ranking == 1
        assert rankings.the_world_ranking == 2


class TestUniversityProgram:
    """Test UniversityProgram model."""

    def test_minimal_university_program(self):
        """Test minimal university program creation."""
        program = UniversityProgram(
            university_name="Test University",
            program_name="Test Program",
            degree_type=DegreeType.MASTER_OF_SCIENCE,
            country="Test Country",
            city="Test City",
            source_url="https://test.edu"
        )

        assert program.university_name == "Test University"
        assert program.program_name == "Test Program"
        assert program.degree_type == DegreeType.MASTER_OF_SCIENCE
        assert program.country == "Test Country"
        assert program.city == "Test City"
        assert str(program.source_url) == "https://test.edu/"

    def test_complete_university_program(self):
        """Test complete university program creation."""
        program = UniversityProgram(
            university_name="Stanford University",
            program_name="MS in Computer Science",
            degree_type=DegreeType.MASTER_OF_SCIENCE,
            country="United States",
            city="Stanford, CA",

            # Academic requirements
            gpa_requirement_min=3.5,
            language_requirements=LanguageProficiency(
                toefl_min=100,
                ielts_min=7.0,
                gre_required=False
            ),

            # Financial information
            tuition_fees=TuitionFees(
                domestic_per_year=65000,
                international_per_year=65000,
                currency="USD"
            ),

            # Program details
            duration_years=2.0,
            program_description="Comprehensive CS program",
            specializations=["AI", "Systems", "Theory"],
            research_interests=["Machine Learning", "Computer Vision"],

            # Rankings
            rankings=Rankings(
                qs_world_ranking=3,
                the_world_ranking=4,
                us_news_ranking=3
            ),

            # Metadata
            source_url="https://cs.stanford.edu/",
            confidence_score=0.92,
            data_completeness=0.85
        )

        assert program.university_name == "Stanford University"
        assert program.gpa_requirement_min == 3.5
        assert program.language_requirements.toefl_min == 100
        assert program.tuition_fees.domestic_per_year == 65000
        assert program.duration_years == 2.0
        assert "AI" in program.specializations
        assert program.rankings.qs_world_ranking == 3
        assert program.confidence_score == 0.92

    def test_university_program_validation(self):
        """Test university program validation."""
        # Valid GPA range
        program = UniversityProgram(
            university_name="Test",
            program_name="Test",
            degree_type=DegreeType.BACHELOR_OF_SCIENCE,
            country="Test",
            city="Test",
            source_url="https://test.edu",
            gpa_requirement_min=3.7
        )
        assert program.gpa_requirement_min == 3.7

        # Valid duration
        program = UniversityProgram(
            university_name="Test",
            program_name="Test",
            degree_type=DegreeType.BACHELOR_OF_SCIENCE,
            country="Test",
            city="Test",
            source_url="https://test.edu",
            duration_years=4.0
        )
        assert program.duration_years == 4.0

    def test_university_program_invalid_data(self):
        """Test university program with invalid data."""
        # Invalid GPA
        with pytest.raises(ValueError):
            UniversityProgram(
                university_name="Test",
                program_name="Test",
                degree_type=DegreeType.BACHELOR_OF_SCIENCE,
                country="Test",
                city="Test",
                source_url="https://test.edu",
                gpa_requirement_min=5.5  # Invalid GPA > 4.0
            )

        # Invalid duration
        with pytest.raises(ValueError):
            UniversityProgram(
                university_name="Test",
                program_name="Test",
                degree_type=DegreeType.BACHELOR_OF_SCIENCE,
                country="Test",
                city="Test",
                source_url="https://test.edu",
                duration_years=10.0  # Invalid duration > 7 years
            )

    def test_university_program_serialization(self):
        """Test university program JSON serialization."""
        program = UniversityProgram(
            university_name="Test University",
            program_name="Test Program",
            degree_type=DegreeType.MASTER_OF_SCIENCE,
            country="Test Country",
            city="Test City",
            source_url="https://test.edu",
            confidence_score=0.85
        )

        # Test JSON serialization
        json_data = program.model_dump()
        assert json_data['university_name'] == "Test University"
        assert json_data['degree_type'] == "Master of Science"
        assert json_data['confidence_score'] == 0.85

        # Test JSON deserialization
        program_copy = UniversityProgram.model_validate(json_data)
        assert program_copy.university_name == program.university_name
        assert program_copy.confidence_score == program.confidence_score

    def test_university_program_computed_fields(self):
        """Test computed fields in university program."""
        program = UniversityProgram(
            university_name="Test University",
            program_name="Test Program",
            degree_type=DegreeType.MASTER_OF_SCIENCE,
            country="Test Country",
            city="Test City",
            source_url="https://test.edu"
        )

        # Test that last_updated is set
        assert isinstance(program.last_updated, datetime)

        # Test data completeness calculation (would need actual implementation)
        # This is a placeholder for when the computed field is implemented
        pass


class TestUniversityTier:
    """Test UniversityTier enum."""

    def test_university_tier_values(self):
        """Test university tier enum values."""
        assert UniversityTier.TOP.value == "top"
        assert UniversityTier.GOOD.value == "good"
        assert UniversityTier.STANDARD.value == "standard"
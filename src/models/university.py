"""Data models for the University Recommendation System."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator
from enum import Enum, IntEnum


class DegreeType(str, Enum):
    """Enumeration of degree types."""
    BACHELOR_OF_SCIENCE = "Bachelor of Science"
    BACHELOR_OF_ARTS = "Bachelor of Arts"
    MASTER_OF_SCIENCE = "Master of Science"
    MASTER_OF_ARTS = "Master of Arts"
    MASTER_OF_ENGINEERING = "Master of Engineering"
    DOCTOR_OF_PHILOSOPHY = "Doctor of Philosophy"
    DOCTOR_OF_SCIENCE = "Doctor of Science"


class UniversityTier(str, Enum):
    """Enumeration of university tiers based on rankings and reputation."""
    TOP = "top"
    GOOD = "good"
    STANDARD = "standard"


class LanguageProficiency(BaseModel):
    """Language proficiency requirements."""
    toefl_min: Optional[int] = Field(None, ge=0, le=120, description="Minimum TOEFL iBT score")
    ielts_min: Optional[float] = Field(None, ge=0.0, le=9.0, description="Minimum IELTS band score")
    pte_min: Optional[int] = Field(None, ge=10, le=90, description="Minimum PTE score")
    duolingo_min: Optional[int] = Field(None, ge=10, le=160, description="Minimum Duolingo score")
    gre_required: Optional[bool] = Field(None, description="Whether GRE is required")


class TuitionFees(BaseModel):
    """Tuition fee information."""
    domestic_per_year: Optional[int] = Field(None, ge=0, description="Domestic tuition per year in USD")
    international_per_year: Optional[int] = Field(None, ge=0, description="International tuition per year in USD")
    currency: str = Field("USD", description="Currency code for fees")
    additional_fees: Optional[Dict[str, int]] = Field(None, description="Additional fees (application, etc.)")


class ApplicationDeadlines(BaseModel):
    """Application deadline information."""
    fall_deadline: Optional[str] = Field(None, description="Fall intake deadline (YYYY-MM-DD)")
    spring_deadline: Optional[str] = Field(None, description="Spring intake deadline (YYYY-MM-DD)")
    summer_deadline: Optional[str] = Field(None, description="Summer intake deadline (YYYY-MM-DD)")
    rolling_admission: bool = Field(False, description="Whether university has rolling admission")


class Rankings(BaseModel):
    """University ranking information."""
    qs_world_ranking: Optional[int] = Field(None, ge=1, description="QS World University Rankings")
    the_world_ranking: Optional[int] = Field(None, ge=1, description="Times Higher Education World Rankings")
    us_news_ranking: Optional[int] = Field(None, ge=1, description="US News Global Universities Rankings")
    subject_ranking_cs: Optional[int] = Field(None, ge=1, description="Computer Science subject ranking")


class UniversityProgram(BaseModel):
    """Main data model for university programs."""

    # Core identifying information
    university_name: str = Field(..., description="Full name of the university")
    program_name: str = Field(..., description="Complete name of the academic program")
    degree_type: DegreeType = Field(..., description="Type of degree offered")

    # Location information
    country: str = Field(..., description="Country where university is located")
    city: str = Field(..., description="City where university is located")

    # Academic requirements
    gpa_requirement_min: Optional[float] = Field(None, ge=0.0, le=4.0, description="Minimum GPA requirement (4.0 scale)")
    language_requirements: LanguageProficiency = Field(default_factory=LanguageProficiency, description="Language proficiency requirements")
    prerequisites: List[str] = Field(default_factory=list, description="List of prerequisite courses or degrees")

    # Program details
    duration_years: Optional[float] = Field(None, gt=0, le=7, description="Program duration in years")
    program_description: str = Field("", description="Detailed program description")
    specializations: List[str] = Field(default_factory=list, description="Available specializations or tracks")
    faculty_research_interests: List[str] = Field(default_factory=list, description="Key research areas and faculty interests")

    # Financial information
    tuition_fees: TuitionFees = Field(default_factory=TuitionFees, description="Tuition fee information")
    scholarships_available: List[str] = Field(default_factory=list, description="Available scholarships")
    cost_of_living_estimate: Optional[int] = Field(None, ge=0, description="Estimated annual cost of living in USD")

    # Application information
    application_deadlines: ApplicationDeadlines = Field(default_factory=ApplicationDeadlines, description="Application deadline information")
    application_fee: Optional[int] = Field(None, ge=0, description="Application fee in USD")

    # Rankings and reputation
    rankings: Rankings = Field(default_factory=Rankings, description="University ranking information")

    # Additional information
    career_outcomes: List[str] = Field(default_factory=list, description="Career outcomes and job placements")
    research_opportunities: List[str] = Field(default_factory=list, description="Research opportunities and labs")
    campus_facilities: List[str] = Field(default_factory=list, description="Campus facilities and resources")
    student_reviews_rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="Average student rating (0-5 scale)")

    # Metadata
    source_url: HttpUrl = Field(..., description="URL where data was scraped from")
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score for data accuracy")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last time data was updated")
    data_completeness: float = Field(0.0, ge=0.0, le=1.0, description="Percentage of fields with data")

    @field_validator("university_name")
    @classmethod
    def validate_university_name(cls, v):
        """Validate university name is not empty and reasonable length."""
        if not v or not v.strip():
            raise ValueError("University name cannot be empty")
        if len(v) > 200:
            raise ValueError("University name too long")
        return v.strip()

    @field_validator("program_name")
    @classmethod
    def validate_program_name(cls, v):
        """Validate program name is not empty and reasonable length."""
        if not v or not v.strip():
            raise ValueError("Program name cannot be empty")
        if len(v) > 300:
            raise ValueError("Program name too long")
        return v.strip()

    @field_validator("gpa_requirement_min")
    @classmethod
    def validate_gpa(cls, v):
        """Validate GPA is within reasonable range."""
        if v is not None and (v < 0 or v > 4.0):
            raise ValueError("GPA must be between 0.0 and 4.0")
        return v

    @model_validator(mode='after')
    def calculate_completeness(self):
        """Calculate data completeness score."""
        total_fields = 0
        filled_fields = 0

        # Define fields to check for completeness
        fields_to_check = [
            "program_description", "duration_years", "tuition_fees",
            "application_deadlines", "gpa_requirement_min", "prerequisites",
            "specializations", "faculty_research_interests"
        ]

        for field in fields_to_check:
            total_fields += 1
            value = getattr(self, field, None)
            if value is not None and value != "" and value != []:
                if isinstance(value, (list, dict)) and len(value) == 0:
                    continue
                filled_fields += 1

        self.data_completeness = filled_fields / total_fields if total_fields > 0 else 0.0
        return self

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str
        }


class ScrapingConfig(BaseModel):
    """Configuration for scraping operations."""
    urls: List[HttpUrl] = Field(..., description="List of URLs to scrape")
    max_concurrent: int = Field(5, gt=0, description="Maximum concurrent scraping tasks")
    timeout: int = Field(30, gt=0, description="Timeout for each scraping operation")
    retry_attempts: int = Field(3, ge=0, description="Number of retry attempts")


class AnalysisResult(BaseModel):
    """Result of data analysis operations."""
    total_programs: int = Field(..., description="Total number of programs analyzed")
    average_completeness: float = Field(..., description="Average data completeness score")
    quality_score: float = Field(..., description="Overall data quality score")
    issues_found: List[str] = Field(default_factory=list, description="List of issues identified")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")


class ExportResult(BaseModel):
    """Result of data export operations."""
    format: str = Field(..., description="Export format (csv, json, xlsx)")
    file_path: str = Field(..., description="Path to exported file")
    record_count: int = Field(..., description="Number of records exported")
    export_time: datetime = Field(default_factory=datetime.utcnow, description="Time of export")
    success: bool = Field(True, description="Whether export was successful")
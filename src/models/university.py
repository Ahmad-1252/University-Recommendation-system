"""Data models for the University Recommendation System."""

import hashlib
import re
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


def generate_university_id(name: str) -> str:
    """Generate a unique university ID from the name using MD5 hash.

    Args:
        name: University name to hash

    Returns:
        A 12-character hex string derived from MD5 hash of normalized name
    """
    # Normalize: lowercase, remove special chars, collapse whitespace
    normalized = re.sub(r"[^a-z0-9\s]", "", name.lower().strip())
    normalized = re.sub(r"\s+", " ", normalized)

    # Generate MD5 hash and take first 12 characters
    return hashlib.md5(normalized.encode()).hexdigest()[:12]


class DegreeType(str, Enum):
    """Enumeration of degree types."""

    # Undergraduate
    BACHELOR_OF_SCIENCE = "Bachelor of Science"
    BACHELOR_OF_ARTS = "Bachelor of Arts"
    BACHELOR_OF_ENGINEERING = "Bachelor of Engineering"
    BACHELOR_OF_BUSINESS = "Bachelor of Business Administration"
    BACHELOR_OF_MEDICINE = "Bachelor of Medicine"
    BACHELOR_OF_LAWS = "Bachelor of Laws"
    BACHELOR_OF_EDUCATION = "Bachelor of Education"

    # Masters
    MASTER_OF_SCIENCE = "Master of Science"
    MASTER_OF_ARTS = "Master of Arts"
    MASTER_OF_ENGINEERING = "Master of Engineering"
    MASTER_OF_PHILOSOPHY = "Master of Philosophy"
    MASTER_OF_BUSINESS = "Master of Business Administration"
    MASTER_OF_LAWS = "Master of Laws"
    MASTER_OF_EDUCATION = "Master of Education"
    MASTER_OF_PUBLIC_HEALTH = "Master of Public Health"

    # Doctoral
    DOCTOR_OF_PHILOSOPHY = "Doctor of Philosophy"
    DOCTOR_OF_SCIENCE = "Doctor of Science"
    DOCTOR_OF_MEDICINE = "Doctor of Medicine"
    DOCTOR_OF_EDUCATION = "Doctor of Education"
    DOCTOR_OF_BUSINESS = "Doctor of Business Administration"


class DegreeLevel(str, Enum):
    """Enumeration of degree levels."""

    UNDERGRADUATE = "Undergraduate"
    GRADUATE = "Graduate"
    MASTERS = "Masters"
    PHD = "PhD"


class ProgramCategory(str, Enum):
    """Enumeration of program categories/fields."""

    COMPUTER_SCIENCE = "Computer Science"
    NETWORKING = "Networking"
    BUSINESS = "Business"
    MEDICAL = "Medical"
    EDUCATION = "Education"
    ENGINEERING = "Engineering"
    LAW = "Law"
    ARTS_HUMANITIES = "Arts & Humanities"
    SCIENCES = "Sciences"
    OTHER = "Other"


def normalize_degree_type(value: str) -> str:
    """Normalize degree type string to valid DegreeType value."""
    if not value:
        return "Master of Science"  # Default

    value_lower = value.lower().strip()

    # Map common variations to full names
    degree_map = {
        # Undergraduate
        "bsc": "Bachelor of Science",
        "b.sc": "Bachelor of Science",
        "bs": "Bachelor of Science",
        "b.s.": "Bachelor of Science",
        "bachelor": "Bachelor of Science",
        "bachelor of science": "Bachelor of Science",
        "ba": "Bachelor of Arts",
        "b.a.": "Bachelor of Arts",
        "bachelor of arts": "Bachelor of Arts",
        "beng": "Bachelor of Engineering",
        "b.eng": "Bachelor of Engineering",
        "bachelor of engineering": "Bachelor of Engineering",
        "bba": "Bachelor of Business Administration",
        "bachelor of business": "Bachelor of Business Administration",
        "bachelor of business administration": "Bachelor of Business Administration",
        "mbbs": "Bachelor of Medicine",
        "bachelor of medicine": "Bachelor of Medicine",
        "md": "Bachelor of Medicine",
        "llb": "Bachelor of Laws",
        "bachelor of laws": "Bachelor of Laws",
        "bed": "Bachelor of Education",
        "bachelor of education": "Bachelor of Education",
        # Masters
        "msc": "Master of Science",
        "m.sc": "Master of Science",
        "ms": "Master of Science",
        "m.s.": "Master of Science",
        "master": "Master of Science",
        "master of science": "Master of Science",
        "masters": "Master of Science",
        "ma": "Master of Arts",
        "m.a.": "Master of Arts",
        "master of arts": "Master of Arts",
        "meng": "Master of Engineering",
        "m.eng": "Master of Engineering",
        "master of engineering": "Master of Engineering",
        "mphil": "Master of Philosophy",
        "m.phil": "Master of Philosophy",
        "master of philosophy": "Master of Philosophy",
        "mba": "Master of Business Administration",
        "master of business administration": "Master of Business Administration",
        "llm": "Master of Laws",
        "master of laws": "Master of Laws",
        "med": "Master of Education",
        "master of education": "Master of Education",
        "mph": "Master of Public Health",
        "master of public health": "Master of Public Health",
        # Doctoral
        "phd": "Doctor of Philosophy",
        "ph.d.": "Doctor of Philosophy",
        "doctor of philosophy": "Doctor of Philosophy",
        "doctorate": "Doctor of Philosophy",
        "dphil": "Doctor of Philosophy",
        "dsc": "Doctor of Science",
        "d.sc": "Doctor of Science",
        "doctor of science": "Doctor of Science",
        "doctor of medicine": "Doctor of Medicine",
        "edd": "Doctor of Education",
        "doctor of education": "Doctor of Education",
        "dba": "Doctor of Business Administration",
        "doctor of business administration": "Doctor of Business Administration",
        # Certificates and Diplomas
        "pgdip": "Master of Arts",  # Postgraduate Diploma → treat as Masters level
        "pgcert": "Master of Arts",  # Postgraduate Certificate → treat as Masters level
        "postgraduate diploma": "Master of Arts",
        "postgraduate certificate": "Master of Arts",
        "diploma": "Master of Arts",
        "certificate": "Master of Arts",
        "mst": "Master of Arts",  # Master of Studies (Oxford)
        "mth": "Master of Arts",  # Master of Theology
        "mres": "Master of Science",  # Master of Research
        "mlitt": "Master of Arts",  # Master of Letters
        "mmus": "Master of Arts",  # Master of Music
    }

    # Try direct match
    if value_lower in degree_map:
        return degree_map[value_lower]

    # Try partial match
    for key, full_name in degree_map.items():
        if key in value_lower or value_lower in key:
            return full_name

    # Default to Master of Science if not recognized
    return "Master of Science"


def normalize_degree_level(value: str) -> str:
    """Normalize degree level string."""
    if not value:
        return "Masters"

    value_lower = value.lower().strip()

    if any(
        term in value_lower
        for term in ["bachelor", "bsc", "ba", "beng", "undergraduate", "ug"]
    ):
        return "Undergraduate"
    elif any(
        term in value_lower
        for term in ["phd", "doctoral", "doctorate", "dphil", "research degree"]
    ):
        return "PhD"
    elif any(
        term in value_lower for term in ["master", "msc", "ma", "mba", "meng", "mphil"]
    ):
        return "Masters"
    elif any(term in value_lower for term in ["graduate", "postgraduate", "pg"]):
        return "Graduate"

    return "Masters"


def normalize_program_category(value: str) -> str:
    """Normalize program category string."""
    if not value:
        return "Other"

    value_lower = value.lower().strip()

    category_map = {
        "Computer Science": [
            "computer",
            "computing",
            "informatics",
            "software",
            "ai",
            "machine learning",
            "data science",
            "cybersecurity",
            "it",
        ],
        "Networking": ["network", "telecommunication", "wireless"],
        "Business": [
            "business",
            "mba",
            "management",
            "finance",
            "accounting",
            "marketing",
            "economics",
            "commerce",
        ],
        "Medical": [
            "medicine",
            "medical",
            "healthcare",
            "nursing",
            "pharmacy",
            "dentistry",
            "health",
            "clinical",
            "biomedical",
        ],
        "Education": ["education", "teaching", "pedagogy", "curriculum", "tesol"],
        "Engineering": [
            "engineering",
            "mechanical",
            "electrical",
            "civil",
            "chemical",
            "aerospace",
        ],
        "Law": ["law", "legal", "jurisprudence", "llm", "jd"],
        "Arts & Humanities": [
            "arts",
            "humanities",
            "literature",
            "history",
            "philosophy",
            "linguistics",
            "music",
        ],
        "Sciences": [
            "biology",
            "chemistry",
            "physics",
            "mathematics",
            "statistics",
            "environmental",
        ],
    }

    for category, keywords in category_map.items():
        if any(kw in value_lower for kw in keywords):
            return category

    return "Other"


class UniversityTier(str, Enum):
    """Enumeration of university tiers based on rankings and reputation."""

    TOP = "top"
    GOOD = "good"
    STANDARD = "standard"


class UniversityType(str, Enum):
    """Enumeration of university types."""

    PUBLIC = "public"
    PRIVATE = "private"
    PRIVATE_NONPROFIT = "private_nonprofit"
    PRIVATE_FORPROFIT = "private_forprofit"


class CampusType(str, Enum):
    """Enumeration of campus types."""

    URBAN = "urban"
    SUBURBAN = "suburban"
    RURAL = "rural"


class University(BaseModel):
    """Comprehensive data model for universities."""

    # Identity and Basic Information
    university_id: Optional[str] = Field(
        None, description="Unique identifier for the university (12-char MD5 hash)"
    )
    name: str = Field(..., description="Official full name of the university")
    alternate_names: List[str] = Field(
        default_factory=list,
        description="Alternative names, abbreviations, or former names",
    )
    motto: Optional[str] = Field(None, description="University motto or slogan")
    description: Optional[str] = Field(
        None, description="Brief description of the university"
    )

    # Location Information
    country: str = Field(..., description="Country where university is located")
    city: str = Field(..., description="Primary city location")
    state_province: Optional[str] = Field(None, description="State or province")
    address: Optional[str] = Field(None, description="Full address of main campus")
    latitude: Optional[float] = Field(
        None, ge=-90, le=90, description="Latitude coordinate"
    )
    longitude: Optional[float] = Field(
        None, ge=-180, le=180, description="Longitude coordinate"
    )
    campus_type: Optional[str] = Field(
        None, description="Type of campus (urban, suburban, rural)"
    )
    campus_size_acres: Optional[int] = Field(
        None, ge=0, description="Campus size in acres"
    )

    # Contact Information
    website: Optional[str] = Field(None, description="Official university website URL")
    admissions_url: Optional[str] = Field(
        None, description="Admissions office website URL"
    )
    email: Optional[str] = Field(None, description="General contact email")
    phone: Optional[str] = Field(None, description="General contact phone number")
    social_media: Dict[str, str] = Field(
        default_factory=dict,
        description="Social media links (facebook, twitter, linkedin, etc.)",
    )

    # Rankings and Reputation
    qs_world_ranking: Optional[int] = Field(
        None, ge=1, description="QS World University Rankings position"
    )
    the_world_ranking: Optional[int] = Field(
        None, ge=1, description="Times Higher Education World Rankings position"
    )
    us_news_ranking: Optional[int] = Field(
        None, ge=1, description="US News Global Universities Rankings position"
    )
    arwu_ranking: Optional[int] = Field(
        None, ge=1, description="Academic Ranking of World Universities position"
    )
    subject_rankings: Dict[str, int] = Field(
        default_factory=dict, description="Subject-specific rankings by field"
    )

    # Classification and Type
    tier: Optional[str] = Field(
        None, description="University tier (top, good, standard)"
    )
    type: Optional[str] = Field(
        None, description="University type (public, private, etc.)"
    )
    founding_year: Optional[int] = Field(
        None, ge=1000, le=2100, description="Year the university was founded"
    )
    research_intensity: Optional[str] = Field(
        None, description="Research intensity level (very high, high, medium, low)"
    )

    # Size and Demographics
    total_students: Optional[int] = Field(
        None, ge=0, description="Total number of enrolled students"
    )
    international_students: Optional[int] = Field(
        None, ge=0, description="Number of international students"
    )
    faculty_count: Optional[int] = Field(
        None, ge=0, description="Total number of faculty members"
    )
    student_faculty_ratio: Optional[float] = Field(
        None, gt=0, description="Student to faculty ratio"
    )

    # Financial Information
    endowment_usd: Optional[int] = Field(
        None, ge=0, description="Endowment value in USD"
    )
    average_tuition_domestic: Optional[int] = Field(
        None, ge=0, description="Average domestic tuition per year in USD"
    )
    average_tuition_international: Optional[int] = Field(
        None, ge=0, description="Average international tuition per year in USD"
    )

    # Facilities and Resources
    libraries_count: Optional[int] = Field(
        None, ge=0, description="Number of libraries"
    )
    research_centers: List[str] = Field(
        default_factory=list, description="Research centers and institutes"
    )
    sports_facilities: List[str] = Field(
        default_factory=list, description="Sports and recreational facilities"
    )
    housing_options: List[str] = Field(
        default_factory=list, description="Available housing options"
    )

    # Accreditation and Memberships
    accreditations: List[str] = Field(
        default_factory=list, description="Accreditation bodies"
    )
    memberships: List[str] = Field(
        default_factory=list, description="Professional memberships and associations"
    )

    # Student Life and Support
    student_organizations: List[str] = Field(
        default_factory=list, description="Student organizations and clubs"
    )
    support_services: List[str] = Field(
        default_factory=list, description="Student support services"
    )
    international_support: List[str] = Field(
        default_factory=list, description="International student support services"
    )

    # Additional Information
    logo_url: Optional[str] = Field(None, description="URL to university logo")
    colors: List[str] = Field(default_factory=list, description="University colors")
    mascot: Optional[str] = Field(None, description="University mascot")

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Record creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    data_source: str = Field("scraped", description="Source of the data")
    confidence_score: float = Field(
        0.0, ge=0.0, le=1.0, description="Confidence score for data accuracy"
    )

    @field_validator("university_id", mode="before")
    @classmethod
    def generate_id_if_not_provided(cls, v):
        """Generate university_id if not provided."""
        return v

    @model_validator(mode="after")
    def generate_university_id_if_missing(self):
        """Generate university_id from name if not provided."""
        if not self.university_id and self.name:
            self.university_id = generate_university_id(self.name)
        return self

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate university name."""
        if not v or not v.strip():
            raise ValueError("University name cannot be empty")
        if len(v) > 200:
            raise ValueError("University name too long")
        return v.strip()

    @field_validator("alternate_names", mode="before")
    @classmethod
    def ensure_list_alternate_names(cls, v):
        """Ensure alternate_names is a list."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        return v

    @field_validator("subject_rankings", "social_media", mode="before")
    @classmethod
    def ensure_dict(cls, v):
        """Ensure dict fields are dicts."""
        if v is None:
            return {}
        return v

    @field_validator(
        "research_centers",
        "sports_facilities",
        "housing_options",
        "accreditations",
        "memberships",
        "student_organizations",
        "support_services",
        "international_support",
        "colors",
        mode="before",
    )
    @classmethod
    def ensure_list(cls, v):
        """Ensure list fields are lists."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        return v

    @model_validator(mode="after")
    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(tz=__import__("datetime").timezone.utc)
        return self

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class LanguageProficiency(BaseModel):
    """Language proficiency requirements."""

    toefl_min: Optional[int] = Field(
        None, ge=0, le=120, description="Minimum TOEFL iBT score"
    )
    ielts_min: Optional[float] = Field(
        None, ge=0.0, le=9.0, description="Minimum IELTS band score"
    )
    pte_min: Optional[int] = Field(None, ge=10, le=90, description="Minimum PTE score")
    duolingo_min: Optional[int] = Field(
        None, ge=10, le=160, description="Minimum Duolingo score"
    )
    gre_required: Optional[bool] = Field(None, description="Whether GRE is required")


class TuitionFees(BaseModel):
    """Tuition fee information."""

    domestic_per_year: Optional[int] = Field(
        None, ge=0, description="Domestic tuition per year in USD"
    )
    international_per_year: Optional[int] = Field(
        None, ge=0, description="International tuition per year in USD"
    )
    currency: str = Field("USD", description="Currency code for fees")
    additional_fees: Optional[Dict[str, int]] = Field(
        None, description="Additional fees (application, etc.)"
    )


class ApplicationDeadlines(BaseModel):
    """Application deadline information."""

    fall_deadline: Optional[str] = Field(
        None, description="Fall intake deadline (YYYY-MM-DD)"
    )
    spring_deadline: Optional[str] = Field(
        None, description="Spring intake deadline (YYYY-MM-DD)"
    )
    summer_deadline: Optional[str] = Field(
        None, description="Summer intake deadline (YYYY-MM-DD)"
    )
    rolling_admission: bool = Field(
        False, description="Whether university has rolling admission"
    )


class Rankings(BaseModel):
    """University ranking information."""

    qs_world_ranking: Optional[int] = Field(
        None, ge=1, description="QS World University Rankings"
    )
    the_world_ranking: Optional[int] = Field(
        None, ge=1, description="Times Higher Education World Rankings"
    )
    us_news_ranking: Optional[int] = Field(
        None, ge=1, description="US News Global Universities Rankings"
    )
    subject_ranking_cs: Optional[int] = Field(
        None, ge=1, description="Computer Science subject ranking"
    )


class UniversityProgram(BaseModel):
    """Main data model for university programs."""

    # Core identifying information
    university_id: Optional[str] = Field(
        None, description="Foreign key reference to University.university_id"
    )
    university_name: str = Field(..., description="Full name of the university")
    program_name: str = Field(..., description="Complete name of the academic program")
    degree_type: str = Field(..., description="Type of degree offered")
    degree_level: str = Field(
        "Masters", description="Level of degree (Undergraduate/Graduate/Masters/PhD)"
    )
    program_category: str = Field(
        "Other",
        description="Program category/field (Computer Science, Business, Medical, etc.)",
    )

    # Location information
    country: str = Field(..., description="Country where university is located")
    city: str = Field(..., description="City where university is located")

    # Academic requirements
    gpa_requirement_min: Optional[float] = Field(
        None, ge=0.0, le=4.0, description="Minimum GPA requirement (4.0 scale)"
    )
    language_requirements: LanguageProficiency = Field(
        default_factory=LanguageProficiency,
        description="Language proficiency requirements",
    )
    prerequisites: List[str] = Field(
        default_factory=list, description="List of prerequisite courses or degrees"
    )

    # Program details
    duration_years: Optional[float] = Field(
        None, gt=0, le=7, description="Program duration in years"
    )
    program_description: Optional[str] = Field(
        "", description="Detailed program description"
    )
    specializations: List[str] = Field(
        default_factory=list, description="Available specializations or tracks"
    )
    faculty_research_interests: List[str] = Field(
        default_factory=list, description="Key research areas and faculty interests"
    )

    # Financial information
    tuition_fees: TuitionFees = Field(
        default_factory=TuitionFees, description="Tuition fee information"
    )
    scholarships_available: List[str] = Field(
        default_factory=list, description="Available scholarships"
    )
    cost_of_living_estimate: Optional[int] = Field(
        None, ge=0, description="Estimated annual cost of living in USD"
    )

    # Application information
    application_deadlines: ApplicationDeadlines = Field(
        default_factory=ApplicationDeadlines,
        description="Application deadline information",
    )
    application_fee: Optional[int] = Field(
        None, ge=0, description="Application fee in USD"
    )

    # Rankings and reputation
    rankings: Rankings = Field(
        default_factory=Rankings, description="University ranking information"
    )

    # Additional information
    career_outcomes: List[str] = Field(
        default_factory=list, description="Career outcomes and job placements"
    )
    research_opportunities: List[str] = Field(
        default_factory=list, description="Research opportunities and labs"
    )
    campus_facilities: List[str] = Field(
        default_factory=list, description="Campus facilities and resources"
    )
    student_reviews_rating: Optional[float] = Field(
        None, ge=0.0, le=5.0, description="Average student rating (0-5 scale)"
    )

    # Metadata
    source_url: Optional[str] = Field(
        None, description="URL where data was scraped from"
    )
    confidence_score: float = Field(
        0.0, ge=0.0, le=1.0, description="Confidence score for data accuracy"
    )
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, description="Last time data was updated"
    )
    data_completeness: float = Field(
        0.0, ge=0.0, le=1.0, description="Percentage of fields with data"
    )

    @field_validator("degree_type", mode="before")
    @classmethod
    def normalize_degree(cls, v):
        """Normalize degree type to valid enum value."""
        if v is None:
            return "Master of Science"  # Default for None values
        if isinstance(v, str):
            return normalize_degree_type(v)
        return v

    @field_validator("degree_level", mode="before")
    @classmethod
    def normalize_level(cls, v):
        """Normalize degree level."""
        if isinstance(v, str):
            return normalize_degree_level(v)
        return v or "Masters"

    @field_validator("program_category", mode="before")
    @classmethod
    def normalize_category(cls, v):
        """Normalize program category."""
        if isinstance(v, str):
            return normalize_program_category(v)
        return v or "Other"

    @field_validator("program_description", mode="before")
    @classmethod
    def ensure_string_description(cls, v):
        """Ensure program_description is a string."""
        if v is None:
            return ""
        return str(v)

    @field_validator("faculty_research_interests", mode="before")
    @classmethod
    def ensure_list_for_research(cls, v):
        """Ensure faculty_research_interests is a list."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        return v

    @field_validator(
        "prerequisites",
        "specializations",
        "scholarships_available",
        "career_outcomes",
        "research_opportunities",
        "campus_facilities",
        mode="before",
    )
    @classmethod
    def ensure_list(cls, v):
        """Ensure list fields are lists."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        return v

    @field_validator("university_name")
    @classmethod
    def validate_university_name(cls, v):
        """Validate university name is not empty and reasonable length."""
        if not v or not v.strip():
            raise ValueError("University name cannot be empty")
        if len(v) > 200:
            raise ValueError("University name too long")
        return v.strip()

    @field_validator("university_id")
    @classmethod
    def validate_university_id(cls, v):
        """Validate university_id is a 12-character hex string."""
        if v is None:
            return v
        if not isinstance(v, str):
            raise ValueError("University ID must be a string")
        if len(v) != 12:
            raise ValueError("University ID must be exactly 12 characters")
        if not re.match(r"^[a-f0-9]{12}$", v):
            raise ValueError(
                "University ID must be a valid 12-character hexadecimal string"
            )
        return v

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

    @model_validator(mode="after")
    def calculate_completeness(self):
        """Calculate data completeness score."""
        total_fields = 0
        filled_fields = 0

        # Define fields to check for completeness
        fields_to_check = [
            "program_description",
            "duration_years",
            "tuition_fees",
            "application_deadlines",
            "gpa_requirement_min",
            "prerequisites",
            "specializations",
            "faculty_research_interests",
        ]

        for field in fields_to_check:
            total_fields += 1
            value = getattr(self, field, None)
            if value is not None and value != "" and value != []:
                if isinstance(value, (list, dict)) and len(value) == 0:
                    continue
                filled_fields += 1

        self.data_completeness = (
            filled_fields / total_fields if total_fields > 0 else 0.0
        )
        return self

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat(), HttpUrl: str}


class ScrapingConfig(BaseModel):
    """Configuration for scraping operations."""

    urls: List[HttpUrl] = Field(..., description="List of URLs to scrape")
    max_concurrent: int = Field(
        5, gt=0, description="Maximum concurrent scraping tasks"
    )
    timeout: int = Field(30, gt=0, description="Timeout for each scraping operation")
    retry_attempts: int = Field(3, ge=0, description="Number of retry attempts")


class AnalysisResult(BaseModel):
    """Result of data analysis operations."""

    total_programs: int = Field(..., description="Total number of programs analyzed")
    average_completeness: float = Field(
        ..., description="Average data completeness score"
    )
    quality_score: float = Field(..., description="Overall data quality score")
    issues_found: List[str] = Field(
        default_factory=list, description="List of issues identified"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Improvement recommendations"
    )


class ExportResult(BaseModel):
    """Result of data export operations."""

    format: str = Field(..., description="Export format (csv, json, xlsx)")
    file_path: str = Field(..., description="Path to exported file")
    record_count: int = Field(..., description="Number of records exported")
    export_time: datetime = Field(
        default_factory=datetime.utcnow, description="Time of export"
    )
    success: bool = Field(True, description="Whether export was successful")

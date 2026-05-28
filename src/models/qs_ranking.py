"""QS World University Rankings data model."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class QSRankingScores(BaseModel):
    """Individual QS ranking score components."""

    academic_reputation: Optional[float] = Field(
        None, ge=0, le=100, description="Academic Reputation Score"
    )
    academic_reputation_rank: Optional[int] = Field(
        None, ge=1, description="Academic Reputation Rank"
    )
    employer_reputation: Optional[float] = Field(
        None, ge=0, le=100, description="Employer Reputation Score"
    )
    employer_reputation_rank: Optional[int] = Field(
        None, ge=1, description="Employer Reputation Rank"
    )
    faculty_student_ratio: Optional[float] = Field(
        None, ge=0, le=100, description="Faculty Student Ratio Score"
    )
    faculty_student_ratio_rank: Optional[int] = Field(
        None, ge=1, description="Faculty Student Ratio Rank"
    )
    citations_per_faculty: Optional[float] = Field(
        None, ge=0, le=100, description="Citations per Faculty Score"
    )
    citations_per_faculty_rank: Optional[int] = Field(
        None, ge=1, description="Citations per Faculty Rank"
    )
    international_faculty: Optional[float] = Field(
        None, ge=0, le=100, description="International Faculty Ratio Score"
    )
    international_faculty_rank: Optional[int] = Field(
        None, ge=1, description="International Faculty Ratio Rank"
    )
    international_students: Optional[float] = Field(
        None, ge=0, le=100, description="International Students Ratio Score"
    )
    international_students_rank: Optional[int] = Field(
        None, ge=1, description="International Students Ratio Rank"
    )
    international_research_network: Optional[float] = Field(
        None, ge=0, le=100, description="International Research Network Score"
    )
    international_research_network_rank: Optional[int] = Field(
        None, ge=1, description="International Research Network Rank"
    )
    employment_outcomes: Optional[float] = Field(
        None, ge=0, le=100, description="Employment Outcomes Score"
    )
    employment_outcomes_rank: Optional[int] = Field(
        None, ge=1, description="Employment Outcomes Rank"
    )
    sustainability: Optional[float] = Field(
        None, ge=0, le=100, description="Sustainability Score"
    )
    sustainability_rank: Optional[int] = Field(
        None, ge=1, description="Sustainability Rank"
    )


class QSRanking(BaseModel):
    """
    QS World University Rankings data model.

    Stores complete ranking data from QS World University Rankings Excel file.
    """

    # Ranking Information
    ranking_year: int = Field(..., description="Year of the ranking (e.g., 2026)")
    rank: int = Field(..., ge=1, description="Current world ranking position")
    rank_display: str = Field(..., description="Display rank (e.g., '1' or '501-510')")
    previous_rank: Optional[int] = Field(
        None, ge=1, description="Previous year ranking position"
    )
    rank_change: Optional[int] = Field(
        None, description="Change in rank (+/- positions)"
    )

    # University Identity
    institution_name: str = Field(..., description="Official institution name")
    institution_name_normalized: str = Field(
        ..., description="Normalized name for matching"
    )

    # Location
    country: str = Field(..., description="Country or territory")
    region: str = Field(
        ..., description="Geographic region (Americas, Europe, Asia, etc.)"
    )

    # Classification
    size: Optional[str] = Field(None, description="University size (S, M, L, XL)")
    focus: Optional[str] = Field(
        None, description="Focus type (CO=Comprehensive, FO=Focused, SP=Specialist)"
    )
    research_intensity: Optional[str] = Field(
        None, description="Research intensity (VH, H, M, L)"
    )
    status: Optional[str] = Field(None, description="Status (Public, Private, etc.)")

    # Scores
    overall_score: Optional[float] = Field(
        None, ge=0, le=100, description="Overall QS score"
    )
    scores: QSRankingScores = Field(
        default_factory=QSRankingScores, description="Detailed score breakdown"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.now, description="Record creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Record update timestamp"
    )
    data_source: str = Field("QS World University Rankings", description="Data source")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        data = self.model_dump()
        data["scores"] = self.scores.model_dump()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QSRanking":
        """Create instance from dictionary."""
        if "scores" in data and isinstance(data["scores"], dict):
            data["scores"] = QSRankingScores(**data["scores"])
        return cls(**data)

"""Pydantic models for ML recommendation API endpoints."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StudentProfile(BaseModel):
    """Student profile for content-based recommendations."""

    gpa: float = Field(3.0, ge=0.0, le=4.0, description="GPA out of 4.0")
    ielts: Optional[float] = Field(None, ge=0.0, le=9.0, description="IELTS score")
    toefl: Optional[int] = Field(None, ge=0, le=120, description="TOEFL score")
    budget: Optional[int] = Field(None, ge=0, description="Max tuition in USD/year")
    preferred_country: Optional[str] = Field(
        None, max_length=100, description="Preferred country"
    )
    degree_level: Optional[str] = Field(
        None, description="Masters | PhD | Undergraduate"
    )
    program_category: Optional[str] = Field(None, description="Field of study")
    top_n: int = Field(10, ge=1, le=50, description="Number of recommendations")


class ProgramRecommendation(BaseModel):
    """A single program recommendation with match score."""

    university_name: str
    program_name: Optional[str] = None
    country: Optional[str] = None
    degree_level: Optional[str] = None
    program_category: Optional[str] = None
    qs_world_ranking: Optional[int] = None
    tuition_international: Optional[float] = None
    match_score: float = Field(..., ge=0.0, le=1.0, description="ML match score")
    predicted_tier: str = Field(..., description="top | good | standard")


class RecommendationResponse(BaseModel):
    """Response from /api/recommend."""

    recommendations: List[ProgramRecommendation]
    total_candidates: int = Field(
        ..., description="Programs considered after filtering"
    )
    filters_applied: Dict[str, Any] = Field(default_factory=dict)
    model_backend: str = "lightgbm"


class SimilarProgramResponse(BaseModel):
    """Response from /api/similar/{program_id}."""

    query_program: Dict[str, Any]
    similar_programs: List[Dict[str, Any]]
    similarity_method: str = "cosine"


class ModelInfoResponse(BaseModel):
    """Response from /api/model/info."""

    model_backend: str
    target_column: str
    class_names: List[str]
    metrics: Dict[str, Optional[float]]
    dataset_shape: List[int]
    training_time_seconds: float
    numeric_features: List[str]
    categorical_features: List[str]
    created_at: str

# In file: schema.py
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional

class UniversityProgram(BaseModel):
    # Key Identifying Fields
    university_name: str = Field(description="The full name of the university (e.g., 'Stanford University')")
    program_name: str = Field(description="The full name of the program (e.g., 'Master of Science in Computer Science')")
    
    # Hard Filtering Fields (for eligibility)
    gpa_requirement_min: Optional[float] = Field(None, description="The minimum required CGPA, standardized to a 4.0 scale.")
    toefl_min: Optional[int] = Field(None, description="Minimum TOEFL iBT score required.")
    ielts_min: Optional[float] = Field(None, description="Minimum IELTS band score required.")
    tuition_fee_per_year: Optional[int] = Field(None, description="The estimated annual tuition fee, in USD. Do not include living expenses.")
    application_deadline: Optional[str] = Field(None, description="The *next* upcoming application deadline, in YYYY-MM-DD format.")
    
    # Semantic Matching Fields (for ranking)
    program_description: str = Field(description="A detailed, multi-sentence summary of the program, its focus, and curriculum.")
    faculty_research_interests: List[str] = Field([], description="A list of key research areas, topics, or faculty specializations.")
    prerequisites: List[str] = Field([], description="A list of required courses or degrees (e.g., 'B.S. in Computer Science')")
    
    # Metadata
    source_url: HttpUrl = Field(description="The exact URL where this data was found.")
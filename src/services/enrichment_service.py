"""Data enrichment and gap-filling services."""

import logging
from typing import Optional

from ..core.config import get_settings
from ..core.constants import UNIVERSITY_METADATA
from ..models.university import University, UniversityProgram
from ..services.llm_service import LLMService

logger = logging.getLogger(__name__)


class EnrichmentService:
    """Service for enriching and improving program data."""

    def __init__(self, llm_service: Optional[LLMService] = None, ranking_service=None):
        self.settings = get_settings()
        self.llm_service = llm_service or LLMService()
        self.ranking_service = (
            ranking_service  # Lazy import to avoid circular dependency
        )

    async def enrich_program_data(
        self, program: UniversityProgram
    ) -> UniversityProgram:
        """
        Enrich program data with additional information.

        Args:
            program: UniversityProgram instance to enrich

        Returns:
            Enriched UniversityProgram instance
        """
        # Enrich with university metadata (static first)
        program = self._enrich_university_metadata(program)

        # Enrich with TopUniversities rankings (if available)
        if self.ranking_service:
            program = await self._enrich_with_topuniversities(program)

        # Fill missing fields with defaults or inferences
        program = self._fill_missing_fields(program)

        # Standardize data formats
        program = self._standardize_formats(program)

        # Update completeness score
        program.data_completeness = self._calculate_completeness(program)

        return program

    async def enrich_university_data(self, university: University) -> University:
        """
        Enrich university data with rankings from TopUniversities.com.

        Args:
            university: University instance to enrich

        Returns:
            Enriched University instance
        """
        # Enrich with TopUniversities rankings
        if self.ranking_service:
            try:
                university = await self.ranking_service.update_university_rankings(
                    university
                )
                logger.info(f"Enriched {university.name} with TopUniversities rankings")
            except Exception as e:
                logger.error(
                    f"Failed to enrich {university.name} with TopUniversities: {e}"
                )

        return university

    async def _enrich_with_topuniversities(
        self, program: UniversityProgram
    ) -> UniversityProgram:
        """Enrich program with rankings from TopUniversities.com."""
        try:
            # Get ranking for this university
            ranking_data = await self.ranking_service.get_university_ranking(
                program.university_name
            )

            if ranking_data:
                # Update QS ranking (TopUniversities is QS rankings)
                if ranking_data.get("rank") and not program.rankings.qs_world_ranking:
                    program.rankings.qs_world_ranking = ranking_data["rank"]
                    logger.info(
                        f"Updated QS ranking for {program.university_name}: {ranking_data['rank']}"
                    )

                # Update location if not set
                if not program.country and ranking_data.get("country"):
                    program.country = ranking_data["country"]
                if not program.city and ranking_data.get("city"):
                    program.city = ranking_data["city"]

        except Exception as e:
            logger.error(f"Error enriching with TopUniversities: {e}")

        return program

    def _enrich_university_metadata(
        self, program: UniversityProgram
    ) -> UniversityProgram:
        """Enrich program with university metadata."""
        university_name = program.university_name

        if university_name in UNIVERSITY_METADATA:
            metadata = UNIVERSITY_METADATA[university_name]

            # Only fill if not already set
            if not program.country:
                program.country = metadata["country"]
            if not program.city:
                program.city = metadata["city"]

            # Add rankings if available and not set
            if not program.rankings.qs_world_ranking and metadata.get("qs_ranking"):
                program.rankings.qs_world_ranking = metadata["qs_ranking"]
            if not program.rankings.the_world_ranking and metadata.get("the_ranking"):
                program.rankings.the_world_ranking = metadata["the_ranking"]
            if not program.rankings.us_news_ranking and metadata.get("us_news_ranking"):
                program.rankings.us_news_ranking = metadata["us_news_ranking"]

        return program

    def _fill_missing_fields(self, program: UniversityProgram) -> UniversityProgram:
        """Fill missing fields with reasonable defaults or inferences."""

        # Infer duration based on degree type if not set
        if not program.duration_years:
            if "bachelor" in program.degree_type.lower():
                program.duration_years = 4.0
            elif "master" in program.degree_type.lower():
                program.duration_years = 2.0
            elif "phd" in program.degree_type.lower():
                program.duration_years = 4.0

        # Set default country if not available
        if not program.country and program.university_name:
            program.country = self._infer_country_from_university(
                program.university_name
            )

        # Add basic program description if missing
        if (
            not program.program_description
            or len(program.program_description.strip()) < 10
        ):
            program.program_description = self._generate_basic_description(program)

        return program

    def _standardize_formats(self, program: UniversityProgram) -> UniversityProgram:
        """Standardize data formats and clean up values."""

        # Standardize university name
        if program.university_name:
            program.university_name = program.university_name.strip()

        # Standardize program name
        if program.program_name:
            program.program_name = program.program_name.strip()

        # Ensure country names are properly formatted
        if program.country:
            program.country = program.country.strip().title()

        # Ensure city names are properly formatted
        if program.city:
            program.city = program.city.strip().title()

        # Standardize degree type
        if program.degree_type:
            program.degree_type = self._standardize_degree_type(program.degree_type)

        return program

    def _standardize_degree_type(self, degree_type: str) -> str:
        """Standardize degree type to match enum values."""
        degree_lower = degree_type.lower().strip()

        # Map common variations to standard types
        mappings = {
            "bachelor of science": "Bachelor of Science",
            "bachelor of arts": "Bachelor of Arts",
            "bachelors": "Bachelor of Science",
            "master of science": "Master of Science",
            "master of arts": "Master of Arts",
            "masters": "Master of Science",
            "msc": "Master of Science",
            "ms": "Master of Science",
            "ma": "Master of Arts",
            "phd": "Doctor of Philosophy",
            "doctorate": "Doctor of Philosophy",
            "doctoral": "Doctor of Philosophy",
        }

        return mappings.get(degree_lower, degree_type)

    def _infer_country_from_university(self, university_name: str) -> str:
        """Infer country from university name."""
        name_lower = university_name.lower()

        # Check for country indicators in name
        country_indicators = {
            "united states": [
                "stanford",
                "harvard",
                "mit",
                "berkeley",
                "california",
                "yale",
            ],
            "united kingdom": [
                "oxford",
                "cambridge",
                "london",
                "manchester",
                "edinburgh",
            ],
            "germany": ["munich", "heidelberg", "berlin", "hamburg"],
            "switzerland": ["zurich", "lausanne", "geneva"],
            "canada": ["toronto", "montreal", "vancouver", "british columbia"],
            "australia": ["melbourne", "sydney", "canberra"],
            "singapore": ["singapore"],
            "china": ["beijing", "shanghai", "tsinghua", "peking"],
            "netherlands": ["amsterdam", "delft", "utrecht"],
        }

        for country, indicators in country_indicators.items():
            if any(indicator in name_lower for indicator in indicators):
                return country.title()

        return "Unknown"

    def _generate_basic_description(self, program: UniversityProgram) -> str:
        """Generate a basic program description if missing."""
        degree = program.degree_type or "degree"
        field = "Computer Science"

        if program.specializations:
            specializations_text = (
                f" with specializations in {', '.join(program.specializations[:3])}"
            )
        else:
            specializations_text = ""

        duration_text = ""
        if program.duration_years:
            duration_text = f" This {program.duration_years}-year program"

        description = f"This is a {degree} program in {field}{specializations_text}.{duration_text} The program provides comprehensive education in computer science fundamentals and advanced topics."

        if program.university_name:
            description += f" Offered by {program.university_name}."

        return description

    def _calculate_completeness(self, program: UniversityProgram) -> float:
        """Calculate data completeness score."""
        total_fields = 0
        filled_fields = 0

        # Define fields to check for completeness
        fields_to_check = [
            ("program_description", str),
            ("duration_years", (int, float)),
            ("tuition_fees.international_per_year", (int, float)),
            ("application_deadlines.fall_deadline", str),
            ("gpa_requirement_min", (int, float)),
            ("prerequisites", list),
            ("specializations", list),
            ("faculty_research_interests", list),
            ("country", str),
            ("city", str),
        ]

        for field_path, expected_types in fields_to_check:
            total_fields += 1

            try:
                # Handle nested fields
                if "." in field_path:
                    obj = program
                    for part in field_path.split("."):
                        obj = getattr(obj, part, None)
                        if obj is None:
                            break
                    value = obj
                else:
                    value = getattr(program, field_path)

                # Check if field has meaningful content
                if value is not None:
                    if isinstance(value, str) and value.strip():
                        filled_fields += 1
                    elif isinstance(value, (int, float)) and value > 0:
                        filled_fields += 1
                    elif isinstance(value, list) and len(value) > 0:
                        filled_fields += 1

            except AttributeError:
                continue

        return filled_fields / total_fields if total_fields > 0 else 0.0

    async def enrich_with_llm(self, program: UniversityProgram) -> UniversityProgram:
        """
        Use LLM to enrich program data with additional information.

        Args:
            program: UniversityProgram instance to enrich

        Returns:
            LLM-enriched UniversityProgram instance
        """
        try:
            # Generate enhanced description
            if program.program_description and len(program.program_description) < 200:
                enhanced_desc = await self.llm_service.generate_summary(
                    content=program.program_description, max_length=500
                )
                if enhanced_desc and len(enhanced_desc) > len(
                    program.program_description
                ):
                    program.program_description = enhanced_desc

            # Infer missing specializations
            if not program.specializations:
                prompt = f"""
                Based on this computer science program description, suggest 3-5 relevant specializations or focus areas:

                Program: {program.program_name}
                Description: {program.program_description}

                Return only a comma-separated list of specializations.
                """

                try:
                    response = await self.llm_service.generate_completion(
                        prompt=prompt, temperature=0.3, max_tokens=100
                    )
                    specializations = [
                        s.strip() for s in response.split(",") if s.strip()
                    ]
                    if specializations:
                        program.specializations = specializations[:5]
                except Exception as e:
                    logger.debug(f"Could not infer specializations: {e}")

            # Infer research interests if missing
            if not program.faculty_research_interests and program.program_description:
                prompt = f"""
                Extract key research areas from this program description:

                {program.program_description}

                Return 3-5 research areas as a comma-separated list.
                """

                try:
                    response = await self.llm_service.generate_completion(
                        prompt=prompt, temperature=0.3, max_tokens=150
                    )
                    research_areas = [
                        r.strip() for r in response.split(",") if r.strip()
                    ]
                    if research_areas:
                        program.faculty_research_interests = research_areas[:5]
                except Exception as e:
                    logger.debug(f"Could not infer research interests: {e}")

        except Exception as e:
            logger.error(f"LLM enrichment failed: {e}")
            # Continue without LLM enrichment

        return program

"""TopUniversities → Recommendation System schema transformer.

Converts a university record from the TopUniversities scraper output format
(nested sections: identity / location / profile / demographics / rankings /
contact / financials / crawl_metadata) into the flat University Pydantic model
used by the Recommendation System's MongoDB repositories.

Also handles the known quirks in the real scraped data:
  - Duplicate ranking entries  (handled by ranking_normalizer)
  - Rank strings like "1201-1400", "=5", "1401+"
  - total_students == 0 treated as None
  - Social-media links that all point to TopUniversities (not the university)
  - contact.website pointing to TopUniversities' own domain
  - QS World ranking extracted as qs_world_ranking (int) for the ML feature
  - Multi-signal tier derivation via pipeline.tier_derivation
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from src.models.university import University, generate_university_id
from pipeline.ranking_normalizer import (
    QS_WORLD,
    normalize_rankings_array,
    extract_rank_value,
)
from pipeline.tier_derivation import derive_tier, derive_tier_with_metadata

logger = logging.getLogger(__name__)

# TopUniversities' own domain – any website that contains it is NOT the
# university's official site (it's just a link back to their profile page).
_TOPUNI_DOMAIN = "topuniversities.com"


# ── helpers ───────────────────────────────────────────────────────────────────

def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        v = int(float(str(value)))
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        v = float(str(value))
        return v if v != 0.0 else None
    except (ValueError, TypeError):
        return None


def _clean_website(url: str | None) -> Optional[str]:
    """Return None if URL belongs to TopUniversities (not the real university)."""
    if not url:
        return None
    if _TOPUNI_DOMAIN in url:
        return None
    return url.strip()


def _clean_text(text: str | None) -> Optional[str]:
    if not text:
        return None
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _international_students_count(demographics: dict) -> Optional[int]:
    """Derive international student count from pct + total."""
    total = _safe_int(demographics.get("total_students"))
    pct_raw = demographics.get("international_students_pct")
    if total and pct_raw:
        try:
            pct = float(str(pct_raw).replace("%", "").strip())
            return int(total * pct / 100)
        except (ValueError, TypeError):
            pass
    intl = _safe_int(demographics.get("international_students"))
    return intl


# ── main transformer ──────────────────────────────────────────────────────────

def transform_university(raw: dict) -> Optional[University]:
    """Transform a single TopUniversities university record into a University model.

    Args:
        raw: Dict loaded from universities.jsonl (one line per university).

    Returns:
        University Pydantic model, or None if critical fields are missing.
    """
    try:
        identity = raw.get("identity", {})
        location = raw.get("location", {})
        profile = raw.get("profile", {})
        demographics = raw.get("demographics", {})
        raw_rankings = raw.get("rankings", [])
        contact = raw.get("contact", {})
        financials = raw.get("financials", {})
        crawl_meta = raw.get("crawl_metadata", {})

        name = _safe_str(identity.get("name"))
        if not name:
            logger.warning("Skipping record with no name: %s", raw.get("source_url"))
            return None

        slug = _safe_str(identity.get("slug"))
        country = _safe_str(location.get("country"))
        city = _safe_str(location.get("city"))

        # Use empty strings as defaults, not None — University model requires country & city
        if not country:
            country = "Unknown"
        if not city:
            city = "Unknown"

        # Normalise rankings array (dedup + parse rank strings)
        rankings = normalize_rankings_array(raw_rankings)

        # QS World rank as a scalar (for the qs_world_ranking ML feature)
        qs_world_rank = extract_rank_value(rankings, QS_WORLD)

        # Multi-signal tier
        tier_meta = derive_tier_with_metadata(rankings)
        tier = tier_meta["tier"]

        # Demographics
        total_students = _safe_int(demographics.get("total_students"))
        faculty_count = _safe_int(demographics.get("faculty_count"))
        international_students = _international_students_count(demographics)

        # Student:faculty ratio
        sfr: Optional[float] = None
        if total_students and faculty_count and faculty_count > 0:
            sfr = round(total_students / faculty_count, 2)

        # Website — prefer canonical URL which always points to TopUniversities
        # profile (acceptable as a reference link), strip TopUni domain websites
        canonical = _safe_str(
            crawl_meta.get("canonical_url") or identity.get("canonical_url")
        )
        website = _clean_website(contact.get("website")) or (
            canonical if canonical else None
        )

        # Tuition from financials (usually sparse — 22% coverage)
        tuition_domestic: Optional[int] = None
        tuition_international: Optional[int] = None
        if financials:
            td = financials.get("tuition_domestic") or {}
            ti = financials.get("tuition_international") or {}
            tuition_domestic = _safe_int(td.get("amount") or td.get("amount_min"))
            tuition_international = _safe_int(ti.get("amount") or ti.get("amount_min"))

        # Founding year
        founding_year = _safe_int(profile.get("established_year"))

        # Build the ranking_signals list (stored for future reference / audit)
        # Format: [{"ranking_type": "QS World...", "rank": 42, "rank_display": "42"}, ...]
        ranking_signals = [
            {
                "ranking_type": r.get("ranking_type", ""),
                "rank": r.get("rank"),
                "rank_display": r.get("rank_display", ""),
            }
            for r in rankings
            if r.get("ranking_type")
        ]

        # Generate a stable university_id from the slug (preferred) or name
        uni_id = generate_university_id(slug or name)

        university = University(
            university_id=uni_id,
            name=name,
            country=country,
            city=city,
            state_province=_safe_str(location.get("state")) or None,
            address=_safe_str(location.get("address")) or None,
            latitude=_safe_float(location.get("latitude")),
            longitude=_safe_float(location.get("longitude")),
            description=_clean_text(
                profile.get("description_full") or profile.get("description_short")
            ),
            website=website,
            qs_world_ranking=qs_world_rank,
            tier=tier,
            type=_safe_str(profile.get("institution_type")) or None,
            founding_year=founding_year,
            total_students=total_students,
            international_students=international_students,
            faculty_count=faculty_count,
            student_faculty_ratio=sfr,
            average_tuition_domestic=tuition_domestic,
            average_tuition_international=tuition_international,
        )

        # Attach extra metadata not in the core model as custom attributes
        # These will be stored as additional fields in MongoDB
        university.__dict__["slug"] = slug
        university.__dict__["ranking_signals"] = ranking_signals
        university.__dict__["tier_metadata"] = tier_meta
        university.__dict__["content_hash"] = _safe_str(crawl_meta.get("content_hash"))
        university.__dict__["source_url"] = _safe_str(
            crawl_meta.get("source_url") or raw.get("source_url")
        )
        university.__dict__["crawled_at"] = _safe_str(
            crawl_meta.get("crawl_timestamp") or raw.get("crawled_at")
        )

        return university

    except Exception as e:
        logger.error("Failed to transform university record: %s — %s", raw.get("identity", {}).get("name", "?"), e)
        return None


def transform_program(raw: dict) -> Optional[dict]:
    """Transform a TopUniversities program record into a flat dict suitable for
    UniversityProgram model construction.

    The program data from TopUniversities is semi-structured:
        - programme_header: programme_title, campus_location
        - overview: highlights (degree, study_level, study_mode, main_subject), description_short
        - admission_requirements: exam_scores[], gpa_score, english_requirements[]
        - tuition_fees: []
        - badges: []
        - qs_subject_rankings: ranking_history[]

    Returns:
        Dict suitable for UniversityProgram(**dict), or None on failure.
    """
    try:
        header = raw.get("programme_header", {})
        overview = raw.get("overview", {})
        admission = raw.get("admission_requirements", {})
        fees = raw.get("tuition_fees", [])
        badges = raw.get("badges", [])
        qs_subject = raw.get("qs_subject_rankings", {})

        programme_title = _safe_str(header.get("programme_title"))
        parent_slug = _safe_str(raw.get("parent_university_slug"))

        if not programme_title or not parent_slug:
            return None

        # Parse highlights dict from overview
        highlights: dict[str, str] = {}
        for hl in overview.get("highlights", []):
            label = _safe_str(hl.get("label")).lower().replace(" ", "_").replace("/", "_")
            value = _safe_str(hl.get("value"))
            if label and value:
                highlights[label] = value

        # Degree type from highlights
        raw_degree = highlights.get("degree", "") or highlights.get("qualification", "")
        from src.models.university import normalize_degree_type, normalize_degree_level
        degree_type = normalize_degree_type(raw_degree)
        degree_level = normalize_degree_level(
            highlights.get("study_level", "") or raw_degree
        )

        # Tuition — pick international fee if available, else any fee
        tuition_amount: Optional[float] = None
        tuition_currency = "USD"
        for fee in fees:
            amount_str = _safe_str(fee.get("fee_amount"))
            if amount_str:
                from pipeline.ranking_normalizer import parse_rank  # reuse numeric parser
                # Fee amounts are like "$55,000", "€12,000"
                amt_match = re.search(r"[\d,]+\.?\d*", amount_str.replace(",", ""))
                if amt_match:
                    tuition_amount = float(amt_match.group())
                    if "€" in amount_str:
                        tuition_currency = "EUR"
                    elif "£" in amount_str:
                        tuition_currency = "GBP"
                    break  # Use first fee found

        # GPA
        gpa_raw = _safe_str(admission.get("gpa_score"))
        gpa_min: Optional[float] = None
        if gpa_raw:
            try:
                gpa_min = float(gpa_raw.split("/")[0].strip())
            except ValueError:
                pass

        # Entry requirements — join exam scores into a list
        entry_reqs: list[str] = []
        for exam in admission.get("exam_scores", []):
            name = _safe_str(exam.get("exam_name"))
            score = _safe_str(exam.get("score"))
            if name:
                entry_reqs.append(f"{name}: {score}" if score else name)
        for eng in admission.get("english_requirements", []):
            name = _safe_str(eng.get("exam_name"))
            score = _safe_str(eng.get("score"))
            if name:
                entry_reqs.append(f"{name}: {score}" if score else name)

        # Field of study from main_subject highlight or subject category
        field_of_study = (
            highlights.get("main_subject")
            or highlights.get("main_subject_area")
            or highlights.get("subject_area")
            or ""
        )
        from src.models.university import normalize_program_category
        program_category = normalize_program_category(field_of_study or programme_title)

        # Programme badges → subject ranking
        subject_rank: Optional[int] = None
        for badge in badges:
            val = _safe_str(badge.get("value"))
            label_b = _safe_str(badge.get("label")).lower()
            if "ranking" in label_b and val:
                from pipeline.ranking_normalizer import parse_rank as _pr
                subject_rank = _pr(val)
                break

        # QS subject ranking history (latest year)
        qs_history = qs_subject.get("ranking_history", [])
        if qs_history and not subject_rank:
            latest = sorted(qs_history, key=lambda x: str(x.get("year", "")), reverse=True)
            if latest:
                from pipeline.ranking_normalizer import parse_rank as _pr
                subject_rank = _pr(latest[0].get("rank"))

        study_mode = highlights.get("study_mode") or highlights.get("mode_of_study") or None

        return {
            "program_name": programme_title,
            "university_name": parent_slug,  # resolved to real name on import
            "country": _parse_country_from_location(header.get("campus_location", "")),
            "city": _parse_city_from_location(header.get("campus_location", "")),
            "degree_type": degree_type,
            "degree_level": degree_level,
            "field_of_study": field_of_study or program_category,
            "program_category": program_category,
            "mode_of_study": study_mode,
            "gpa_requirement_min": gpa_min,
            "entry_requirements": entry_reqs,
            "tuition_fees": {
                "international_per_year": int(tuition_amount) if tuition_amount else None,
                "currency": tuition_currency,
            },
            "subject_ranking": subject_rank,
            "description": _clean_text(overview.get("description_short")),
            "source_url": _safe_str(raw.get("source_url")),
            "parent_university_slug": parent_slug,
            "program_slug": _safe_str(raw.get("program_slug")),
            "crawled_at": _safe_str(raw.get("crawled_at")),
        }

    except Exception as e:
        logger.error(
            "Failed to transform program '%s': %s",
            raw.get("programme_header", {}).get("programme_title", "?"),
            e,
        )
        return None


def _parse_country_from_location(campus_location: str) -> str:
    """Extract country from campus location string like 'Boston, US, Boston United States'."""
    if not campus_location:
        return "Unknown"
    # Pattern: "..., Country Name" at end, or try "US" country code
    parts = [p.strip() for p in campus_location.split(",")]
    if len(parts) >= 3:
        # Usually: "Address, City, CountryCode, City Country"
        # or: "City United States" at the end
        last = parts[-1]
        words = last.split()
        if len(words) >= 2:
            # "Boston United States" → "United States"
            return " ".join(words[1:])
        return last
    if len(parts) == 2:
        return parts[-1]
    return "Unknown"


def _parse_city_from_location(campus_location: str) -> str:
    """Extract city from campus location string."""
    if not campus_location:
        return "Unknown"
    parts = [p.strip() for p in campus_location.split(",")]
    if len(parts) >= 2:
        return parts[-2] if len(parts) >= 2 else parts[0]
    return parts[0] if parts else "Unknown"

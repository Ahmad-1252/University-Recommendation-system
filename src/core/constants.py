"""Constants and configuration data for the University Recommendation System."""

from typing import Dict, List


# University program URLs for computer science programs
UNIVERSITY_URLS: Dict[str, str] = {
    # Top Universities
    "University of Oxford": "https://www.cs.ox.ac.uk/research/graduate-study/mphil-dphil-computer-science/",
    "University of Cambridge": "https://www.cst.cam.ac.uk/prospective/postgraduate",
    "Imperial College London": "https://www.imperial.ac.uk/computing/prospective-students/courses/msc-computing/",
    "ETH Zurich": "https://ethz.ch/en/studies/en/master/computer-science.html",
    "UCL": "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/computer-science-msc",
    "Université PSL": "https://www.psl.eu/en/academic-offer/master-programmes/computer-science",
    "Technical University of Munich": "https://www.tum.de/en/studies/application/master/computer-science/",
    "EPFL": "https://www.epfl.ch/education/studies/en/rules-and-procedures/master/computer-science/",

    # Strong Universities
    "University of Edinburgh": "https://www.ed.ac.uk/studying/postgraduate/degrees/index.php?r=site/view&id=919",
    "University of Manchester": "https://www.manchester.ac.uk/study/postgraduate-research/programmes/list/02674/msc-advanced-computer-science/",
    "King's College London": "https://www.kcl.ac.uk/study/postgraduate-taught/courses/computer-science-msc",
    "Delft University of Technology": "https://www.tudelft.nl/en/education/programmes/masters/computer-science/msc-computer-science/",
    "University of Glasgow": "https://www.gla.ac.uk/postgraduate/taught/computerscience/",
    "University of Leeds": "https://www.leeds.ac.uk/info/130000/postgraduate_taught_courses/130001/Computer_Science",
    "University of Amsterdam": "https://www.uva.nl/en/programmes/master-s/master-s-programmes/content/folder/computer-science/computer-science.html",
    "LMU Munich": "https://www.lmu.de/en/studies/degree-programmes/master/computer-science/",
    "University of Warwick": "https://warwick.ac.uk/study/postgraduate/courses/computerscience",
    "Heidelberg University": "https://www.uni-heidelberg.de/en/study/all-subjects/computer-science/computer-science-master",

    # Medium Universities
    "Utrecht University": "https://www.uu.nl/en/masters/computer-science",
    "University of Tartu": "https://www.ut.ee/en/study/programme/computer-science-msc",
    "University of Athens": "https://www.uoa.gr/en/studies/postgraduate-studies/postgraduate-programmes/computer-science",
    "KU Leuven": "https://www.kuleuven.be/en/study/programmes/master-of-science-in-computer-science",
    "Leiden University": "https://www.universiteitleiden.nl/en/education/study-programmes/master/computer-science"
}

# University rankings and metadata
UNIVERSITY_METADATA: Dict[str, Dict] = {
    "Harvard University": {
        "country": "United States",
        "city": "Cambridge, MA",
        "tier": "top",
        "qs_ranking": 5,
        "the_ranking": 2,
        "us_news_ranking": 3
    },
    "Stanford University": {
        "country": "United States",
        "city": "Stanford, CA",
        "tier": "top",
        "qs_ranking": 4,
        "the_ranking": 4,
        "us_news_ranking": 3
    },
    "MIT": {
        "country": "United States",
        "city": "Cambridge, MA",
        "tier": "top",
        "qs_ranking": 1,
        "the_ranking": 5,
        "us_news_ranking": 2
    },
    "University of Oxford": {
        "country": "United Kingdom",
        "city": "Oxford",
        "tier": "top",
        "qs_ranking": 2,
        "the_ranking": 1,
        "us_news_ranking": 6
    },
    "University of Cambridge": {
        "country": "United Kingdom",
        "city": "Cambridge",
        "tier": "top",
        "qs_ranking": 3,
        "the_ranking": 3,
        "us_news_ranking": 2
    },
    "Imperial College London": {
        "country": "United Kingdom",
        "city": "London",
        "tier": "top",
        "qs_ranking": 8,
        "the_ranking": 8,
        "us_news_ranking": 8
    },
    "ETH Zurich": {
        "country": "Switzerland",
        "city": "Zurich",
        "tier": "top",
        "qs_ranking": 9,
        "the_ranking": 11,
        "us_news_ranking": 7
    },
    "EPFL": {
        "country": "Switzerland",
        "city": "Lausanne",
        "tier": "top",
        "qs_ranking": 14,
        "the_ranking": 30,
        "us_news_ranking": 16
    },
    "Technical University of Munich": {
        "country": "Germany",
        "city": "Munich",
        "tier": "top",
        "qs_ranking": 37,
        "the_ranking": 37,
        "us_news_ranking": 41
    },
    "University of Toronto": {
        "country": "Canada",
        "city": "Toronto",
        "tier": "top",
        "qs_ranking": 21,
        "the_ranking": 18,
        "us_news_ranking": 17
    },
    "McGill University": {
        "country": "Canada",
        "city": "Montreal",
        "tier": "good",
        "qs_ranking": 30,
        "the_ranking": 49,
        "us_news_ranking": 51
    },
    "University of British Columbia": {
        "country": "Canada",
        "city": "Vancouver",
        "tier": "good",
        "qs_ranking": 40,
        "the_ranking": 37,
        "us_news_ranking": 35
    },
    "Carnegie Mellon University": {
        "country": "United States",
        "city": "Pittsburgh, PA",
        "tier": "top",
        "qs_ranking": 52,
        "the_ranking": 24,
        "us_news_ranking": 22
    },
    "Australian National University": {
        "country": "Australia",
        "city": "Canberra",
        "tier": "good",
        "qs_ranking": 30,
        "the_ranking": 54,
        "us_news_ranking": 62
    },
    "University of Melbourne": {
        "country": "Australia",
        "city": "Melbourne",
        "tier": "good",
        "qs_ranking": 14,
        "the_ranking": 33,
        "us_news_ranking": 37
    },
    "University of Sydney": {
        "country": "Australia",
        "city": "Sydney",
        "tier": "good",
        "qs_ranking": 19,
        "the_ranking": 41,
        "us_news_ranking": 41
    },
    "National University of Singapore": {
        "country": "Singapore",
        "city": "Singapore",
        "tier": "top",
        "qs_ranking": 8,
        "the_ranking": 21,
        "us_news_ranking": 32
    },
    "University of Hong Kong": {
        "country": "Hong Kong",
        "city": "Hong Kong",
        "tier": "good",
        "qs_ranking": 21,
        "the_ranking": 35,
        "us_news_ranking": 89
    },
    "Peking University": {
        "country": "China",
        "city": "Beijing",
        "tier": "good",
        "qs_ranking": 12,
        "the_ranking": 14,
        "us_news_ranking": 43
    },
    "Tsinghua University": {
        "country": "China",
        "city": "Beijing",
        "tier": "good",
        "qs_ranking": 12,
        "the_ranking": 12,
        "us_news_ranking": 28
    },
    "UCL": {
        "country": "United Kingdom",
        "city": "London",
        "tier": "top",
        "qs_ranking": 9,
        "the_ranking": 22,
        "us_news_ranking": 16
    },
    "Université PSL": {
        "country": "France",
        "city": "Paris",
        "tier": "good",
        "qs_ranking": 44,
        "the_ranking": 46,
        "us_news_ranking": 60
    },
    "University of Edinburgh": {
        "country": "United Kingdom",
        "city": "Edinburgh",
        "tier": "good",
        "qs_ranking": 22,
        "the_ranking": 30,
        "us_news_ranking": 30
    },
    "University of Manchester": {
        "country": "United Kingdom",
        "city": "Manchester",
        "tier": "good",
        "qs_ranking": 28,
        "the_ranking": 54,
        "us_news_ranking": 63
    },
    "King's College London": {
        "country": "United Kingdom",
        "city": "London",
        "tier": "good",
        "qs_ranking": 35,
        "the_ranking": 35,
        "us_news_ranking": 35
    },
    "Delft University of Technology": {
        "country": "Netherlands",
        "city": "Delft",
        "tier": "good",
        "qs_ranking": 57,
        "the_ranking": 61,
        "us_news_ranking": 63
    },
    "University of Glasgow": {
        "country": "United Kingdom",
        "city": "Glasgow",
        "tier": "good",
        "qs_ranking": 73,
        "the_ranking": 86,
        "us_news_ranking": 86
    },
    "University of Leeds": {
        "country": "United Kingdom",
        "city": "Leeds",
        "tier": "good",
        "qs_ranking": 75,
        "the_ranking": 125,
        "us_news_ranking": 101
    },
    "University of Amsterdam": {
        "country": "Netherlands",
        "city": "Amsterdam",
        "tier": "good",
        "qs_ranking": 58,
        "the_ranking": 58,
        "us_news_ranking": 58
    },
    "LMU Munich": {
        "country": "Germany",
        "city": "Munich",
        "tier": "good",
        "qs_ranking": 64,
        "the_ranking": 32,
        "us_news_ranking": 43
    },
    "University of Warwick": {
        "country": "United Kingdom",
        "city": "Coventry",
        "tier": "good",
        "qs_ranking": 64,
        "the_ranking": 104,
        "us_news_ranking": 78
    },
    "Heidelberg University": {
        "country": "Germany",
        "city": "Heidelberg",
        "tier": "good",
        "qs_ranking": 67,
        "the_ranking": 42,
        "us_news_ranking": 54
    },
    "Utrecht University": {
        "country": "Netherlands",
        "city": "Utrecht",
        "tier": "standard",
        "qs_ranking": 110,
        "the_ranking": 75,
        "us_news_ranking": 52
    },
    "University of Tartu": {
        "country": "Estonia",
        "city": "Tartu",
        "tier": "standard",
        "qs_ranking": 295,
        "the_ranking": 301,
        "us_news_ranking": 350
    },
    "University of Athens": {
        "country": "Greece",
        "city": "Athens",
        "tier": "standard",
        "qs_ranking": 651,
        "the_ranking": 601,
        "us_news_ranking": 500
    },
    "KU Leuven": {
        "country": "Belgium",
        "city": "Leuven",
        "tier": "good",
        "qs_ranking": 45,
        "the_ranking": 45,
        "us_news_ranking": 45
    },
    "Leiden University": {
        "country": "Netherlands",
        "city": "Leiden",
        "tier": "good",
        "qs_ranking": 139,
        "the_ranking": 71,
        "us_news_ranking": 79
    }
}

# Degree types
DEGREE_TYPES: List[str] = [
    "Bachelor of Science",
    "Bachelor of Arts",
    "Master of Science",
    "Master of Arts",
    "Master of Engineering",
    "Doctor of Philosophy",
    "Doctor of Science"
]

# Program specializations
PROGRAM_SPECIALIZATIONS: List[str] = [
    "Artificial Intelligence",
    "Machine Learning",
    "Data Science",
    "Computer Vision",
    "Natural Language Processing",
    "Robotics",
    "Cybersecurity",
    "Software Engineering",
    "Computer Networks",
    "Distributed Systems",
    "Human-Computer Interaction",
    "Computer Graphics",
    "Algorithms",
    "Theory of Computation",
    "Database Systems",
    "Web Development",
    "Mobile Computing",
    "Cloud Computing",
    "Blockchain",
    "IoT",
    "Bioinformatics"
]

# Language proficiency requirements
LANGUAGE_REQUIREMENTS: Dict[str, Dict] = {
    "TOEFL": {
        "min_score": 80,
        "max_score": 120,
        "sections": ["Reading", "Listening", "Speaking", "Writing"]
    },
    "IELTS": {
        "min_score": 6.0,
        "max_score": 9.0,
        "sections": ["Listening", "Reading", "Writing", "Speaking"]
    },
    "PTE": {
        "min_score": 50,
        "max_score": 90,
        "sections": ["Speaking", "Writing", "Reading", "Listening"]
    },
    "Duolingo": {
        "min_score": 105,
        "max_score": 160,
        "sections": []
    }
}

# Currency codes for tuition fees
CURRENCY_CODES: Dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "CAD": "C$",
    "AUD": "A$",
    "CHF": "CHF",
    "CNY": "¥",
    "SGD": "S$",
    "HKD": "HK$"
}

# Application deadlines (typical patterns)
APPLICATION_DEADLINES: Dict[str, str] = {
    "fall": "December 15 - January 15",
    "spring": "September 1 - October 1",
    "summer": "March 1 - April 1",
    "rolling": "Various dates throughout the year"
}

# Data quality thresholds
QUALITY_THRESHOLDS: Dict[str, float] = {
    "min_confidence_score": 0.7,
    "min_field_completeness": 0.8,
    "max_duplicate_rate": 0.05
}

# Export format configurations
EXPORT_CONFIGS: Dict[str, Dict] = {
    "csv": {
        "delimiter": ",",
        "encoding": "utf-8-sig",
        "date_format": "%Y-%m-%d"
    },
    "json": {
        "indent": 2,
        "ensure_ascii": False,
        "date_format": "%Y-%m-%d"
    },
    "xlsx": {
        "engine": "openpyxl",
        "date_format": "%Y-%m-%d"
    }
}

# LLM prompt templates
LLM_PROMPTS: Dict[str, str] = {
    "program_extraction": """
Extract detailed information about the computer science program from the provided webpage content.
Focus on academic requirements, tuition, deadlines, and program details.

Return a structured JSON object with the following fields:
- university_name: Full university name
- program_name: Complete program name
- degree_type: Type of degree (Bachelor/Master/PhD)
- duration: Program duration in years or semesters
- tuition_fee_per_year: Annual tuition in USD
- application_deadline: Next deadline in YYYY-MM-DD format
- gpa_requirement_min: Minimum GPA required (4.0 scale)
- toefl_min: Minimum TOEFL score
- ielts_min: Minimum IELTS score
- prerequisites: List of required courses/degrees
- program_description: Detailed program description
- specializations: List of available specializations
- faculty_research_interests: Key research areas
- country: Country where university is located
- city: City where university is located

Be as accurate and complete as possible. If information is not available, use null.
""",
    "quality_assessment": """
Assess the quality and completeness of the extracted program data.
Rate each field on a scale of 0-1 for confidence in accuracy.
Calculate overall completeness percentage.
"""
}
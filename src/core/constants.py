"""Constants and configuration data for the University Recommendation System."""

from typing import Dict, List


# Program Categories/Fields to scrape
PROGRAM_CATEGORIES: Dict[str, List[str]] = {
    "Computer Science": [
        "computer science", "computing", "informatics", "software engineering",
        "artificial intelligence", "machine learning", "data science", "cybersecurity",
        "information technology", "computer engineering"
    ],
    "Networking": [
        "networking", "network engineering", "telecommunications", "network security",
        "network administration", "computer networks", "wireless networks"
    ],
    "Business": [
        "business", "mba", "management", "finance", "accounting", "marketing",
        "entrepreneurship", "business administration", "commerce", "economics",
        "international business", "supply chain", "operations management"
    ],
    "Medical": [
        "medicine", "medical", "healthcare", "nursing", "pharmacy", "dentistry",
        "public health", "biomedical", "clinical", "health sciences", "physiotherapy",
        "occupational therapy", "medical imaging", "pathology"
    ],
    "Education": [
        "education", "teaching", "pedagogy", "curriculum", "educational leadership",
        "special education", "early childhood", "educational psychology", "tesol",
        "educational technology"
    ],
    "Engineering": [
        "engineering", "mechanical", "electrical", "civil", "chemical", "aerospace",
        "industrial", "environmental engineering", "materials science"
    ],
    "Law": [
        "law", "legal", "jurisprudence", "llm", "jd"
    ],
    "Arts & Humanities": [
        "arts", "humanities", "literature", "history", "philosophy", "linguistics",
        "languages", "music", "fine arts", "creative writing"
    ],
    "Sciences": [
        "biology", "chemistry", "physics", "mathematics", "statistics",
        "environmental science", "geology", "astronomy"
    ]
}

# Degree Levels to scrape
DEGREE_LEVELS: Dict[str, List[str]] = {
    "Undergraduate": [
        "bachelor", "bsc", "ba", "beng", "bba", "undergraduate", "ug"
    ],
    "Graduate": [
        "graduate", "postgraduate", "pg"
    ],
    "Masters": [
        "master", "msc", "ma", "mba", "meng", "mphil", "masters", "taught masters"
    ],
    "PhD": [
        "phd", "doctorate", "doctoral", "dphil", "research degree"
    ]
}

# University Course Directory URLs - These are the main pages listing all programs
# Each university has URLs for different degree levels
UNIVERSITY_COURSE_DIRECTORIES: Dict[str, Dict[str, str]] = {
    "University of Oxford": {
        "undergraduate": "https://www.ox.ac.uk/admissions/undergraduate/courses/course-listing/",
        "graduate": "https://www.ox.ac.uk/admissions/graduate/courses/courses-a-z-listing/",
        "base_url": "https://www.ox.ac.uk",
        # Matches: /admissions/graduate/courses/msc-advanced-computer-science
        "program_url_pattern": "/admissions/(?:undergraduate|graduate)/courses/(?:msc|ma|mba|mst|mth|dphil|pgdip|pgcert|bm|bcl|ba|bsc)-[a-z0-9-]+"
    },
    "University of Cambridge": {
        "undergraduate": "https://www.undergraduate.study.cam.ac.uk/courses/directory",
        "graduate": "https://www.postgraduate.study.cam.ac.uk/courses/directory",
        "base_url": "https://www.cam.ac.uk",
        # Matches: /courses/directory/cscsmpacs (course codes)
        "program_url_pattern": "/courses/directory/[a-z]{4,}"
    },
    "Imperial College London": {
        "undergraduate": "https://www.imperial.ac.uk/study/courses/undergraduate/",
        "graduate": "https://www.imperial.ac.uk/study/courses/postgraduate-taught/",
        "phd": "https://www.imperial.ac.uk/study/courses/postgraduate-research/",
        "base_url": "https://www.imperial.ac.uk",
        # Matches: /study/courses/postgraduate-taught/2026/advanced-computing/ or /study/courses/postgraduate-taught/computing/
        "program_url_pattern": "/study/courses/(?:undergraduate|postgraduate-taught|postgraduate-research)/(?:\\d{4}/)?[a-z][a-z0-9-]+/?$"
    },
    "UCL": {
        "undergraduate": "https://www.ucl.ac.uk/prospective-students/undergraduate/degrees",
        "graduate": "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees",
        "phd": "https://www.ucl.ac.uk/prospective-students/graduate/research-degrees",
        "base_url": "https://www.ucl.ac.uk",
        # Matches: /prospective-students/graduate/taught-degrees/computer-science-msc
        "program_url_pattern": "/prospective-students/(?:undergraduate|graduate)/(?:degrees|taught-degrees|research-degrees)/[a-z][a-z0-9-]+-(?:msc|ma|mba|phd|mres|bsc|ba|beng)$"
    },
    "University of Edinburgh": {
        "undergraduate": "https://study.ed.ac.uk/programmes/undergraduate-a-z",
        "graduate": "https://study.ed.ac.uk/programmes/postgraduate-taught-a-z",
        "phd": "https://study.ed.ac.uk/programmes/postgraduate-research-a-z",
        "base_url": "https://study.ed.ac.uk",
        # Matches: /programmes/postgraduate-taught/12345-computer-science-msc
        "program_url_pattern": "/programmes/(?:undergraduate|postgraduate-taught|postgraduate-research)/[0-9]+-[a-z0-9-]+"
    },
    "University of Manchester": {
        "undergraduate": "https://www.manchester.ac.uk/study/undergraduate/courses/list/",
        "graduate": "https://www.manchester.ac.uk/study/masters/courses/list/",
        "phd": "https://www.manchester.ac.uk/study/postgraduate-research/programmes/",
        "base_url": "https://www.manchester.ac.uk",
        # Matches: /study/masters/courses/list/02674/msc-advanced-computer-science/
        "program_url_pattern": "/study/(?:undergraduate|masters|postgraduate-research)/(?:courses/list|programmes)/\\d+/[a-z][a-z0-9-]+/?$"
    },
    "King's College London": {
        "undergraduate": "https://www.kcl.ac.uk/study/undergraduate/courses",
        "graduate": "https://www.kcl.ac.uk/study/postgraduate-taught/courses",
        "phd": "https://www.kcl.ac.uk/study/postgraduate-research/courses",
        "base_url": "https://www.kcl.ac.uk",
        # Matches: /study/postgraduate-taught/courses/computer-science-msc
        "program_url_pattern": "/study/(?:undergraduate|postgraduate-taught|postgraduate-research)/courses/[a-z][a-z0-9-]+-(?:msc|ma|phd|bsc|ba|llm|llb|pg|mres)$"
    },
    "University of Glasgow": {
        "undergraduate": "https://www.gla.ac.uk/undergraduate/degrees/",
        "graduate": "https://www.gla.ac.uk/postgraduate/taught/",
        "phd": "https://www.gla.ac.uk/postgraduate/research/",
        "base_url": "https://www.gla.ac.uk",
        # Matches: /postgraduate/taught/computing-science/ or /undergraduate/degrees/computing-science/
        "program_url_pattern": "/(?:undergraduate/degrees|postgraduate/(?:taught|research))/[a-z][a-z0-9-]+/?$"
    },
    "University of Leeds": {
        "undergraduate": "https://courses.leeds.ac.uk/course-search/undergraduate-courses",
        "graduate": "https://courses.leeds.ac.uk/course-search/masters-courses",
        "phd": "https://courses.leeds.ac.uk/course-search/research-degrees",
        "base_url": "https://courses.leeds.ac.uk",
        # Matches: /j702/advanced-computer-science-msc (course code pattern)
        "program_url_pattern": "/[a-z]\\d+/[a-z][a-z0-9-]+$"
    },
    "University of Warwick": {
        "undergraduate": "https://warwick.ac.uk/study/undergraduate/courses/",
        "graduate": "https://warwick.ac.uk/study/postgraduate/courses/",
        "base_url": "https://warwick.ac.uk",
        # Matches: /study/postgraduate/courses/csmscdcs/
        "program_url_pattern": "/study/(?:undergraduate|postgraduate)/courses/[a-z][a-z0-9]+/?$"
    },
    "ETH Zurich": {
        "undergraduate": "https://ethz.ch/en/studies/bachelor/degree-programmes.html",
        "graduate": "https://ethz.ch/en/studies/master/degree-programmes/engineering-sciences.html",
        "graduate_sciences": "https://ethz.ch/en/studies/master/degree-programmes/natural-sciences-and-mathematics.html",
        "graduate_arch": "https://ethz.ch/en/studies/master/degree-programmes/architecture-and-civil-engineering.html",
        "graduate_mgmt": "https://ethz.ch/en/studies/master/degree-programmes/management-and-social-sciences.html",
        "phd": "https://ethz.ch/en/doctorate.html",
        "base_url": "https://ethz.ch",
        # Matches: /studies/master/degree-programmes/engineering-sciences/computer-science.html
        "program_url_pattern": "/studies/(?:master|bachelor)/degree-programmes/[a-z-]+/[a-z][a-z0-9-]+\\.html$"
    },
    "EPFL": {
        "undergraduate": "https://www.epfl.ch/education/bachelor/programs/",
        "graduate": "https://www.epfl.ch/education/master/programs/",
        "phd": "https://www.epfl.ch/education/phd/programs/",
        "base_url": "https://www.epfl.ch",
        # Matches: /education/master/programs/computer-science/
        "program_url_pattern": "/education/(?:bachelor|master|phd)/programs/[a-z][a-z0-9-]+/?$"
    },
    "Technical University of Munich": {
        "all": "https://www.tum.de/en/studies/degree-programs/",
        "base_url": "https://www.tum.de",
        # Matches: /studies/degree-programs/detail/informatics-master-of-science-msc
        "program_url_pattern": "/studies/degree-programs/detail/[a-z][a-z0-9-]+$",
        "pagination": {
            "type": "hash",
            "pattern": "#page={page}",
            "max_pages": 15
        }
    },
    "LMU Munich": {
        "all": "https://www.lmu.de/en/study/all-degrees-and-programs/international-degree-programs/",
        "base_url": "https://www.lmu.de",
        # Matches: LMU Munich program pages (often redirects to uni-muenchen.de)
        "program_url_pattern": "(?:uni-muenchen\\.de|lmu\\.de)/.*(?:studium|study|degree-program|master|bachelor)[^/]*/?$"
    },
    "Heidelberg University": {
        "all": "https://www.uni-heidelberg.de/en/study/all-subjects",
        "base_url": "https://www.uni-heidelberg.de",
        # Matches: /study/all-subjects/computer-science/
        "program_url_pattern": "/study/all-subjects/[a-z][a-z0-9-]+/?$"
    },
    "University of Amsterdam": {
        "undergraduate": "https://www.uva.nl/en/programmes/bachelors/bachelors.html",
        "graduate": "https://www.uva.nl/en/programmes/masters/masters.html",
        "base_url": "https://www.uva.nl",
        # Matches: /programmes/masters/computer-science/computer-science.html
        "program_url_pattern": "/programmes/(?:bachelors|masters)/[a-z][a-z0-9-]+/[a-z][a-z0-9-]+\\.html$"
    },
    "Delft University of Technology": {
        "undergraduate": "https://www.tudelft.nl/en/education/programmes/bachelors",
        "graduate": "https://www.tudelft.nl/en/education/programmes/masters",
        "base_url": "https://www.tudelft.nl",
        # Matches: /education/programmes/masters/computer-science
        "program_url_pattern": "/education/programmes/(?:bachelors|masters)/[a-z][a-z0-9-]+/?$"
    },
    "KU Leuven": {
        "undergraduate": "https://www.kuleuven.be/programmes/bachelors",
        "graduate": "https://www.kuleuven.be/programmes/masters",
        "base_url": "https://www.kuleuven.be",
        # Matches: /programmes/master-computer-science
        "program_url_pattern": "/programmes/(?:bachelor|master)-[a-z][a-z0-9-]+$"
    },
    "Leiden University": {
        "undergraduate": "https://www.universiteitleiden.nl/en/education/study-programmes",
        "graduate": "https://www.universiteitleiden.nl/en/education/study-programmes",
        "studiegids": "https://studiegids.universiteitleiden.nl/en/studies",
        "base_url": "https://www.universiteitleiden.nl",
        # Matches: /education/study-programmes/master/computer-science or /education/study-programmes/bachelor/archaeology
        "program_url_pattern": "/education/study-programmes/(?:bachelor|master)/[a-z][a-z0-9-]+(?:/[a-z][a-z0-9-]+)?$"
    },
    "Utrecht University": {
        "undergraduate": "https://www.uu.nl/en/bachelors/bachelors-programmes",
        "graduate": "https://www.uu.nl/en/masters/masters-programmes",
        "base_url": "https://www.uu.nl",
        # Matches: /masters/computer-science
        "program_url_pattern": "/(?:masters|bachelors)/[a-z][a-z0-9-]+$"
    },
    "Université PSL": {
        "graduate": "https://www.psl.eu/en/education",
        "base_url": "https://www.psl.eu",
        # Matches: /education/master-computer-science
        "program_url_pattern": "/education/(?:master|bachelor|phd)-[a-z][a-z0-9-]+$"
    },
    "University of Tartu": {
        "undergraduate": "https://ut.ee/en/bachelors-programmes",
        "graduate": "https://ut.ee/en/masters-programmes",
        "phd": "https://ut.ee/en/doctoral-programmes",
        "base_url": "https://ut.ee",
        # Matches: /curriculum/computer-science or /en/curriculum/...
        "program_url_pattern": "/(?:en/)?curriculum/[a-z][a-z0-9-]+$"
    },
    "National and Kapodistrian University of Athens": {
        "all": "https://en.uoa.gr/studies/",
        "base_url": "https://en.uoa.gr",
        # Matches: /studies/undergraduate/computer-science/ or /studies/postgraduate/...
        "program_url_pattern": "/studies/(?:undergraduate|postgraduate)/[a-z][a-z0-9-]+/?$"
    }
}

# Legacy: Single program URLs (for backward compatibility)
UNIVERSITY_URLS: Dict[str, str] = {
    # Top Universities - Official Admissions/Program Pages
    "University of Oxford": "https://www.ox.ac.uk/admissions/graduate/courses/msc-advanced-computer-science",
    "University of Cambridge": "https://www.postgraduate.study.cam.ac.uk/courses/directory/cscsmpacs",
    "Imperial College London": "https://www.imperial.ac.uk/study/courses/postgraduate-taught/computing/",
    "ETH Zurich": "https://ethz.ch/en/studies/master/degree-programmes/engineering-sciences/computer-science.html",
    "UCL": "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/computer-science-msc",
    "Université PSL": "https://www.psl.eu/en/education/master-computer-science",
    "Technical University of Munich": "https://www.tum.de/en/studies/degree-programs/detail/informatics-master-of-science-msc",
    "EPFL": "https://www.epfl.ch/education/master/programs/computer-science/",

    # Strong Universities - Official Admissions/Program Pages
    "University of Edinburgh": "https://www.ed.ac.uk/studying/postgraduate/degrees/index.php?r=site/view&edition=2024&id=110",
    "University of Manchester": "https://www.manchester.ac.uk/study/masters/courses/list/02674/msc-advanced-computer-science/",
    "King's College London": "https://www.kcl.ac.uk/study/postgraduate-taught/courses/computer-science-msc",
    "Delft University of Technology": "https://www.tudelft.nl/en/education/programmes/masters/computer-science/msc-computer-science",
    "University of Glasgow": "https://www.gla.ac.uk/postgraduate/taught/computing-science/",
    "University of Leeds": "https://courses.leeds.ac.uk/j702/advanced-computer-science-msc",
    "University of Amsterdam": "https://www.uva.nl/en/programmes/masters/computer-science/computer-science.html",
    "LMU Munich": "https://www.lmu.de/en/study/all-degree-programs/computer-science-master/",
    "University of Warwick": "https://warwick.ac.uk/study/postgraduate/courses/csmscdcs/",
    "Heidelberg University": "https://www.uni-heidelberg.de/en/study/all-subjects/computer-science/computer-science-master",

    # Medium Universities - Official Admissions/Program Pages
    "Utrecht University": "https://www.uu.nl/en/masters/computer-science",
    "University of Tartu": "https://ut.ee/en/curriculum/computer-science",
    "National and Kapodistrian University of Athens": "https://www.di.uoa.gr/en/studies/postgraduate",
    "KU Leuven": "https://www.kuleuven.be/programmes/master-computer-science",
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
Extract detailed information about the academic program from the provided webpage content.
This could be any type of program: Computer Science, Business, Medical, Education, Engineering, Law, Arts, Sciences, etc.
Focus on academic requirements, tuition, deadlines, and program details.

CRITICAL - ENGLISH ONLY OUTPUT:
- ALL extracted text MUST be translated to ENGLISH regardless of the source language
- If the webpage is in German, French, Dutch, Estonian, Greek, Swedish, or any other language, YOU MUST TRANSLATE everything
- Program names should be in English (e.g., "Master of Computer Science" not "Master Informatik")
- Descriptions, prerequisites, specializations - ALL in English
- Do NOT leave any text in the original language
- Use standard English academic terminology

Return a structured JSON object with the following fields:
- university_name: Full university name
- program_name: Complete program name (e.g., "MSc Computer Science", "MBA", "Bachelor of Medicine")
- degree_type: Type of degree - use one of these exact values:
  * For undergraduate: "Bachelor of Science", "Bachelor of Arts", "Bachelor of Engineering", "Bachelor of Medicine"
  * For masters: "Master of Science", "Master of Arts", "Master of Business Administration", "Master of Engineering", "Master of Philosophy"
  * For doctoral: "Doctor of Philosophy", "Doctor of Medicine", "Doctor of Science"
- degree_level: One of "Undergraduate", "Graduate", "Masters", "PhD"
- program_category: Main field/category (e.g., "Computer Science", "Business", "Medical", "Education", "Engineering", "Law", "Arts", "Sciences")
- duration_years: Program duration in years (e.g., 1, 2, 3, 4)
- tuition_fees: Object with domestic_per_year and international_per_year in local currency
- application_deadline: Next deadline in YYYY-MM-DD format or description
- gpa_requirement_min: Minimum GPA required (4.0 scale) or equivalent
- toefl_min: Minimum TOEFL score (if applicable)
- ielts_min: Minimum IELTS score (if applicable)
- prerequisites: List of required courses/degrees/qualifications
- program_description: Detailed program description
- specializations: List of available specializations or tracks
- faculty_research_interests: Key research areas (if applicable)
- career_outcomes: Typical career paths for graduates
- country: Country where university is located
- city: City where university is located

Be as accurate and complete as possible. If information is not available, use null.
Remember: ALL output must be in English, translate any non-English content.
""",
    "program_list_extraction": """
Extract a list of all academic programs/courses from this university webpage.
Look for program names, degree types, and links to individual program pages.

CRITICAL - ENGLISH ONLY OUTPUT:
- ALL program names and descriptions MUST be translated to ENGLISH
- If content is in German, French, Dutch, Estonian, Greek, or any other language - TRANSLATE IT
- Use standard English program names (e.g., "Computer Science" not "Informatik", "Business Administration" not "Betriebswirtschaft")
- Do NOT leave any text in the original language

Return a JSON object with:
- programs: Array of objects, each containing:
  * program_name: Full program name (IN ENGLISH)
  * degree_type: Bachelor/Master/PhD etc.
  * program_category: Field (Computer Science, Business, Medical, etc.)
  * program_url: Link to the detailed program page (if available)
  * department: Department or faculty name (if available, IN ENGLISH)

Focus on finding ALL programs listed on the page across all fields:
- Computer Science, IT, Software Engineering
- Business, MBA, Management, Finance, Accounting
- Medical, Healthcare, Nursing, Pharmacy
- Education, Teaching
- Engineering (all types)
- Law
- Arts & Humanities
- Natural Sciences

Be thorough and extract every program you can find.
""",
    "quality_assessment": """
Assess the quality and completeness of the extracted program data.
Rate each field on a scale of 0-1 for confidence in accuracy.
Calculate overall completeness percentage.
"""
}


# TopUniversities.com Configuration
TOPUNIVERSITIES_CONFIG = {
    "base_url": "https://www.topuniversities.com",
    "urls": {
        "world_rankings": "https://www.topuniversities.com/world-university-rankings",
        "subject_rankings": "https://www.topuniversities.com/university-rankings/university-subject-rankings",
        "by_country": "https://www.topuniversities.com/where-to-study",
        "find_university": "https://www.topuniversities.com/find-your-university"
    },
    "selectors": {
        # Primary selectors (2026 page structure)
        "ranking_list": ".ranking-result-table",
        "ranking_item": "._qs-ranking-data-row.row",
        "ranking_item_card": ".ind-item",  # Quick View cards
        "ranking_position": "._univ-rank .td-wrap-in",
        "ranking_position_card": ".overall-rank-value",  # Quick View
        "university_name": "a.uni-link",
        "location": ".location",
        "overall_score": ".overall-score-span",
        "score_indicator": ".td-wrap-in",
        "pagination": ".pagination",
        "next_page_button": ".page-link.next",
        # Fallback selectors
        "fallback_ranking_item": "[class*='ranking'][class*='row']",
        "fallback_university_name": "a[href*='/universities/']",
        "fallback_score": "[class*='score']",
        # Legacy selectors (for backwards compatibility)
        "load_more_button": "button:has-text('Load More')"
    },
    "rate_limiting": {
        "delay_seconds": 2,
        "max_retries": 3,
        "timeout_seconds": 30
    },
    "subjects": {
        "computer-science": "Computer Science & Information Systems",
        "business": "Business & Management Studies",
        "engineering": "Engineering",
        "medicine": "Medicine",
        "law": "Law & Legal Studies",
        "education": "Education & Training",
        "arts": "Arts & Humanities",
        "sciences": "Natural Sciences"
    }
}


# University Name Mapping for TopUniversities.com
# Maps our internal university names to TopUniversities.com names
UNIVERSITY_NAME_MAPPING = {
    "University of Oxford": "University of Oxford",
    "University of Cambridge": "University of Cambridge",
    "Imperial College London": "Imperial College London",
    "UCL": "UCL (University College London)",
    "University of Edinburgh": "The University of Edinburgh",
    "University of Manchester": "The University of Manchester",
    "King's College London": "King's College London",
    "University of Glasgow": "University of Glasgow",
    "University of Leeds": "University of Leeds",
    "University of Warwick": "University of Warwick",
    "ETH Zurich": "ETH Zurich - Swiss Federal Institute of Technology",
    "EPFL": "EPFL",
    "Technical University of Munich": "Technical University of Munich",
    "LMU Munich": "Ludwig-Maximilians-Universität München",
    "Heidelberg University": "Heidelberg University",
    "University of Amsterdam": "University of Amsterdam",
    "TU Delft": "Delft University of Technology",
    "Utrecht University": "Utrecht University",
    "Leiden University": "Leiden University",
    "KU Leuven": "KU Leuven",
    "Université PSL": "Université PSL",
    "University of Tartu": "University of Tartu",
    "National and Kapodistrian University of Athens": "National and Kapodistrian University of Athens"
}
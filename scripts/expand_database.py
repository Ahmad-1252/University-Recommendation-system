#!/usr/bin/env python
"""
EXPANDED PROGRAM DATABASE
Programmatically generates comprehensive program data for universities
"""

import json
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniversityProgram(BaseModel):
    university_name: str
    program_name: str
    degree_type: str
    faculty_name: Optional[str] = None
    duration: Optional[str] = None
    tuition_fees: Optional[str] = None
    admission_requirements: Optional[str] = None
    language_requirements: Optional[str] = None
    application_deadline: Optional[str] = None
    program_url: str
    country: str
    city: Optional[str] = None
    ranking: Optional[int] = None  # Changed to int, not string
    description: Optional[str] = None
    specializations: Optional[List[str]] = None
    extracted_at: datetime = Field(default_factory=datetime.now)
    confidence_score: float = 0.9

# Comprehensive program database for all universities
UNIVERSITIES_PROGRAMS = {
    'Harvard University': {
        'info': {'country': 'United States', 'city': 'Cambridge', 'ranking': 1, 'url': 'https://www.harvard.edu/'},
        'programs': [
            {'name': 'Computer Science', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['AI', 'Systems', 'Theory'], 'faculty': 'School of Engineering'},
            {'name': 'Business Administration', 'degrees': ['MBA', 'Master'], 'specializations': ['Finance', 'Management', 'Entrepreneurship'], 'faculty': 'Harvard Business School'},
            {'name': 'Law', 'degrees': ['JD', 'LLM'], 'specializations': ['Corporate Law', 'International Law'], 'faculty': 'Harvard Law School'},
            {'name': 'Medicine', 'degrees': ['MD', 'PhD'], 'specializations': ['Surgery', 'Cardiology'], 'faculty': 'Harvard Medical School'},
            {'name': 'Mathematics', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Analysis', 'Algebra', 'Topology'], 'faculty': 'Faculty of Arts & Sciences'},
            {'name': 'Physics', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Quantum', 'Astrophysics'], 'faculty': 'School of Engineering'},
            {'name': 'Chemistry', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Organic', 'Inorganic'], 'faculty': 'Faculty of Arts & Sciences'},
            {'name': 'Biology', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Molecular', 'Cell Biology'], 'faculty': 'Faculty of Arts & Sciences'},
            {'name': 'Economics', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Microeconomics', 'Macroeconomics'], 'faculty': 'Faculty of Arts & Sciences'},
            {'name': 'Psychology', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Cognitive', 'Clinical'], 'faculty': 'Faculty of Arts & Sciences'},
            {'name': 'Environmental Science', 'degrees': ['Master', 'PhD'], 'specializations': ['Climate', 'Conservation'], 'faculty': 'Harvard Graduate School'},
            {'name': 'Public Health', 'degrees': ['MPH', 'Master', 'PhD'], 'specializations': ['Epidemiology', 'Health Policy'], 'faculty': 'Harvard School of Public Health'},
        ]
    },
    'Stanford University': {
        'info': {'country': 'United States', 'city': 'Palo Alto', 'ranking': 2, 'url': 'https://www.stanford.edu/'},
        'programs': [
            {'name': 'Computer Science', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['AI', 'Machine Learning', 'HCI'], 'faculty': 'School of Engineering'},
            {'name': 'Data Science', 'degrees': ['Master', 'PhD'], 'specializations': ['Analytics', 'Statistics'], 'faculty': 'School of Engineering'},
            {'name': 'Business Administration', 'degrees': ['MBA'], 'specializations': ['Strategy', 'Finance'], 'faculty': 'Stanford Business School'},
            {'name': 'Electrical Engineering', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Signal Processing', 'Controls'], 'faculty': 'School of Engineering'},
            {'name': 'Civil Engineering', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Structural', 'Transportation'], 'faculty': 'School of Engineering'},
            {'name': 'Mechanical Engineering', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Robotics', 'Dynamics'], 'faculty': 'School of Engineering'},
            {'name': 'Chemical Engineering', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Process', 'Materials'], 'faculty': 'School of Engineering'},
            {'name': 'Physics', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Particle Physics', 'Quantum'], 'faculty': 'School of Humanities & Sciences'},
            {'name': 'Economics', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['International', 'Labor'], 'faculty': 'School of Humanities & Sciences'},
            {'name': 'Psychology', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Organizational', 'Cognitive'], 'faculty': 'School of Humanities & Sciences'},
            {'name': 'Biology', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Genetics', 'Neurobiology'], 'faculty': 'School of Humanities & Sciences'},
            {'name': 'Environmental Science', 'degrees': ['Master', 'PhD'], 'specializations': ['Sustainability', 'Climate'], 'faculty': 'School of Earth'},
        ]
    },
    'MIT': {
        'info': {'country': 'United States', 'city': 'Cambridge', 'ranking': 3, 'url': 'https://www.mit.edu/'},
        'programs': [
            {'name': 'Computer Science', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['AI', 'Cryptography', 'Theory'], 'faculty': 'School of Engineering'},
            {'name': 'Electrical Engineering', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Electronics', 'Power'], 'faculty': 'School of Engineering'},
            {'name': 'Mechanical Engineering', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Controls', 'Biomechanics'], 'faculty': 'School of Engineering'},
            {'name': 'Aeronautical Engineering', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Aerospace', 'Propulsion'], 'faculty': 'School of Engineering'},
            {'name': 'Chemical Engineering', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Biomedical', 'Environmental'], 'faculty': 'School of Engineering'},
            {'name': 'Nuclear Science & Engineering', 'degrees': ['Master', 'PhD'], 'specializations': ['Reactor', 'Plasma'], 'faculty': 'School of Engineering'},
            {'name': 'Materials Science', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Polymers', 'Semiconductors'], 'faculty': 'School of Engineering'},
            {'name': 'Physics', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Quantum', 'Condensed Matter'], 'faculty': 'School of Science'},
            {'name': 'Mathematics', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Applied', 'Pure'], 'faculty': 'School of Science'},
            {'name': 'Chemistry', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Organic', 'Physical'], 'faculty': 'School of Science'},
            {'name': 'Biology', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Molecular', 'Systems'], 'faculty': 'School of Science'},
            {'name': 'Neuroscience', 'degrees': ['Master', 'PhD'], 'specializations': ['Cognitive', 'Neural'], 'faculty': 'School of Science'},
            {'name': 'Economics', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Econometrics', 'Development'], 'faculty': 'Sloan School of Management'},
            {'name': 'Management', 'degrees': ['MBA', 'Master'], 'specializations': ['Entrepreneurship', 'Finance'], 'faculty': 'Sloan School of Management'},
        ]
    },
    'University of Cambridge': {
        'info': {'country': 'United Kingdom', 'city': 'Cambridge', 'ranking': 4, 'url': 'https://www.cam.ac.uk/'},
        'programs': [
            {'name': 'Engineering', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Civil', 'Mechanical', 'Electrical'], 'faculty': 'Engineering'},
            {'name': 'Mathematics', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Pure', 'Applied'], 'faculty': 'Mathematics'},
            {'name': 'Physics', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Theoretical', 'Experimental'], 'faculty': 'Physics'},
            {'name': 'Chemistry', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Organic', 'Biochemistry'], 'faculty': 'Chemistry'},
            {'name': 'Natural Sciences', 'degrees': ['Bachelor'], 'specializations': ['Biology', 'Geology'], 'faculty': 'Natural Sciences'},
            {'name': 'Law', 'degrees': ['Bachelor', 'LLM'], 'specializations': ['Constitutional', 'Commercial'], 'faculty': 'Law'},
            {'name': 'Medicine', 'degrees': ['BA', 'MB', 'MD'], 'specializations': ['Surgery', 'Pediatrics'], 'faculty': 'Medicine'},
            {'name': 'Theology', 'degrees': ['Bachelor', 'Master'], 'specializations': ['Biblical', 'Systematic'], 'faculty': 'Theology'},
            {'name': 'Economics', 'degrees': ['Bachelor', 'Master'], 'specializations': ['Macroeconomics', 'Microeconomics'], 'faculty': 'Economics'},
            {'name': 'Geography', 'degrees': ['Bachelor', 'Master'], 'specializations': ['Human', 'Physical'], 'faculty': 'Geography'},
            {'name': 'History', 'degrees': ['Bachelor', 'Master'], 'specializations': ['Medieval', 'Modern'], 'faculty': 'History'},
            {'name': 'Philosophy', 'degrees': ['Bachelor', 'Master'], 'specializations': ['Metaphysics', 'Ethics'], 'faculty': 'Philosophy'},
        ]
    },
    'University of Oxford': {
        'info': {'country': 'United Kingdom', 'city': 'Oxford', 'ranking': 5, 'url': 'https://www.ox.ac.uk/'},
        'programs': [
            {'name': 'Philosophy, Politics & Economics', 'degrees': ['Bachelor', 'Master'], 'specializations': ['Political Theory', 'Micro'], 'faculty': 'Social Sciences'},
            {'name': 'Classics', 'degrees': ['Bachelor', 'Master'], 'specializations': ['Greek', 'Latin'], 'faculty': 'Humanities'},
            {'name': 'English Language & Literature', 'degrees': ['Bachelor', 'Master'], 'specializations': ['Medieval', 'Modern'], 'faculty': 'Humanities'},
            {'name': 'History', 'degrees': ['Bachelor', 'Master'], 'specializations': ['Ancient', 'British'], 'faculty': 'Humanities'},
            {'name': 'Mathematics', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Pure', 'Applied'], 'faculty': 'Mathematical Sciences'},
            {'name': 'Physics', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Quantum', 'Astrophysics'], 'faculty': 'Mathematical Sciences'},
            {'name': 'Chemistry', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Inorganic', 'Physical'], 'faculty': 'Mathematical Sciences'},
            {'name': 'Biology', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Molecular', 'Ecology'], 'faculty': 'Mathematical Sciences'},
            {'name': 'Medicine', 'degrees': ['MB', 'MD'], 'specializations': ['Surgery', 'Medicine'], 'faculty': 'Medical Sciences'},
            {'name': 'Law', 'degrees': ['BA', 'BCL', 'LLM'], 'specializations': ['Human Rights', 'Commercial'], 'faculty': 'Law'},
            {'name': 'Economics', 'degrees': ['Bachelor', 'Master'], 'specializations': ['Development', 'Finance'], 'faculty': 'Social Sciences'},
            {'name': 'Management', 'degrees': ['MBA', 'Master'], 'specializations': ['Strategy', 'Operations'], 'faculty': 'Oxford Saïd'},
        ]
    },
    'Imperial College London': {
        'info': {'country': 'United Kingdom', 'city': 'London', 'ranking': 6, 'url': 'https://www.imperial.ac.uk/'},
        'programs': [
            {'name': 'Aeronautical Engineering', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Flight', 'Structures'], 'faculty': 'Engineering'},
            {'name': 'Chemical Engineering', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Biochemical', 'Sustainable'], 'faculty': 'Engineering'},
            {'name': 'Civil Engineering', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Structural', 'Infrastructure'], 'faculty': 'Engineering'},
            {'name': 'Electrical & Electronic Engineering', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Power', 'Communications'], 'faculty': 'Engineering'},
            {'name': 'Mechanical Engineering', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Design', 'Manufacturing'], 'faculty': 'Engineering'},
            {'name': 'Computing', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['AI', 'Networks', 'Security'], 'faculty': 'Engineering'},
            {'name': 'Physics', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Particle', 'Photonics'], 'faculty': 'Natural Sciences'},
            {'name': 'Chemistry', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Materials', 'Catalysis'], 'faculty': 'Natural Sciences'},
            {'name': 'Mathematics', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Statistics', 'Optimization'], 'faculty': 'Natural Sciences'},
            {'name': 'Biology', 'degrees': ['Bachelor', 'Master', 'PhD'], 'specializations': ['Molecular', 'Biotechnology'], 'faculty': 'Natural Sciences'},
            {'name': 'Business Administration', 'degrees': ['MBA', 'Master'], 'specializations': ['Finance', 'Entrepreneurship'], 'faculty': 'Business School'},
        ]
    },
}

def expand_program_data():
    """Generate expanded program database"""
    
    mongo_client = MongoClient('mongodb://localhost:27017/')
    db = mongo_client['university_scraper']
    collection = db['programs']
    
    logger.info("Expanding program database...")
    
    all_programs = []
    total_saved = 0
    
    for uni_name, uni_data in UNIVERSITIES_PROGRAMS.items():
        logger.info(f"\nProcessing: {uni_name}")
        
        info = uni_data['info']
        programs_list = uni_data['programs']
        
        for prog in programs_list:
            for degree in prog['degrees']:
                try:
                    program = UniversityProgram(
                        university_name=uni_name,
                        program_name=prog['name'],
                        degree_type=degree,
                        faculty_name=prog['faculty'],
                        duration='1-4 years',
                        admission_requirements='Bachelor degree',
                        language_requirements='English',
                        application_deadline='Rolling admission',
                        program_url=info['url'],
                        country=info['country'],
                        city=info['city'],
                        ranking=info['ranking'],
                        description=f"{prog['name']} ({degree}) at {uni_name}",
                        specializations=prog['specializations'],
                        confidence_score=0.95
                    )
                    
                    # Save to MongoDB with upsert
                    result = collection.update_one(
                        {
                            'university_name': program.university_name,
                            'program_name': program.program_name,
                            'degree_type': program.degree_type
                        },
                        {'$set': program.dict()},
                        upsert=True
                    )
                    
                    if result.upserted_id or result.modified_count:
                        total_saved += 1
                        all_programs.append(program)
                    
                except Exception as e:
                    logger.error(f"Error saving program: {e}")
    
    logger.info("\n" + "=" * 80)
    logger.info("DATABASE EXPANSION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total programs created: {total_saved}")
    logger.info(f"Total unique universities: {len(UNIVERSITIES_PROGRAMS)}")
    
    # Statistics
    degree_counts = {}
    for prog in all_programs:
        degree = prog.degree_type
        degree_counts[degree] = degree_counts.get(degree, 0) + 1
    
    logger.info("\nPrograms by degree type:")
    for degree, count in sorted(degree_counts.items()):
        logger.info(f"  {degree}: {count}")
    
    return all_programs

if __name__ == "__main__":
    programs = expand_program_data()
    print(f"\n✅ Successfully expanded database with {len(programs)} program records!")
    print(f"Database: university_scraper.programs")

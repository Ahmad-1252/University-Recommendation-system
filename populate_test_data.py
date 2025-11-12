"""
Populate test data based on the last successful scraper run
"""

import json
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Sample programs extracted from the scraper logs
test_programs = [
    {
        "university_name": "Harvard University",
        "program_name": "Computer Science",
        "degree_type": "Master",
        "duration": "2 years",
        "tuition_fees": "$60,000 per year",
        "admission_requirements": "Bachelor's degree",
        "language_requirements": "English",
        "application_deadline": "December 15",
        "program_url": "https://www.harvard.edu/academics/",
        "country": "United States",
        "city": "Cambridge",
        "ranking": "1",
        "description": "Advanced computer science program",
        "extracted_at": datetime.now(),
        "confidence_score": 0.95
    },
    {
        "university_name": "Harvard University",
        "program_name": "Business Administration",
        "degree_type": "MBA",
        "duration": "2 years",
        "tuition_fees": "$73,440 per year",
        "admission_requirements": "Bachelor's degree",
        "language_requirements": "English",
        "application_deadline": "March 31",
        "program_url": "https://www.harvard.edu/academics/",
        "country": "United States",
        "city": "Boston",
        "ranking": "1",
        "description": "Harvard Business School MBA",
        "extracted_at": datetime.now(),
        "confidence_score": 0.98
    },
    {
        "university_name": "Stanford University",
        "program_name": "Artificial Intelligence",
        "degree_type": "Master",
        "duration": "2 years",
        "tuition_fees": "$57,693 per year",
        "admission_requirements": "Bachelor's degree in relevant field",
        "language_requirements": "English",
        "application_deadline": "December 1",
        "program_url": "https://www.stanford.edu/academics/",
        "country": "United States",
        "city": "Palo Alto",
        "ranking": "2",
        "description": "MS in Computer Science with AI specialization",
        "extracted_at": datetime.now(),
        "confidence_score": 0.94
    },
    {
        "university_name": "University of Cambridge",
        "program_name": "Engineering",
        "degree_type": "Bachelor",
        "duration": "3 years",
        "tuition_fees": "£22,200 per year",
        "admission_requirements": "A-levels",
        "language_requirements": "English",
        "application_deadline": "October 15",
        "program_url": "https://www.cam.ac.uk/",
        "country": "United Kingdom",
        "city": "Cambridge",
        "ranking": "3",
        "description": "Natural Sciences and Engineering",
        "extracted_at": datetime.now(),
        "confidence_score": 0.92
    },
    {
        "university_name": "University of Cambridge",
        "program_name": "Mathematics",
        "degree_type": "Bachelor",
        "duration": "3 years",
        "tuition_fees": "£22,200 per year",
        "admission_requirements": "A-levels",
        "language_requirements": "English",
        "application_deadline": "October 15",
        "program_url": "https://www.cam.ac.uk/",
        "country": "United Kingdom",
        "city": "Cambridge",
        "ranking": "3",
        "description": "Mathematics program",
        "extracted_at": datetime.now(),
        "confidence_score": 0.91
    },
    {
        "university_name": "University of Oxford",
        "program_name": "Philosophy",
        "degree_type": "Bachelor",
        "duration": "3 years",
        "tuition_fees": "£22,200 per year",
        "admission_requirements": "A-levels",
        "language_requirements": "English",
        "application_deadline": "October 15",
        "program_url": "https://www.ox.ac.uk/",
        "country": "United Kingdom",
        "city": "Oxford",
        "ranking": "4",
        "description": "Philosophy, Politics and Economics",
        "extracted_at": datetime.now(),
        "confidence_score": 0.90
    },
    {
        "university_name": "Imperial College London",
        "program_name": "Physics",
        "degree_type": "Master",
        "duration": "1 year",
        "tuition_fees": "£24,000 per year",
        "admission_requirements": "Bachelor's degree in Physics",
        "language_requirements": "English",
        "application_deadline": "April 30",
        "program_url": "https://www.imperial.ac.uk/",
        "country": "United Kingdom",
        "city": "London",
        "ranking": "5",
        "description": "Advanced Physics MSc",
        "extracted_at": datetime.now(),
        "confidence_score": 0.93
    },
    {
        "university_name": "ETH Zurich",
        "program_name": "Civil Engineering",
        "degree_type": "Master",
        "duration": "2 years",
        "tuition_fees": "CHF 730 per year",
        "admission_requirements": "Bachelor's degree in Engineering",
        "language_requirements": "English/German",
        "application_deadline": "December 15",
        "program_url": "https://www.ethz.ch/",
        "country": "Switzerland",
        "city": "Zurich",
        "ranking": "9",
        "description": "Civil Engineering Master's program",
        "extracted_at": datetime.now(),
        "confidence_score": 0.96
    },
    {
        "university_name": "Technical University of Munich",
        "program_name": "Electrical Engineering",
        "degree_type": "Master",
        "duration": "2 years",
        "tuition_fees": "€0 per year",
        "admission_requirements": "Bachelor's degree in Engineering",
        "language_requirements": "German/English",
        "application_deadline": "January 15",
        "program_url": "https://www.tum.de/",
        "country": "Germany",
        "city": "Munich",
        "ranking": "45",
        "description": "Electrical Engineering MSc",
        "extracted_at": datetime.now(),
        "confidence_score": 0.88
    },
    {
        "university_name": "University of Toronto",
        "program_name": "Computer Science",
        "degree_type": "Master",
        "duration": "2 years",
        "tuition_fees": "CAD 6,700 per year",
        "admission_requirements": "Bachelor's degree",
        "language_requirements": "English",
        "application_deadline": "February 1",
        "program_url": "https://www.utoronto.ca/",
        "country": "Canada",
        "city": "Toronto",
        "ranking": "20",
        "description": "Master of Science in Computer Science",
        "extracted_at": datetime.now(),
        "confidence_score": 0.89
    },
    {
        "university_name": "University of British Columbia",
        "program_name": "Environmental Science",
        "degree_type": "Master",
        "duration": "2 years",
        "tuition_fees": "CAD 7,200 per year",
        "admission_requirements": "Bachelor's degree in relevant field",
        "language_requirements": "English",
        "application_deadline": "January 15",
        "program_url": "https://www.ubc.ca/",
        "country": "Canada",
        "city": "Vancouver",
        "ranking": "34",
        "description": "Environmental Science Graduate Program",
        "extracted_at": datetime.now(),
        "confidence_score": 0.87
    },
    {
        "university_name": "Australian National University",
        "program_name": "Physics",
        "degree_type": "Master",
        "duration": "2 years",
        "tuition_fees": "AUD 40,000 per year",
        "admission_requirements": "Bachelor's degree in Physics",
        "language_requirements": "English",
        "application_deadline": "June 1",
        "program_url": "https://www.anu.edu.au/",
        "country": "Australia",
        "city": "Canberra",
        "ranking": "54",
        "description": "Master of Advanced Science in Physics",
        "extracted_at": datetime.now(),
        "confidence_score": 0.85
    },
    {
        "university_name": "University of Melbourne",
        "program_name": "Business",
        "degree_type": "MBA",
        "duration": "2 years",
        "tuition_fees": "AUD 110,000 per year",
        "admission_requirements": "Bachelor's degree and work experience",
        "language_requirements": "English",
        "application_deadline": "July 1",
        "program_url": "https://www.unimelb.edu.au/",
        "country": "Australia",
        "city": "Melbourne",
        "ranking": "46",
        "description": "Melbourne MBA",
        "extracted_at": datetime.now(),
        "confidence_score": 0.92
    },
    {
        "university_name": "Peking University",
        "program_name": "Economics",
        "degree_type": "Master",
        "duration": "2 years",
        "tuition_fees": "CNY 48,000 per year",
        "admission_requirements": "Bachelor's degree",
        "language_requirements": "Chinese/English",
        "application_deadline": "March 31",
        "program_url": "https://www.pku.edu.cn/",
        "country": "China",
        "city": "Beijing",
        "ranking": "49",
        "description": "Master of Economics",
        "extracted_at": datetime.now(),
        "confidence_score": 0.84
    },
    {
        "university_name": "Tsinghua University",
        "program_name": "Computer Science",
        "degree_type": "Master",
        "duration": "3 years",
        "tuition_fees": "CNY 50,000 per year",
        "admission_requirements": "Bachelor's degree in CS",
        "language_requirements": "Chinese/English",
        "application_deadline": "April 15",
        "program_url": "https://www.tsinghua.edu.cn/",
        "country": "China",
        "city": "Beijing",
        "ranking": "50",
        "description": "Master of Science in Computer Science",
        "extracted_at": datetime.now(),
        "confidence_score": 0.86
    }
]

def populate_test_data():
    """Insert test data into MongoDB"""
    try:
        mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Verify connection
        client.admin.command('ping')
        print("[OK] MongoDB connection established")
        
        db = client['university_scraper']
        collection = db['programs']
        
        # Clear existing data
        collection.delete_many({})
        print(f"[OK] Cleared existing data")
        
        # Insert test data
        result = collection.insert_many(test_programs)
        print(f"[OK] Inserted {len(result.inserted_ids)} programs into database")
        
        # Verify insertion
        count = collection.count_documents({})
        print(f"[OK] Total programs in database: {count}")
        
        # Show distribution by university
        print(f"\n[OK] Programs by university:")
        universities = collection.distinct('university_name')
        for uni in sorted(universities):
            count = collection.count_documents({'university_name': uni})
            print(f"  - {uni}: {count} programs")
        
        client.close()
        print(f"\n[OK] Test data population completed successfully")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to populate test data: {e}")
        return False

if __name__ == "__main__":
    populate_test_data()

#!/usr/bin/env python
"""
COMPREHENSIVE UNIVERSITY PROGRAM SCRAPER
Extracts ALL programs from universities (Bachelor, Master, PhD, etc.)
Uses Groq LLM for intelligent extraction
"""

import asyncio
import requests
from bs4 import BeautifulSoup
from groq import Groq
import pymongo
from pymongo import MongoClient
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from tqdm import tqdm
import logging
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('comprehensive_scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class UniversityProgram(BaseModel):
    """Data model for university program"""
    university_name: str
    program_name: str
    degree_type: str  # Bachelor, Master, PhD, Certificate, Diploma, etc.
    faculty_name: Optional[str] = None
    duration: Optional[str] = None
    tuition_fees: Optional[str] = None
    admission_requirements: Optional[str] = None
    language_requirements: Optional[str] = None
    application_deadline: Optional[str] = None
    program_url: str
    country: str
    city: Optional[str] = None
    ranking: Optional[str] = None
    description: Optional[str] = None
    specializations: Optional[List[str]] = None  # NEW: Track specializations
    extracted_at: datetime = Field(default_factory=datetime.now)
    confidence_score: float = 0.0

class ComprehensiveScraper:
    """Enhanced scraper to get ALL programs from universities"""
    
    def __init__(self):
        self.client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        self.mongo_client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
        self.db = self.mongo_client['university_scraper']
        self.collection = self.db['programs']
        
        # Universities with comprehensive data
        self.universities = {
            'Harvard University': {
                'url': 'https://www.harvard.edu/academics/',
                'country': 'United States',
                'city': 'Cambridge',
                'ranking': 1
            },
            'Stanford University': {
                'url': 'https://www.stanford.edu/academics/',
                'country': 'United States',
                'city': 'Palo Alto',
                'ranking': 2
            },
            'MIT': {
                'url': 'https://www.mit.edu/academics/',
                'country': 'United States',
                'city': 'Cambridge',
                'ranking': 3
            },
            'University of Cambridge': {
                'url': 'https://www.cam.ac.uk/study-at-cambridge',
                'country': 'United Kingdom',
                'city': 'Cambridge',
                'ranking': 4
            },
            'University of Oxford': {
                'url': 'https://www.ox.ac.uk/students',
                'country': 'United Kingdom',
                'city': 'Oxford',
                'ranking': 5
            },
            'University College London': {
                'url': 'https://www.ucl.ac.uk/prospective-students',
                'country': 'United Kingdom',
                'city': 'London',
                'ranking': 8
            },
            'Imperial College London': {
                'url': 'https://www.imperial.ac.uk/study/',
                'country': 'United Kingdom',
                'city': 'London',
                'ranking': 6
            },
            'ETH Zurich': {
                'url': 'https://www.ethz.ch/en/studies.html',
                'country': 'Switzerland',
                'city': 'Zurich',
                'ranking': 9
            },
            'Technical University of Munich': {
                'url': 'https://www.tum.de/en/studies/',
                'country': 'Germany',
                'city': 'Munich',
                'ranking': 45
            },
            'University of Toronto': {
                'url': 'https://www.utoronto.ca/academics',
                'country': 'Canada',
                'city': 'Toronto',
                'ranking': 20
            },
            'McGill University': {
                'url': 'https://www.mcgill.ca/study/',
                'country': 'Canada',
                'city': 'Montreal',
                'ranking': 30
            },
            'University of British Columbia': {
                'url': 'https://www.ubc.ca/academics/',
                'country': 'Canada',
                'city': 'Vancouver',
                'ranking': 34
            },
            'Australian National University': {
                'url': 'https://www.anu.edu.au/study',
                'country': 'Australia',
                'city': 'Canberra',
                'ranking': 54
            },
            'University of Melbourne': {
                'url': 'https://study.unimelb.edu.au/',
                'country': 'Australia',
                'city': 'Melbourne',
                'ranking': 46
            },
            'University of Sydney': {
                'url': 'https://www.sydney.edu.au/study/',
                'country': 'Australia',
                'city': 'Sydney',
                'ranking': 60
            },
            'National University of Singapore': {
                'url': 'https://www.nus.edu.sg/education',
                'country': 'Singapore',
                'city': 'Singapore',
                'ranking': 11
            },
            'University of Hong Kong': {
                'url': 'https://www.hku.hk/academics',
                'country': 'Hong Kong',
                'city': 'Hong Kong',
                'ranking': 22
            },
            'Peking University': {
                'url': 'https://www.pku.edu.cn/',
                'country': 'China',
                'city': 'Beijing',
                'ranking': 49
            },
            'Tsinghua University': {
                'url': 'https://www.tsinghua.edu.cn/en/',
                'country': 'China',
                'city': 'Beijing',
                'ranking': 50
            },
            'Tokyo University': {
                'url': 'https://www.u-tokyo.ac.jp/en/',
                'country': 'Japan',
                'city': 'Tokyo',
                'ranking': 47
            },
            'University of Seoul': {
                'url': 'https://www.uos.ac.kr/en/Main.do',
                'country': 'South Korea',
                'city': 'Seoul',
                'ranking': 70
            }
        }

    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch webpage with retry logic"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        for attempt in range(3):
            try:
                response = requests.get(url, timeout=15, headers=headers)
                if response.status_code == 200:
                    return response.content
                logger.warning(f"Attempt {attempt+1}: HTTP {response.status_code} for {url}")
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt+1} failed: {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt)
        
        return None

    def extract_programs_with_llm(self, html_content: str, university_name: str, url: str) -> List[Dict]:
        """Use Groq LLM to extract ALL programs from HTML"""
        
        # Create text from HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text()
        text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
        
        # Limit text length for LLM
        text = text[:4000]
        
        prompt = f"""Extract ALL academic programs from this university website.
Return ONLY a JSON array with NO other text, NO markdown, NO explanation.

University: {university_name}

Website text excerpt:
{text}

REQUIREMENTS:
1. Extract EVERY program: Bachelor, Master, PhD, Certificate, MBA, etc.
2. Include all specializations and concentrations
3. Return ONLY valid JSON array
4. Each item must have: program_name, degree_type, confidence (0-1)
5. Optional: faculty_name, description, specializations

Example format:
[{{"program_name":"Computer Science","degree_type":"Bachelor","confidence":0.95}},{{"program_name":"MBA","degree_type":"Master","confidence":0.93}}]

NOW EXTRACT ALL PROGRAMS AS VALID JSON ARRAY ONLY:"""
        
        try:
            message = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_text = message.choices[0].message.content.strip()
            
            # Clean response if it has markdown code blocks
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
            response_text = response_text.strip()
            
            # Try to parse JSON
            try:
                programs = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                start_idx = response_text.find('[')
                end_idx = response_text.rfind(']') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    programs = json.loads(json_str)
                else:
                    logger.error(f"Could not find JSON in response for {university_name}")
                    return []
            
            logger.info(f"Extracted {len(programs)} programs from {university_name}")
            return programs
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error for {university_name}: {e}")
            logger.debug(f"Response was: {response_text[:500]}")
            return []
        except Exception as e:
            logger.error(f"LLM extraction error for {university_name}: {e}")
            return []

    def process_university(self, uni_name: str, uni_data: Dict) -> List[UniversityProgram]:
        """Process one university and extract all programs"""
        
        logger.info(f"\nProcessing: {uni_name}")
        
        # Fetch page
        html = self.fetch_page(uni_data['url'])
        if not html:
            logger.error(f"Failed to fetch {uni_name}")
            return []
        
        # Extract programs using LLM
        programs = self.extract_programs_with_llm(html, uni_name, uni_data['url'])
        
        if not programs:
            logger.warning(f"No programs extracted from {uni_name}")
            return []
        
        # Convert to UniversityProgram objects
        uni_programs = []
        for prog in programs:
            try:
                program = UniversityProgram(
                    university_name=uni_name,
                    program_name=prog.get('program_name', 'Unknown'),
                    degree_type=prog.get('degree_type', 'Unknown'),
                    faculty_name=prog.get('faculty_name'),
                    description=prog.get('description'),
                    specializations=prog.get('specializations'),
                    program_url=uni_data['url'],
                    country=uni_data['country'],
                    city=uni_data['city'],
                    ranking=uni_data['ranking'],
                    confidence_score=prog.get('confidence', 0.8)
                )
                uni_programs.append(program)
            except Exception as e:
                logger.error(f"Error creating program object: {e}")
                continue
        
        logger.info(f"Created {len(uni_programs)} program objects for {uni_name}")
        return uni_programs

    def save_to_mongodb(self, programs: List[UniversityProgram]) -> int:
        """Save programs to MongoDB with upsert logic"""
        
        saved_count = 0
        
        for program in programs:
            try:
                # Upsert: update if exists, insert if not
                result = self.collection.update_one(
                    {
                        'university_name': program.university_name,
                        'program_name': program.program_name,
                        'degree_type': program.degree_type
                    },
                    {
                        '$set': program.dict()
                    },
                    upsert=True
                )
                
                if result.upserted_id or result.modified_count:
                    saved_count += 1
                    
            except Exception as e:
                logger.error(f"Error saving program: {e}")
        
        return saved_count

    def run(self):
        """Main scraping process"""
        
        logger.info("=" * 80)
        logger.info("COMPREHENSIVE UNIVERSITY PROGRAM SCRAPER")
        logger.info("=" * 80)
        logger.info(f"Total universities: {len(self.universities)}")
        
        all_programs = []
        total_saved = 0
        
        for uni_name in tqdm(self.universities, desc="Processing universities"):
            try:
                uni_data = self.universities[uni_name]
                programs = self.process_university(uni_name, uni_data)
                all_programs.extend(programs)
                
                # Save to MongoDB
                saved = self.save_to_mongodb(programs)
                total_saved += saved
                
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing {uni_name}: {e}")
                continue
        
        # Print summary
        logger.info("\n" + "=" * 80)
        logger.info("SCRAPING SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total programs extracted: {len(all_programs)}")
        logger.info(f"Total programs saved to MongoDB: {total_saved}")
        logger.info(f"Unique universities: {len(set(p.university_name for p in all_programs))}")
        
        # Count by degree type
        degree_counts = {}
        for prog in all_programs:
            degree = prog.degree_type
            degree_counts[degree] = degree_counts.get(degree, 0) + 1
        
        logger.info("\nPrograms by degree type:")
        for degree, count in sorted(degree_counts.items()):
            logger.info(f"  {degree}: {count}")
        
        return all_programs


if __name__ == "__main__":
    scraper = ComprehensiveScraper()
    programs = scraper.run()
    
    print("\n" + "=" * 80)
    print("COMPREHENSIVE SCRAPING COMPLETE!")
    print("=" * 80)
    print(f"Total programs: {len(programs)}")
    print(f"Database: university_scraper.programs")
    print("=" * 80)

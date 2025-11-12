import asyncio
import requests
from bs4 import BeautifulSoup
from groq import Groq
import pymongo
from pymongo import MongoClient
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import tqdm
import aiohttp
import tenacity
import json
import logging
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class UniversityProgram(BaseModel):
    university_name: str = Field(..., description="Name of the university")
    program_name: str = Field(..., description="Name of the academic program")
    degree_type: str = Field(..., description="Type of degree (Bachelor, Master, PhD, etc.)")
    duration: Optional[str] = Field(None, description="Duration of the program")
    tuition_fees: Optional[str] = Field(None, description="Tuition fees information")
    admission_requirements: Optional[str] = Field(None, description="Admission requirements")
    language_requirements: Optional[str] = Field(None, description="Language proficiency requirements")
    application_deadline: Optional[str] = Field(None, description="Application deadline")
    program_url: str = Field(..., description="URL of the program page")
    country: str = Field(..., description="Country where the university is located")
    city: Optional[str] = Field(None, description="City where the university is located")
    ranking: Optional[str] = Field(None, description="University ranking information")
    description: Optional[str] = Field(None, description="Program description")
    extracted_at: datetime = Field(default_factory=datetime.now)
    confidence_score: float = Field(default=0.0, description="Confidence score of the extraction")
    field: Optional[str] = Field(None, description="The academic field or department, e.g., 'Engineering', 'Computer Science'")

class EnhancedUniversityScraper:
    def __init__(self):
        self.client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        self.mongo_client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
        self.db = self.mongo_client['university_scraper']
        self.collection = self.db['programs']
        self.processed_urls = set() # Keep track of processed URLs to avoid duplicates

        # University URLs to scrape
        self.universities = {
            'Harvard University': ('https://www.harvard.edu/academics/', 'United States'),
            'Stanford University': ('https://www.stanford.edu/academics/', 'United States'),
            'MIT': ('https://www.mit.edu/academics/', 'United States'),
            'University of Cambridge': ('https://www.cam.ac.uk/study-at-cambridge', 'United Kingdom'),
            'University of Oxford': ('https://www.ox.ac.uk/students', 'United Kingdom'),
            'University College London': ('https://www.ucl.ac.uk/prospective-students', 'United Kingdom'),
            'Imperial College London': ('https://www.imperial.ac.uk/study/', 'United Kingdom'),
            'ETH Zurich': ('https://ethz.ch/en/studies.html', 'Switzerland'),
            'EPFL': ('https://www.epfl.ch/education/studies/en/', 'Switzerland'),
            'Technical University of Munich': ('https://www.tum.de/en/studies/', 'Germany'),
            'University of Toronto': ('https://www.utoronto.ca/academics', 'Canada'),
            'McGill University': ('https://www.mcgill.ca/study/', 'Canada'),
            'University of British Columbia': ('https://www.ubc.ca/academics/', 'Canada'),
            'Australian National University': ('https://www.anu.edu.au/study', 'Australia'),
            'University of Melbourne': ('https://study.unimelb.edu.au/', 'Australia'),
            'University of Sydney': ('https://www.sydney.edu.au/study/', 'Australia'),
            'National University of Singapore': ('https://www.nus.edu.sg/education', 'Singapore'),
            'University of Hong Kong': ('https://www.hku.hk/academics', 'Hong Kong'),
            'Peking University': ('https://en.pku.edu.cn/academics.html', 'China'),
            'Tsinghua University': ('https://www.tsinghua.edu.cn/en/academics.html', 'China'),
            'Carnegie Mellon University': ('https://www.cmu.edu/academics/index.html', 'United States')
        }

    async def _discover_program_links(self, university_name: str, base_url: str) -> List[str]:
        """Stage 1: Discover potential program page URLs from a base URL."""
        logger.info(f"[{university_name}] Stage 1: Discovering program links from {base_url}")
        try:
            async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
                async with session.get(base_url, timeout=30) as response:
                    if response.status != 200:
                        logger.warning(f"[{university_name}] Failed to fetch base URL {base_url}: HTTP {response.status}")
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    links = set()
                    for a_tag in soup.find_all('a', href=True):
                        href = a_tag['href']
                        # Create absolute URL
                        full_url = requests.compat.urljoin(base_url, href)
                        
                        # Simple filter to find likely program pages
                        if any(keyword in full_url.lower() for keyword in ['program', 'course', 'degree', 'major', 'subject', 'department']):
                            if full_url not in self.processed_urls:
                                links.add(full_url)
                    
                    logger.info(f"[{university_name}] Discovered {len(links)} potential program links.")
                    return list(links)[:20] # Limit to 20 links per university to manage scope

        except Exception as e:
            logger.error(f"[{university_name}] Error discovering links from {base_url}: {e}")
            return []

    async def _extract_program_details_from_url(self, university_name: str, program_url: str, country: str) -> Optional[Dict[str, Any]]:
        """Stage 2: Extract detailed program information from a specific program URL."""
        if program_url in self.processed_urls:
            logger.info(f"[{university_name}] Skipping already processed URL: {program_url}")
            return None
            
        logger.info(f"[{university_name}] Stage 2: Extracting details from {program_url}")
        try:
            async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
                async with session.get(program_url, timeout=30) as response:
                    if response.status != 200:
                        logger.warning(f"[{university_name}] Failed to fetch program URL {program_url}: HTTP {response.status}")
                        return None

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    text_content = soup.get_text(separator=' ', strip=True)

                    if not text_content:
                        return None

                    program = await self._extract_program_with_llm(text_content, university_name, program_url, country)
                    if program:
                        self.processed_urls.add(program_url)
                        return program
                    return None
        except Exception as e:
            logger.error(f"[{university_name}] Error extracting details from {program_url}: {e}")
            return None

    async def _extract_program_with_llm(self, text_content: str, university_name: str, url: str, country: str) -> Optional[Dict[str, Any]]:
        """Use Groq LLM to extract structured program data from a single page's text content."""
        try:
            # Get the page title from the text content if possible
            title_match = BeautifulSoup(text_content, 'html.parser').title
            page_title = title_match.string if title_match else "Unknown Program"

            prompt = f"""
            Analyze the text from the webpage '{page_title}' for the university '{university_name}'.
            Extract the details of the main academic program described on this page.
            Return a SINGLE JSON object with these fields:
            - program_name: The specific name of the academic program (e.g., "Bachelor of Science in Computer Science").
            - degree_type: The type of degree (e.g., "Bachelor", "Master of Science", "PhD").
            - field: The general academic field (e.g., "Computer Science", "Engineering", "Arts & Humanities").
            - description: A concise summary of the program's focus and objectives.
            - duration: The typical time to complete the program (e.g., "4 years", "2 years full-time").
            - admission_requirements: A brief summary of key admission criteria (e.g., "High school diploma with calculus", "Bachelor's degree in a related field").
            
            If the page does not describe a specific degree-granting program (e.g., it's a department homepage or a list of courses), return null.
            Focus on the primary program offered on the page.

            Webpage Content: {text_content[:8000]}
            """

            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are an expert academic program analyst. You extract details for a single program from a webpage's text and return a single, clean JSON object or null if no specific program is found."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content.strip()
            
            if not result_text or result_text.lower() == 'null':
                logger.info(f"[{university_name}] LLM determined no specific program on page {url}")
                return None

            program_data = json.loads(result_text)

            if not program_data.get('program_name') or not program_data.get('degree_type'):
                 logger.warning(f"[{university_name}] LLM response for {url} lacked essential fields (program_name, degree_type). Skipping.")
                 return None

            # Validate and structure the program
            program = UniversityProgram(
                university_name=university_name,
                program_url=url,
                country=country,
                city=None, # City can be added later or derived
                confidence_score=0.85, # Assign a default high confidence for this new method
                **program_data
            )
            logger.info(f"[{university_name}] Successfully extracted: {program.program_name}")
            return program.dict()

        except json.JSONDecodeError:
            logger.warning(f"[{university_name}] Failed to parse LLM JSON response for {url}")
            return None
        except Exception as e:
            logger.error(f"[{university_name}] Error in LLM extraction for {url}: {e}")
            return None

    async def _process_university(self, university_name: str, base_url: str, country: str) -> Dict[str, Any]:
        """Process a single university: discover links, then extract details."""
        # Stage 1: Discover links
        program_links = await self._discover_program_links(university_name, base_url)
        
        if not program_links:
            logger.warning(f"[{university_name}] No program links discovered. Moving to next university.")
            return {'university': university_name, 'programs': [], 'total_programs': 0, 'success': False}

        # Stage 2: Extract details from each link concurrently
        tasks = [self._extract_program_details_from_url(university_name, link, country) for link in program_links]
        
        extracted_programs = []
        with tqdm.tqdm(total=len(tasks), desc=f"Extracting from {university_name}", leave=False) as pbar:
            for coro in asyncio.as_completed(tasks):
                result = await coro
                if result:
                    extracted_programs.append(result)
                pbar.update(1)

        return {
            'university': university_name,
            'programs': extracted_programs,
            'total_programs': len(extracted_programs),
            'success': len(extracted_programs) > 0
        }

    async def scrape_all_universities(self) -> Dict[str, Any]:
        """Main scraping function that processes all universities."""
        logger.info("Starting enhanced 2-stage university scraping process")
        self.processed_urls.clear()

        tasks = []
        for university_name, (url, country) in self.universities.items():
            task = asyncio.create_task(self._process_university(university_name, url, country))
            tasks.append(task)

        results = []
        with tqdm.tqdm(total=len(tasks), desc="Scraping Universities") as pbar:
            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
                pbar.set_description(f"Completed {result['university']} ({result['total_programs']} programs)")
                pbar.update(1)

        # Save results to MongoDB
        saved_count = 0
        for result in results:
            if result['programs']:
                for program in result['programs']:
                    try:
                        # Use a more specific filter for upserting to avoid collisions
                        filter_query = {
                            'university_name': program['university_name'],
                            'program_name': program['program_name'],
                            'degree_type': program.get('degree_type')
                        }
                        self.collection.update_one(
                            filter_query,
                            {'$set': program},
                            upsert=True
                        )
                        saved_count += 1
                    except Exception as e:
                        logger.error(f"Failed to save program: {program.get('program_name')}. Error: {e}")

        total_programs = sum(r['total_programs'] for r in results)
        summary = {
            'total_universities_processed': len(self.universities),
            'successful_universities': len([r for r in results if r['success']]),
            'total_programs_extracted': total_programs,
            'programs_saved_to_db': saved_count,
            'results': results
        }

        logger.info(f"Scraping completed: {summary['successful_universities']}/{summary['total_universities_processed']} universities successful, {total_programs} programs extracted.")
        return summary

async def main():
    """Main function that handles the complete automated scraping workflow"""
    start_time = time.time()

    logger.info("=== Enhanced University Scraper Starting ===")

    # Initialize scraper
    try:
        scraper = EnhancedUniversityScraper()
        logger.info("Scraper initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize scraper: {e}")
        return

    # Run the scraping process
    try:
        logger.info("Starting scraping process for all universities...")
        summary = await scraper.scrape_all_universities()

        # Update processing time
        summary['processing_time_seconds'] = time.time() - start_time

        # Display results
        logger.info("=== Scraping Results ===")
        logger.info(f"Universities processed: {summary['total_universities_processed']}")
        logger.info(f"Successful: {summary['successful_universities']}")
        logger.info(f"Programs extracted: {summary['total_programs_extracted']}")
        logger.info(f"Programs saved: {summary['programs_saved_to_db']}")
        logger.info(f"Processing time: {summary['processing_time_seconds']:.2f} seconds")

        # Detailed results
        logger.info("\n=== Detailed Results by University ===")
        for result in summary['results']:
            status = "SUCCESS" if result['success'] else "FAILED"
            logger.info(f"- {result['university']}: Found {result['total_programs']} programs. Status: {status}")
            if result['programs']:
                for prog in result['programs'][:2]: # Show a sample of 2 programs
                    logger.info(f"  - Sample: {prog['program_name']} ({prog['degree_type']})")


        logger.info("=== Scraping Process Completed Successfully ===")

    except Exception as e:
        logger.error(f"Scraping process failed: {e}")
        logger.info("=== Scraping Process Failed ===")

if __name__ == "__main__":
    # Set up asyncio for Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Run the main function
    asyncio.run(main())

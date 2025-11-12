# In file: scraper.py
import os
import asyncio
import logging
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from groq import Groq
from schema import UniversityProgram
from dotenv import load_dotenv
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

class AIScraper:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.model_name = os.getenv("GROQ_MODEL", "llama3-70b-8192")
        self.scrape_timeout = int(os.getenv("SCRAPE_TIMEOUT", 30))
        self.rate_limit_delay = int(os.getenv("RATE_LIMIT_DELAY", 2))
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not found in .env file")
        
        # 1. Initialize the Groq client
        self.groq_client = Groq(api_key=self.groq_api_key)
        logging.info("AIScraper initialized.")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def scrape_program_data(self, url: str) -> Optional[UniversityProgram]:
        logging.info(f"Scraping: {url}")
        
        # 2. Define the LLM extraction strategy (the core of the video's method)
        extraction_strategy = LLMExtractionStrategy(
            llm=self.groq_client,
            model_name=self.model_name,
            pydantic_schema=UniversityProgram
        )
        
        # 3. Initialize Crawl4AI
        crawler = AsyncWebCrawler()
        
        try:
            # 4. Run the crawl and extract
            result = await crawler.arun(url=url, extraction_strategy=extraction_strategy, timeout=self.scrape_timeout)
            
            # Check if extraction was successful
            try:
                logging.info(f"Result success: {result.success}, extracted_content type: {type(result.extracted_content)}")
                if result.extracted_content:
                    logging.info(f"Extracted content length: {len(result.extracted_content)}")
                    if result.extracted_content:
                        program_data = result.extracted_content[0]
                        
                        # Manually add the source_url (Crawl4AI doesn't do this automatically)
                        program_data.source_url = url
                        
                        logging.info(f"Successfully extracted: {program_data.program_name}")
                        # Rate limiting delay
                        await asyncio.sleep(self.rate_limit_delay)
                        return program_data
                    else:
                        logging.warning("Extracted content is empty list.")
                        return None
                else:
                    logging.warning("No data extracted.")
                    return None
            except AttributeError as e:
                logging.warning(f"Extraction failed: {e}")
                return None
                
        except Exception as e:
            logging.error(f"An error occurred during scraping {url}: {e}")
            raise  # Re-raise for retry
# In file: main.py
import asyncio
import logging
import argparse
from scraper import AIScraper
from database import MongoConnection
from tqdm.asyncio import tqdm

# --- IMPORTANT ---
# Real university program URLs for computer science master's programs
URLS_TO_SCRAPE = [
    # Top Universities
    "https://www.cs.ox.ac.uk/research/graduate-study/mphil-dphil-computer-science/",  # University of Oxford
    "https://www.cst.cam.ac.uk/prospective/postgraduate",  # University of Cambridge
    "https://www.imperial.ac.uk/computing/prospective-students/courses/msc-computing/",  # Imperial College London
    "https://ethz.ch/en/studies/en/master/computer-science.html",  # ETH Zurich
    "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/computer-science-msc",  # UCL
    "https://www.psl.eu/en/academic-offer/master-programmes/computer-science",  # Université PSL
    "https://www.tum.de/en/studies/application/master/computer-science/",  # Technical University of Munich
    "https://www.epfl.ch/education/studies/en/rules-and-procedures/master/computer-science/",  # EPFL
    
    # Strong Universities
    "https://www.ed.ac.uk/studying/postgraduate/degrees/index.php?r=site/view&id=919",  # University of Edinburgh
    "https://www.manchester.ac.uk/study/postgraduate-research/programmes/list/02674/msc-advanced-computer-science/",  # University of Manchester
    "https://www.kcl.ac.uk/study/postgraduate-taught/courses/computer-science-msc",  # King's College London
    "https://www.tudelft.nl/en/education/programmes/masters/computer-science/msc-computer-science/",  # Delft University of Technology
    "https://www.gla.ac.uk/postgraduate/taught/computerscience/",  # University of Glasgow
    "https://www.leeds.ac.uk/info/130000/postgraduate_taught_courses/130001/Computer_Science",  # University of Leeds
    "https://www.uva.nl/en/programmes/master-s/master-s-programmes/content/folder/computer-science/computer-science.html",  # University of Amsterdam
    "https://www.lmu.de/en/studies/degree-programmes/master/computer-science/",  # LMU Munich
    "https://warwick.ac.uk/study/postgraduate/courses/computerscience",  # University of Warwick
    "https://www.uni-heidelberg.de/en/study/all-subjects/computer-science/computer-science-master",  # Heidelberg University
    
    # Medium Universities
    "https://www.uu.nl/en/masters/computer-science",  # Utrecht University
    "https://www.ut.ee/en/study/programme/computer-science-msc",  # University of Tartu
    "https://www.uoa.gr/en/studies/postgraduate-studies/postgraduate-programmes/computer-science",  # University of Athens
    "https://www.kuleuven.be/en/study/programmes/master-of-science-in-computer-science",  # KU Leuven
    "https://www.universiteitleiden.nl/en/education/study-programmes/master/computer-science"  # Leiden University
]

async def scrape_and_save(scraper, mongo, url, pbar):
    program_data = await scraper.scrape_program_data(url)
    
    # 3. If we got data, save it
    if program_data:
        # Convert the Pydantic model to a dictionary
        data_dict = program_data.model_dump()
        
        # Save to MongoDB
        mongo.save_program(data_dict)
    else:
        logging.warning(f"Failed to scrape data from: {url}")
    pbar.update(1)

async def main():
    parser = argparse.ArgumentParser(description="Scrape university program data.")
    parser.add_argument('--urls', nargs='*', default=URLS_TO_SCRAPE, help='List of URLs to scrape')
    parser.add_argument('--urls-file', type=str, help='File containing URLs, one per line')
    args = parser.parse_args()

    urls = args.urls
    if args.urls_file:
        with open(args.urls_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler(), logging.FileHandler('scraper.log')])
    logging.info("Starting the AI Scraping job...")
    
    # 1. Initialize tools
    scraper = AIScraper()
    mongo = MongoConnection()
    
    if not mongo.client:
        logging.error("Failed to connect to MongoDB. Exiting.")
        return

    # 2. Scrape concurrently
    with tqdm(total=len(urls), desc="Scraping URLs") as pbar:
        tasks = [scrape_and_save(scraper, mongo, url, pbar) for url in urls]
        await asyncio.gather(*tasks)

    logging.info("Scraping job complete.")

if __name__ == "__main__":
    asyncio.run(main())
import os
import pymongo
from pymongo import MongoClient
from dotenv import load_dotenv
from tabulate import tabulate
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_database_content():
    """
    Connects to the MongoDB database used by the scraper and verifies its content.
    This script proves that the data from the live scraping is being stored.
    """
    load_dotenv()
    
    # IMPORTANT: These are the hardcoded values from uni_scraper_enhanced.py
    DATABASE_NAME = "university_scraper"
    COLLECTION_NAME = "programs"
    
    try:
        # Connect to MongoDB
        mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Ping the server to confirm connection
        client.admin.command('ping')
        logger.info("✅ MongoDB connection successful.")
        
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        logger.info(f"Connecting to Database: '{DATABASE_NAME}', Collection: '{COLLECTION_NAME}'")
        
        # Count the documents
        total_records = collection.count_documents({})
        
        print("\n" + "="*80)
        print("                  DATABASE VERIFICATION REPORT")
        print("="*80)
        
        if total_records > 0:
            logger.info(f"✅ SUCCESS: Found {total_records} records in the database.")
            
            # Fetch a sample of records to display
            sample_records = list(collection.find({}, {
                'university_name': 1, 
                'program_name': 1, 
                'degree_type': 1,
                'confidence_score': 1,
                '_id': 0
            }).limit(15))
            
            # Format confidence score for display
            for record in sample_records:
                if 'confidence_score' in record and record['confidence_score'] is not None:
                    record['confidence_score'] = f"{record['confidence_score']:.2f}"

            print("\nSample of 15 records found in the database:\n")
            # Use headers="keys" for a list of dictionaries
            print(tabulate(sample_records, headers="keys", tablefmt="grid"))
            
            print("\n" + "="*80)
            print("CONCLUSION:")
            print("The live scraper IS storing data in the database.")
            print(f"Please check the '{DATABASE_NAME}' database and '{COLLECTION_NAME}' collection in your MongoDB client.")
            print("\nTo export this data to CSV/Excel, run: python test_export.py")
            print("="*80)

        else:
            logger.error("❌ FAILURE: No records found in the database.")
            logger.error("This indicates a problem with the scraper's saving mechanism or the database connection.")
            print("\n" + "="*80)
            print("CONCLUSION: The database is empty. Please re-run the scraper.")
            print("="*80)

    except pymongo.errors.ServerSelectionTimeoutError as e:
        logger.error(f"❌ DATABASE CONNECTION FAILED: Could not connect to MongoDB.")
        logger.error(f"Please ensure MongoDB is running at the URI specified in your .env file: {os.getenv('MONGODB_URI')}")
        logger.error(f"Error details: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    finally:
        if 'client' in locals():
            client.close()
            logger.info("MongoDB connection closed.")

if __name__ == "__main__":
    verify_database_content()

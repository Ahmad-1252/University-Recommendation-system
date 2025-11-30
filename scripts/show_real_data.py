
import os
from dotenv import load_dotenv
import pymongo
import pandas as pd

# --- Configuration ---
# This script specifically targets the database and collection used by the live scraper
DATABASE_NAME = 'university_scraper'
COLLECTION_NAME = 'programs'
# This regex is designed to find URLs from the *actual* universities that were scraped
LIVE_DATA_URL_PATTERN = r'\.ca|\.ac\.uk|\.edu\.au|cmu\.edu'

def show_real_data_only():
    """
    Connects to MongoDB and queries for records that are confirmed to be from the
    live web scraper, then displays them clearly.
    """
    load_dotenv()
    mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')

    print(f"Attempting to connect to MongoDB at: {mongodb_uri}")
    print(f"Targeting database: '{DATABASE_NAME}', collection: '{COLLECTION_NAME}'")

    try:
        client = pymongo.MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        client.server_info()  # Verify connection
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        print("✅ Successfully connected to MongoDB.")

        # --- Query for REAL Data, Excluding Synthetic Placeholders ---
        query = {'program_url': {'$regex': LIVE_DATA_URL_PATTERN}}
        print(f"\nSearching for records with real URLs (matching: '{LIVE_DATA_URL_PATTERN}')...")
        
        # Projection to get only the most relevant fields for verification
        projection = {
            'university_name': 1,
            'program_name': 1,
            'program_url': 1,
            'field': 1,
            '_id': 0
        }
        
        real_records = list(collection.find(query, projection))
        
        if not real_records:
            print("\n❌ --- NO LIVE-SCRAPED RECORDS FOUND --- ❌")
            print("The database currently contains only synthetic data.")
            print("This can happen if the live scraper (`uni_scraper_enhanced.py`) has not been run yet.")
            return

        print(f"\n✅ SUCCESS: Found {len(real_records)} records with REAL URLs. Displaying them now:")

        # --- Display Data in a Readable Format ---
        df = pd.DataFrame(real_records)
        
        # Ensure key columns are present
        display_columns = ['university_name', 'program_name', 'program_url', 'field']
        for col in display_columns:
            if col not in df.columns:
                df[col] = 'N/A'
        
        # Print the DataFrame as a clean table
        print(df[display_columns].to_string(index=False))

    except pymongo.errors.ServerSelectionTimeoutError as err:
        print(f"\n❌ DATABASE ERROR: Could not connect to MongoDB.")
        print(f"Please ensure your MongoDB server is running and accessible at '{mongodb_uri}'.")
        print(f"Error details: {err}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        if 'client' in locals():
            client.close()
            print("\nConnection to MongoDB closed.")

if __name__ == "__main__":
    show_real_data_only()

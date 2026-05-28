import os

import pandas as pd
import pymongo
from dotenv import load_dotenv

# --- Configuration ---
# Ensure we are looking at the same place the scraper saved the data
DATABASE_NAME = "university_scraper"
COLLECTION_NAME = "programs"
# Regex to identify records from the LIVE scraper based on the domains that were scraped
LIVE_DATA_URL_PATTERN = (
    r"\.ca/|\.ac\.uk/|\.edu\.au/|cmu\.edu|utoronto\.ca|ubc\.ca|mcgill\.ca|uwaterloo\.ca"
)


def verify_live_data():
    """
    Connects to MongoDB and queries for records that match the pattern of
    live-scraped data, displaying them to the user.
    """
    load_dotenv()
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")

    print(f"Connecting to MongoDB: {mongodb_uri}")
    print(f"Database: '{DATABASE_NAME}', Collection: '{COLLECTION_NAME}'")

    try:
        client = pymongo.MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        client.server_info()  # Force connection to verify it's working
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        print("✅ Successfully connected to MongoDB.")

        # --- Query for Live Data ---
        query = {"program_url": {"$regex": LIVE_DATA_URL_PATTERN}}
        print(
            f"\nSearching for LIVE records with pattern: '{LIVE_DATA_URL_PATTERN}'..."
        )

        # Use a projection to only get the fields we need
        projection = {
            "university_name": 1,
            "program_name": 1,
            "program_url": 1,
            "field": 1,
            "degree_type": 1,
            "_id": 0,
        }
        live_records = list(collection.find(query, projection))

        if not live_records:
            print("\n❌ --- NO LIVE RECORDS FOUND ---")
            print("Could not find any records matching the live-scraped URL patterns.")
            print(
                "This might mean the live scraper hasn't run or found programs from the target domains."
            )
            return

        print(
            f"\n✅ SUCCESS: Found {len(live_records)} live-scraped records. Showing a sample:"
        )

        # --- Display Data Clearly ---
        df = pd.DataFrame(live_records)

        # Define the most important columns to show for verification
        display_columns = [
            "university_name",
            "program_name",
            "program_url",
            "field",
            "degree_type",
        ]

        # Ensure columns exist to prevent errors
        for col in display_columns:
            if col not in df.columns:
                df[col] = "Not Available"

        # Use pandas to print a clean, readable table
        print(df[display_columns].to_string(index=False))

    except pymongo.errors.ServerSelectionTimeoutError as err:
        print("\n❌ DATABASE ERROR: Could not connect to MongoDB.")
        print(
            f"Please ensure your MongoDB server is running and accessible at '{mongodb_uri}'."
        )
        print(f"Details: {err}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        if "client" in locals():
            client.close()
            print("\nConnection to MongoDB closed.")


if __name__ == "__main__":
    verify_live_data()

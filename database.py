# In file: database.py
import os
import pymongo
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class MongoConnection:
    def __init__(self):
        try:
            connection_string = os.getenv("MONGO_CONNECTION_STRING")
            database_name = os.getenv("DATABASE_NAME", "university_db")
            collection_name = os.getenv("COLLECTION_NAME", "programs")
            if not connection_string:
                raise ValueError("MONGO_CONNECTION_STRING not found in .env file")
            
            self.client = pymongo.MongoClient(connection_string)
            self.db = self.client[database_name]
            self.collection = self.db[collection_name]
            # Create indexes for better performance
            self.collection.create_index([("source_url", 1)], unique=True)
            self.collection.create_index([("university_name", 1)])
            print("Successfully connected to MongoDB Atlas.")
            
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            self.client = None
            
    def save_program(self, program_data: dict):
        if not self.client:
            print("Not connected to MongoDB. Cannot save.")
            return

        try:
            # Add timestamp
            program_data["last_updated"] = datetime.utcnow()
            # Use 'source_url' as the unique key
            filter_query = {"source_url": program_data.get("source_url")}
            
            # replace_one with upsert=True:
            # If a doc with this URL exists, it's replaced.
            # If not, a new doc is inserted.
            self.collection.replace_one(filter_query, program_data, upsert=True)
            print(f"Successfully saved/updated: {program_data.get('program_name')}")
            
        except Exception as e:
            print(f"Error saving to MongoDB: {e}")
    
    def get_program_by_url(self, url: str):
        return self.collection.find_one({"source_url": url})
    
    def list_all_programs(self):
        return list(self.collection.find())
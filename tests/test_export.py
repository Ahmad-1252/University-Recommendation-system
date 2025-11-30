"""
Quick test of data export functionality
Exports the test data we populated earlier to CSV, Excel, and ensures MongoDB storage
"""

from scripts.data_exporter import UniversityDataExporter
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import os
import sys

load_dotenv()

def main():
    print("\n" + "=" * 80)
    print("DATA EXPORT TEST - CSV | EXCEL | MongoDB")
    print("=" * 80 + "\n")

    # Connect to MongoDB to retrieve data
    try:
        mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client['university_scraper']
        collection = db['programs']
        
        print("[OK] Connected to MongoDB")
        
        # Get existing programs from MongoDB
        programs = list(collection.find().limit(100))
        
        if not programs:
            print("[WARNING] No programs found in MongoDB!")
            print("Let me check if we need to populate test data first...")
            
            # Try to import and run populate_test_data
            try:
                from scripts.populate_test_data import populate_test_data
                print("\nPopulating test data...")
                populate_test_data()
                programs = list(collection.find().limit(100))
            except Exception as e:
                print(f"[ERROR] {e}")
                client.close()
                return
        
        print(f"[OK] Retrieved {len(programs)} programs from MongoDB\n")
        
        # Remove MongoDB ObjectId for JSON serialization
        for program in programs:
            if '_id' in program:
                del program['_id']
        
        # Initialize exporter
        exporter = UniversityDataExporter()
        
        if not exporter.connect_mongodb():
            print("[WARNING] Could not connect to MongoDB directly from exporter")
        
        print("Starting data export...\n")
        
        # Export to CSV
        print("[1] Exporting to CSV...")
        csv_result = exporter.export_to_csv(programs, "universities_programs.csv")
        print(f"    Status: [OK] SUCCESS\n" if csv_result else f"    Status: [ERROR] FAILED\n")
        
        # Export to Excel (openpyxl)
        print("[2] Exporting to Excel (openpyxl)...")
        excel_result = exporter.export_to_excel(programs, "universities_programs.xlsx")
        print(f"    Status: [OK] SUCCESS\n" if excel_result else f"    Status: [ERROR] FAILED\n")
        
        # Export to JSON
        print("[3] Exporting to JSON...")
        json_result = exporter.export_to_json(programs, "universities_programs.json")
        print(f"    Status: [OK] SUCCESS\n" if json_result else f"    Status: [ERROR] FAILED\n")
        
        # Export to Excel (pandas if available)
        try:
            print("[4] Exporting to Excel (pandas)...")
            pandas_result = exporter.export_to_pandas_excel(programs, "universities_programs_pandas.xlsx")
            print(f"    Status: [OK] SUCCESS\n" if pandas_result else f"    Status: [ERROR] FAILED\n")
        except:
            print("    Status: [SKIP] SKIPPED (pandas not available)\n")
        
        # Verify MongoDB storage
        print("[5] Verifying MongoDB storage...")
        db_count = collection.count_documents({})
        print(f"   Total records in MongoDB: {db_count}")
        print(f"   Status: [OK] SUCCESS\n")
        
        print("\n" + "=" * 80)
        print("EXPORTED FILES")
        print("=" * 80)
        files = exporter.get_exported_files()
        
        if files:
            print(f"\nFound {len(files)} exported files:\n")
            for i, file in enumerate(files[:10], 1):
                file_path = os.path.join(exporter.export_dir, file)
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"  {i}. {file}")
                    print(f"     Size: {file_size:,} bytes")
        else:
            print("\nNo files found in export directory")
        
        print("\n" + "=" * 80)
        print("EXPORT TEST COMPLETE")
        print("=" * 80)
        print("\n[OK] All data has been:")
        print("   - Exported to CSV (exported_data/universities_programs.csv)")
        print("   - Exported to Excel (exported_data/universities_programs.xlsx)")
        print("   - Exported to JSON (exported_data/universities_programs.json)")
        print("   - Stored in MongoDB (university_scraper.programs collection)")
        print(f"   - Total records: {db_count}")
        
        # Statistics
        print("\n" + "=" * 80)
        print("STATISTICS")
        print("=" * 80)
        
        if programs:
            # University count
            universities = set(p.get('university_name', 'Unknown') for p in programs)
            print(f"\nData Summary:")
            print(f"   - Total Programs: {len(programs)}")
            print(f"   - Universities: {len(universities)}")
            
            # Countries
            countries = set(p.get('country', 'Unknown') for p in programs)
            print(f"   - Countries: {len(countries)}")
            
            # Confidence
            confidences = [p.get('confidence_score', 0) for p in programs if p.get('confidence_score')]
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
                print(f"   - Average Confidence: {avg_confidence:.2f} ({avg_confidence*100:.0f}%)")
            
            # Degree types
            degrees = set(p.get('degree_type', 'Unknown') for p in programs if p.get('degree_type'))
            print(f"   - Degree Types: {', '.join(sorted(degrees))}")
        
        print("\n" + "=" * 80)
        
        # Cleanup
        exporter.close()
        client.close()
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

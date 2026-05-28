#!/usr/bin/env python
"""
STARTUP GUIDE - University Recommendation System
Quick start script to initialize and run the system
"""

import os
import sys


def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_step(step_num, description):
    """Print step information"""
    print(f"[STEP {step_num}] {description}")
    print("-" * 80)


def check_python():
    """Check Python version"""
    print_step(1, "Checking Python Installation")

    version = sys.version_info
    print(f"Python Version: {version.major}.{version.minor}.{version.micro}")

    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("[ERROR] Python 3.8+ required")
        return False

    print("[OK] Python version compatible\n")
    return True


def check_mongodb():
    """Check MongoDB installation"""
    print_step(2, "Checking MongoDB Connection")

    try:
        from pymongo import MongoClient

        client = MongoClient(
            "mongodb://localhost:27017/", serverSelectionTimeoutMS=5000
        )
        client.admin.command("ping")
        client.close()
        print("[OK] MongoDB is running on localhost:27017\n")
        return True
    except Exception as e:
        print(f"[WARNING] MongoDB not accessible: {e}")
        print("[INFO] You can:")
        print(
            "  1. Start MongoDB: services.msc (Windows) or systemctl start mongod (Linux)"
        )
        print("  2. Use MongoDB Atlas cloud: Update MONGODB_URI in .env")
        print("  3. Proceed anyway (data export will still work)\n")
        return False


def check_env_file():
    """Check .env file"""
    print_step(3, "Checking Environment Configuration")

    if os.path.exists(".env"):
        print("[OK] .env file exists")

        # Check for required variables
        with open(".env") as f:
            content = f.read()

        if "GROQ_API_KEY" in content:
            print("[OK] GROQ_API_KEY configured")
        else:
            print("[WARNING] GROQ_API_KEY not found in .env")

        if "MONGODB_URI" in content:
            print("[OK] MONGODB_URI configured")
        else:
            print("[WARNING] MONGODB_URI not found in .env")

        print()
        return True
    else:
        print("[ERROR] .env file not found")
        print("[INFO] Create .env with:")
        print("  GROQ_API_KEY=your_api_key_here")
        print("  MONGODB_URI=mongodb://localhost:27017/")
        print()
        return False


def check_dependencies():
    """Check Python dependencies"""
    print_step(4, "Checking Python Dependencies")

    required = {
        "requests": "HTTP requests",
        "beautifulsoup4": "Web scraping",
        "groq": "Groq LLM API",
        "pymongo": "MongoDB",
        "pydantic": "Data validation",
        "tqdm": "Progress tracking",
        "aiohttp": "Async HTTP",
        "tenacity": "Retry logic",
        "python-dotenv": "Environment variables",
    }

    optional = {"pandas": "Data analysis", "openpyxl": "Excel export"}

    missing = []

    for package, description in required.items():
        try:
            __import__(package.replace("-", "_"))
            print(f"[OK] {package:20} - {description}")
        except ImportError:
            print(f"[ERROR] {package:20} - {description} [MISSING]")
            missing.append(package)

    print()

    for package, description in optional.items():
        try:
            __import__(package.replace("-", "_"))
            print(f"[OK] {package:20} - {description}")
        except ImportError:
            print(f"[WARN] {package:20} - {description} [OPTIONAL]")

    print()

    if missing:
        print("[ACTION] Install missing packages:")
        install_cmd = " ".join(missing)
        print(f"  pip install {install_cmd}")
        return False

    return True


def show_startup_options():
    """Display startup options"""
    print_header("STARTUP OPTIONS")

    print(
        """
Choose how you want to start:

[1] QUICK TEST - Export existing data
    Command: python test_export.py
    What it does:
      - Retrieves data from MongoDB
      - Exports to CSV, Excel, JSON
      - Shows statistics
    Time: ~5 seconds

[2] FULL SCRAPE + EXPORT - Scrape all universities
    Command: python scraper_with_export.py
    What it does:
      - Scrapes 20 universities
      - Extracts programs via LLM
      - Saves to MongoDB
      - Exports to CSV/Excel/JSON
    Time: ~5-15 minutes
    Rate limits: May take longer due to API limits

[3] RUN COMPREHENSIVE TEST - Validate system
    Command: python test_scraper_comprehensive.py
    What it does:
      - Tests MongoDB connection
      - Validates data schema
      - Checks API integration
      - Verifies data quality
    Time: ~10 seconds

[4] VIEW EXPORTED DATA
    Command: dir exported_data  (Windows)
             ls -la exported_data/ (Linux/Mac)
    What it does:
      - Lists all exported files
      - Shows file sizes

[5] MANUAL DATA EXPORT
    If you only want to export existing MongoDB data:
    Command: python test_export.py

[6] SETUP GUIDE
    See this file for detailed setup instructions
"""
    )


def show_file_structure():
    """Show project file structure"""
    print_header("PROJECT FILES")

    files = {
        "Scrapers": {
            "uni_scraper_enhanced.py": "Main scraper with multi-strategy retry",
            "scraper_with_export.py": "Scraper + automatic export",
        },
        "Data Export": {
            "data_exporter.py": "Core export functionality (CSV, Excel, JSON, MongoDB)",
            "test_export.py": "Quick test of export features",
        },
        "Testing": {
            "test_scraper_comprehensive.py": "Comprehensive test suite",
            "populate_test_data.py": "Populate test data",
        },
        "Documentation": {
            "DATA_EXPORT_GUIDE.md": "Complete export guide",
            "README.md": "Project overview",
        },
        "Data": {
            "exported_data/": "Directory for exported files",
        },
    }

    for category, file_dict in files.items():
        print(f"\n{category}:")
        for filename, description in file_dict.items():
            print(f"  {filename:35} - {description}")


def show_troubleshooting():
    """Show troubleshooting guide"""
    print_header("TROUBLESHOOTING")

    print(
        """
PROBLEM: "ModuleNotFoundError: No module named 'groq'"
SOLUTION: pip install groq

PROBLEM: "Connection refused" (MongoDB)
SOLUTION:
  1. Start MongoDB:
     Windows: net start MongoDB
     Linux: sudo systemctl start mongod
  2. Or use MongoDB Atlas cloud URL

PROBLEM: "GROQ_API_KEY not found"
SOLUTION:
  1. Create .env file in project directory
  2. Add: GROQ_API_KEY=your_key_here
  3. Get key from: https://console.groq.com

PROBLEM: "UnicodeEncodeError" on Windows
SOLUTION: Already fixed in latest version, try:
  python -c "import sys; print(sys.stdout.encoding)"

PROBLEM: Scraper takes too long
SOLUTION:
  1. This is normal (API rate limits)
  2. Exports still work while scraping
  3. Check exported_data/ for current files

PROBLEM: No files in exported_data/
SOLUTION:
  1. Check directory permissions
  2. Run test: python test_export.py
  3. Check logs: data_export.log
"""
    )


def show_quick_commands():
    """Show quick reference commands"""
    print_header("QUICK COMMANDS")

    print(
        """
1. Test Export (Recommended First):
   python test_export.py

2. View Exported Files:
   dir exported_data         (Windows)
   ls exported_data/         (Linux/Mac)

3. Run Full Scrape:
   python scraper_with_export.py

4. Run Tests:
   python test_scraper_comprehensive.py

5. Check MongoDB:
   mongosh                   (Connect to database)
   db.university_scraper.programs.countDocuments()

6. View Logs:
   type data_export.log      (Windows)
   tail -f data_export.log   (Linux/Mac)

7. Install Dependencies:
   pip install -r requirements.txt

8. Clean Exported Files:
   rm -r exported_data/*     (Linux/Mac)
   del exported_data\\*     (Windows)
"""
    )


def show_data_flow():
    """Show data flow diagram"""
    print_header("DATA FLOW")

    print(
        """
OPTION 1: Quick Export (Test Existing Data)
┌─────────────────────┐
│  MongoDB Database   │  ← Data from previous runs
│  (15+ programs)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  data_exporter.py   │  ← Export module
└──────────┬──────────┘
           │
    ┌──────┼──────┬──────┐
    ▼      ▼      ▼      ▼
   CSV   Excel   JSON  MongoDB
    │      │      │      │
    ▼      ▼      ▼      ▼
 .csv   .xlsx   .json   Persist


OPTION 2: Full Scrape + Export (Recommended)
┌──────────────────────────┐
│  Universities (20)       │  ← Target universities
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Web Scraper             │  ← Fetch HTML
│  (BeautifulSoup4)        │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  LLM Extraction          │  ← Parse with AI
│  (Groq - llama 3.1)      │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Data Validation         │  ← Pydantic
│  (Schema Check)          │
└──────────┬───────────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
┌────────┐   ┌──────────────┐
│MongoDB │   │data_exporter │
│Storage │   │    Module    │
└────────┘   └──────┬───────┘
                    │
            ┌───────┼───────┬────────┐
            ▼       ▼       ▼        ▼
           CSV    Excel   JSON   MongoDB
            │       │       │        │
            ▼       ▼       ▼        ▼
         exported_data/  +  Database Persist
"""
    )


def main():
    """Main startup guide"""
    print_header("UNIVERSITY RECOMMENDATION SYSTEM - STARTUP GUIDE")

    # Run checks
    print("\nRunning system checks...\n")

    checks = {
        "Python": check_python(),
        "Environment File": check_env_file(),
        "Dependencies": check_dependencies(),
        "MongoDB": check_mongodb(),
    }

    # Summary
    print_header("SYSTEM CHECK SUMMARY")
    for check_name, result in checks.items():
        status = "[OK]" if result else "[WARN]"
        print(f"{status} {check_name}")

    # Show options
    show_startup_options()

    # Show file structure
    show_file_structure()

    # Show data flow
    show_data_flow()

    # Show quick commands
    show_quick_commands()

    # Show troubleshooting
    show_troubleshooting()

    # Final instructions
    print_header("GETTING STARTED")

    print(
        """
STEP 1: Prepare (One-time setup)
  1. Ensure MongoDB is running or use cloud URI
  2. Set GROQ_API_KEY in .env
  3. Install dependencies: pip install -r requirements.txt

STEP 2: Test (Verify system works)
  python test_export.py

  This should:
  - Connect to MongoDB
  - Retrieve 15 test programs
  - Export to CSV, Excel, JSON
  - Show statistics

STEP 3: Run Full Scrape (Optional, takes 5-15 minutes)
  python scraper_with_export.py

  This will:
  - Scrape 20 universities
  - Extract programs
  - Save to MongoDB
  - Export to all formats

STEP 4: Access Your Data
  - CSV: exported_data/universities_programs.csv
  - Excel: exported_data/universities_programs.xlsx
  - JSON: exported_data/universities_programs.json
  - MongoDB: Use mongosh or MongoDB Compass

SUCCESS! You now have:
  ✅ CSV files (import to Excel/Google Sheets)
  ✅ Excel files (formatted with colors/borders)
  ✅ JSON files (for APIs/applications)
  ✅ MongoDB database (persistent storage)
  ✅ All data synchronized across all formats
"""
    )

    print_header("NEXT STEPS")
    print(
        """
1. Run the test export:
   python test_export.py

2. Check the exported files:
   dir exported_data

3. Run the full scraper (optional):
   python scraper_with_export.py

4. For help:
   - Check DATA_EXPORT_GUIDE.md
   - Review README.md
   - Check logs in data_export.log

Good luck! Your system is ready to go! 🚀
"""
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Startup guide interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

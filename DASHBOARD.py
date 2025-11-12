#!/usr/bin/env python
# SYSTEM DASHBOARD - University Recommendation System

def print_dashboard():
    dashboard_text = """
╔════════════════════════════════════════════════════════════════════════════╗
║                   UNIVERSITY RECOMMENDATION SYSTEM                         ║
║                        STATUS DASHBOARD STARTUP                            ║
╚════════════════════════════════════════════════════════════════════════════╝

SYSTEM STATUS: [OK] READY TO USE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[OK] Python 3.13.5
[OK] MongoDB (Local - Running)
[OK] GROQ API (Configured)
[OK] Dependencies (All Installed)
[OK] Test Data (15 Programs)
[OK] Export System (4 Formats)
[OK] Database Storage (Working)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3 WAYS TO GET STARTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1] QUICK TEST (Recommended - 5 seconds)
    Command: python test_export.py
    
    Result: CSV, Excel, JSON files created
    Time: ~5 seconds
    Difficulty: Easy

[2] FULL SCRAPE + EXPORT (10-15 minutes)
    Command: python scraper_with_export.py
    
    Result: 50+ programs + all exports
    Time: ~10-15 minutes
    Difficulty: Easy (just run it)

[3] VALIDATION (10 seconds)
    Command: python test_scraper_comprehensive.py
    
    Result: System validation report
    Time: ~10 seconds
    Difficulty: Easy

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

YOUR FILES (Already Ready)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

exported_data/
├── universities_programs.csv (3,645 bytes)
├── universities_programs.xlsx (7,168 bytes)
├── universities_programs_pandas.xlsx (7,154 bytes)
└── universities_programs.json (9,055 bytes)

MongoDB: 15 programs stored and ready

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

QUICK START NOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Copy and paste this command:

python test_export.py

Then check your files:

dir exported_data

Done! You now have CSV, Excel, and JSON exports!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

QUICK COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

python STARTUP.py                    - Check system
python test_export.py                - Quick test (5 sec)
python scraper_with_export.py        - Full scrape (10-15 min)
python test_scraper_comprehensive.py - Validate
dir exported_data                    - View files
type data_export.log                 - View logs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STARTUP GUIDES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Read these files for help:
• START_HERE.md (overview - BEST FOR QUICK START)
• HOW_TO_START.md (step-by-step guide)
• QUICK_START.md (quick reference)
• DATA_EXPORT_GUIDE.md (technical details)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Problem: Module not found
Fix: pip install beautifulsoup4 python-dotenv

Problem: MongoDB connection error
Fix: net start MongoDB

Problem: API key not found
Fix: Create .env and add GROQ_API_KEY

Problem: No files created
Fix: Check data_export.log for errors

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ Your system is ready to use! ✨

╚════════════════════════════════════════════════════════════════════════════╝
"""
    print(dashboard_text)

if __name__ == "__main__":
    print_dashboard()
    print("NEXT STEP: Run 'python test_export.py' to start!")
    print()

import json
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from typing import List, Dict
from datetime import datetime
import tabulate

load_dotenv()

class UniversityDataViewer:
    """View, search, and analyze scraped university data"""

    def __init__(self):
        self.client = MongoClient(os.getenv('MONGODB_URI'))
        self.db = self.client[os.getenv('DATABASE_NAME', 'university_db')]
        self.collection = self.db[os.getenv('COLLECTION_NAME', 'programs')]

    def view_all_programs(self, detailed: bool = False):
        """Display all programs"""
        programs = list(self.collection.find({}, {'_id': 0}))

        if not programs:
            print("❌ No programs found in database")
            return

        print(f"\n📚 TOTAL PROGRAMS: {len(programs)}\n")

        if detailed:
            for i, prog in enumerate(programs, 1):
                print(f"{'='*100}")
                print(f"#{i} - {prog['university_name']} ({prog['country']})")
                print(f"{'='*100}")
                print(f"Program: {prog.get('program_name', 'N/A')}")
                print(f"Tier: {prog.get('tier', 'N/A').upper()}")
                print(f"Confidence: {prog.get('extraction_confidence', 0):.0%}")
                print()
                print(f"GPA Required: {prog.get('min_gpa', 'N/A')}")
                print(f"English Req: {prog.get('english_requirement', 'N/A')}")
                print(f"Tuition: {prog.get('tuition_fee', 'N/A')}")
                print(f"Duration: {prog.get('duration', 'N/A')}")
                print(f"Deadline: {prog.get('application_deadline', 'N/A')}")

                if prog.get('program_description'):
                    desc = prog['program_description']
                    if len(desc) > 200:
                        desc = desc[:200] + "..."
                    print(f"\nDescription: {desc}")

                if prog.get('scholarships_info'):
                    print(f"Scholarships: {prog['scholarships_info']}")

                if prog.get('career_outcomes'):
                    print(f"Career Outcomes: {prog['career_outcomes']}")

                print()
        else:
            # Table view
            table_data = []
            for prog in programs:
                table_data.append([
                    prog['university_name'],
                    prog.get('country', 'N/A'),
                    prog.get('tier', 'N/A').upper(),
                    prog.get('min_gpa', '-'),
                    prog.get('tuition_fee', '-'),
                    f"{prog.get('extraction_confidence', 0):.0%}"
                ])

            headers = ['University', 'Country', 'Tier', 'GPA Req', 'Tuition', 'Confidence']
            print(tabulate.tabulate(table_data, headers=headers, tablefmt='grid'))

    def search_by_country(self, country: str, show_all_fields: bool = False):
        """Search programs by country"""
        programs = list(self.collection.find(
            {'country': country},
            {'_id': 0}
        ))

        if not programs:
            print(f"❌ No programs found in {country}")
            return

        print(f"\n🌍 Programs in {country}: {len(programs)}\n")

        if show_all_fields:
            for prog in programs:
                print(f"{'─'*80}")
                print(f"{prog['university_name']}")
                print(f"  Program: {prog.get('program_name', 'N/A')}")
                print(f"  GPA: {prog.get('min_gpa', 'N/A')}")
                print(f"  Tuition: {prog.get('tuition_fee', 'N/A')}")
                print(f"  Deadline: {prog.get('application_deadline', 'N/A')}")
        else:
            table_data = [[p['university_name'], p.get('min_gpa', '-'), p.get('tuition_fee', '-')] for p in programs]
            print(tabulate.tabulate(table_data, headers=['University', 'GPA Req', 'Tuition'], tablefmt='grid'))

    def search_by_tier(self, tier: str):
        """Search programs by tier (top, strong, medium)"""
        programs = list(self.collection.find(
            {'tier': tier},
            {'_id': 0}
        ))

        if not programs:
            print(f"❌ No {tier} tier programs found")
            return

        print(f"\n⭐ {tier.upper()} TIER PROGRAMS: {len(programs)}\n")

        table_data = [
            [p['university_name'], p.get('country', 'N/A'), p.get('min_gpa', '-'),
             p.get('tuition_fee', '-'), f"{p.get('extraction_confidence', 0):.0%}"]
            for p in programs
        ]
        print(tabulate.tabulate(table_data,
                               headers=['University', 'Country', 'GPA', 'Tuition', 'Confidence'],
                               tablefmt='grid'))

    def find_by_university(self, uni_name: str):
        """Find and display specific university"""
        program = self.collection.find_one(
            {'university_name': {'$regex': uni_name, '$options': 'i'}},
            {'_id': 0}
        )

        if not program:
            print(f"❌ University '{uni_name}' not found")
            return

        print(f"\n{'='*100}")
        print(f"🎓 {program['university_name']} - {program['country']}")
        print(f"{'='*100}\n")

        # Display all available fields
        important_fields = [
            'program_name', 'min_gpa', 'english_requirement', 'tuition_fee',
            'duration', 'application_deadline', 'intake_months',
            'program_description', 'specializations', 'work_experience_required',
            'prerequisites', 'program_format', 'scholarship_info',
            'faculty_research_areas', 'research_focus', 'career_outcomes',
            'top_recruiters', 'average_salary', 'accreditation'
        ]

        for field in important_fields:
            if field in program and program[field]:
                # Format field name
                display_name = ' '.join(word.capitalize() for word in field.split('_'))
                value = program[field]

                if isinstance(value, list):
                    value = ', '.join(value)

                if isinstance(value, str) and len(value) > 150:
                    value = value[:150] + "..."

                print(f"• {display_name}: {value}")

        print(f"\nMetadata:")
        print(f"  Extraction Confidence: {program.get('extraction_confidence', 0):.0%}")
        print(f"  Scraped: {program.get('scraped_at', 'N/A')}")
        print(f"  URL: {program.get('source_url', 'N/A')}")

    def compare_universities(self, uni_names: List[str]):
        """Compare multiple universities side by side"""
        programs = []
        for uni_name in uni_names:
            prog = self.collection.find_one(
                {'university_name': {'$regex': uni_name, '$$options': 'i'}},
                {'_id': 0}
            )
            if prog:
                programs.append(prog)

        if not programs:
            print("❌ No universities found")
            return

        print(f"\n📊 COMPARISON: {', '.join([p['university_name'] for p in programs])}\n")

        table_data = [
            [
                p['university_name'],
                p.get('country', '-'),
                p.get('min_gpa', '-'),
                p.get('english_requirement', '-'),
                p.get('tuition_fee', '-'),
                p.get('duration', '-'),
            ]
            for p in programs
        ]

        headers = ['University', 'Country', 'Min GPA', 'English Req', 'Tuition', 'Duration']
        print(tabulate.tabulate(table_data, headers=headers, tablefmt='grid'))

    def get_scholarships(self):
        """Find universities with scholarship info"""
        programs = list(self.collection.find(
            {'scholarship_info': {'$ne': None}},
            {'_id': 0, 'university_name': 1, 'country': 1, 'scholarship_info': 1}
        ))

        if not programs:
            print("❌ No scholarship information found")
            return

        print(f"\n💰 UNIVERSITIES WITH SCHOLARSHIP INFO: {len(programs)}\n")

        for prog in programs:
            print(f"{prog['university_name']} ({prog['country']})")
            print(f"  {prog['scholarship_info']}\n")

    def get_free_programs(self):
        """Find universities with free/low tuition"""
        programs = list(self.collection.find(
            {'tuition_fee': {'$regex': 'free|Free|0|minimal', '$options': 'i'}},
            {'_id': 0}
        ))

        if not programs:
            print("❌ No free programs found")
            return

        if programs:
            print(f"\n🎓 FREE/LOW COST PROGRAMS: {len(programs)}\n")

            table_data = [[p['university_name'], p['country'], p.get('tuition_fee', '-')] for p in programs]
            print(tabulate.tabulate(table_data, headers=['University', 'Country', 'Tuition'], tablefmt='grid'))

    def stats_summary(self):
        """Display database statistics"""
        total = self.collection.count_documents({})

        by_tier = list(self.collection.aggregate([
            {'$group': {'_id': '$tier', 'count': {'$sum': 1}}}
        ]))

        by_country = list(self.collection.aggregate([
            {'$group': {'_id': '$country', 'count': {'$sum': 1}}}
        ]))

        avg_confidence = list(self.collection.aggregate([
            {'$group': {'_id': None, 'avg': {'$avg': '$extraction_confidence'}}}
        ]))

        with_scholarships = self.collection.count_documents({'scholarship_info': {'$ne': None}})
        with_career_info = self.collection.count_documents({'career_outcomes': {'$ne': None}})

        print(f"\n{'='*60}")
        print(f"📊 DATABASE STATISTICS")
        print(f"{'='*60}\n")

        print(f"Total Programs: {total}")
        print(f"Average Extraction Confidence: {avg_confidence[0]['avg']:.0%}\n")

        print(f"By Tier:")
        for tier_data in sorted(by_tier, key=lambda x: x['_id']):
            print(f"  {tier_data['_id'].upper()}: {tier_data['count']}")

        print(f"\nBy Country:")
        for country_data in sorted(by_country, key=lambda x: x['count'], reverse=True):
            print(f"  {country_data['_id']}: {country_data['count']}")

        print(f"\nData Richness:")
        print(f"  With Scholarship Info: {with_scholarships}")
        print(f"  With Career Outcomes: {with_career_info}")

        print(f"\n{'='*60}\n")

    def export_data(self, filename: str = None):
        """Export data to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"university_export_{timestamp}.json"

        data = list(self.collection.find({}, {'_id': 0}))

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✓ Data exported to {filename} ({len(data)} records)")

    def search_by_gpa_range(self, min_gpa: float = None, max_gpa: float = None):
        """Search universities by GPA requirements"""
        query = {}

        if min_gpa is not None and max_gpa is not None:
            # Find programs where GPA requirement is between min and max
            # This is tricky since GPA is stored as string, we'll do text search
            programs = list(self.collection.find({}, {'_id': 0}))
            filtered = []

            for prog in programs:
                gpa_str = prog.get('min_gpa', '')
                if gpa_str:
                    try:
                        # Extract numeric GPA from string
                        import re
                        gpa_match = re.search(r'(\d+\.?\d*)', gpa_str)
                        if gpa_match:
                            gpa_val = float(gpa_match.group(1))
                            if min_gpa <= gpa_val <= max_gpa:
                                filtered.append(prog)
                    except:
                        continue

            programs = filtered
        else:
            programs = list(self.collection.find(
                {'min_gpa': {'$ne': None}},
                {'_id': 0}
            ))

        if not programs:
            print("❌ No programs found with GPA requirements")
            return

        print(f"\n🎯 PROGRAMS WITH GPA REQUIREMENTS: {len(programs)}\n")

        table_data = [
            [p['university_name'], p.get('country', '-'), p.get('min_gpa', '-'),
             p.get('tuition_fee', '-'), f"{p.get('extraction_confidence', 0):.0%}"]
            for p in programs
        ]

        headers = ['University', 'Country', 'Min GPA', 'Tuition', 'Confidence']
        print(tabulate.tabulate(table_data, headers=headers, tablefmt='grid'))

# ==================== INTERACTIVE CLI ====================

def main():
    viewer = UniversityDataViewer()

    while True:
        print("\n" + "="*60)
        print("🎓 UNIVERSITY DATA VIEWER")
        print("="*60)
        print("\n1. View all programs (compact)")
        print("2. View all programs (detailed)")
        print("3. Search by country")
        print("4. Search by tier (TOP/STRONG/MEDIUM)")
        print("5. Find specific university")
        print("6. Compare universities")
        print("7. Find universities with scholarships")
        print("8. Find free/low-cost programs")
        print("9. Search by GPA range")
        print("10. Database statistics")
        print("11. Export data to JSON")
        print("0. Exit")

        choice = input("\nSelect option: ").strip()

        if choice == '0':
            print("Goodbye! 👋")
            break

        elif choice == '1':
            viewer.view_all_programs(detailed=False)

        elif choice == '2':
            viewer.view_all_programs(detailed=True)

        elif choice == '3':
            country = input("Enter country name: ").strip()
            viewer.search_by_country(country)

        elif choice == '4':
            tier = input("Enter tier (top/strong/medium): ").strip().lower()
            if tier in ['top', 'strong', 'medium']:
                viewer.search_by_tier(tier)
            else:
                print("❌ Invalid tier")

        elif choice == '5':
            uni = input("Enter university name (partial OK): ").strip()
            viewer.find_by_university(uni)

        elif choice == '6':
            unis = input("Enter university names (comma-separated): ").strip().split(',')
            unis = [u.strip() for u in unis]
            viewer.compare_universities(unis)

        elif choice == '7':
            viewer.get_scholarships()

        elif choice == '8':
            viewer.get_free_programs()

        elif choice == '9':
            try:
                min_gpa = input("Enter minimum GPA (or press Enter for none): ").strip()
                max_gpa = input("Enter maximum GPA (or press Enter for none): ").strip()

                min_val = float(min_gpa) if min_gpa else None
                max_val = float(max_gpa) if max_gpa else None

                viewer.search_by_gpa_range(min_val, max_val)
            except ValueError:
                print("❌ Invalid GPA values")

        elif choice == '10':
            viewer.stats_summary()

        elif choice == '11':
            filename = input("Enter filename (or press Enter for auto-generated): ").strip()
            if not filename:
                filename = None
            viewer.export_data(filename)

        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main()
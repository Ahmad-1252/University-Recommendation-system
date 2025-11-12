import asyncio
import logging
from pymongo import MongoClient, ASCENDING
from datetime import datetime, timedelta
import json
from typing import List, Dict
from crawl4ai import AsyncWebCrawler, CacheMode
from groq import Groq
from dotenv import load_dotenv
import os
from pprint import pprint

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ScraperMonitor:
    """Monitor and recover low-confidence or missing data"""

    def __init__(self):
        self.client = MongoClient(os.getenv('MONGODB_URI'))
        self.db = self.client[os.getenv('DATABASE_NAME', 'university_db')]
        self.collection = self.db[os.getenv('COLLECTION_NAME', 'programs')]
        self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        self.model = os.getenv('GROQ_MODEL', 'llama-3.1-70b-versatile')

    def analyze_data_quality(self):
        """Analyze current database for gaps and low-confidence entries"""
        logger.info("\n" + "="*80)
        logger.info("📊 DATA QUALITY ANALYSIS")
        logger.info("="*80)

        total = self.collection.count_documents({})
        logger.info(f"\n📦 Total Records: {total}")

        # Low confidence records
        low_conf = list(self.collection.find(
            {'extraction_confidence': {'$lt': 0.5}},
            {'university_name': 1, 'extraction_confidence': 1}
        ))

        if low_conf:
            logger.info(f"\n⚠ Low Confidence Records ({len(low_conf)}):")
            for record in low_conf:
                logger.info(f"   {record['university_name']}: {record['extraction_confidence']:.0%}")

        # Missing critical fields
        missing_gpa = self.collection.count_documents({'min_gpa': None})
        missing_tuition = self.collection.count_documents({'tuition_fee': None})
        missing_deadline = self.collection.count_documents({'application_deadline': None})

        logger.info(f"\n📋 Missing Critical Fields:")
        logger.info(f"   GPA Requirements: {missing_gpa}/{total}")
        logger.info(f"   Tuition Info: {missing_tuition}/{total}")
        logger.info(f"   Deadlines: {missing_deadline}/{total}")

        # Rich data (all major fields filled)
        rich_data = self.collection.count_documents({
            'min_gpa': {'$ne': None},
            'tuition_fee': {'$ne': None},
            'application_deadline': {'$ne': None},
            'program_description': {'$ne': None},
            'career_outcomes': {'$ne': None}
        })

        logger.info(f"   Rich Records (all major fields): {rich_data}/{total}")

        # By tier
        by_tier = list(self.collection.aggregate([
            {'$group': {'_id': '$tier', 'count': {'$sum': 1}}}
        ]))

        logger.info(f"\n📍 Records by Tier:")
        for tier_data in by_tier:
            logger.info(f"   {tier_data['_id'].upper()}: {tier_data['count']}")

        logger.info("="*80)

        return {
            'total': total,
            'low_conf': low_conf,
            'missing_gpa': missing_gpa,
            'missing_tuition': missing_tuition,
            'missing_deadline': missing_deadline,
            'rich_data': rich_data
        }

    async def fill_missing_data(self):
        """Attempt to fill missing critical data"""
        logger.info("\n" + "="*80)
        logger.info("🔧 FILLING MISSING DATA")
        logger.info("="*80)

        # Find records with missing critical info
        incomplete = list(self.collection.find({
            '$or': [
                {'min_gpa': None},
                {'tuition_fee': None},
                {'application_deadline': None}
            ]
        }))

        logger.info(f"\n🔍 Found {len(incomplete)} incomplete records")

        updated = 0
        for record in incomplete:
            result = await self._enrich_record(record)
            if result:
                updated += 1

        logger.info(f"✓ Updated {updated} records with new data")
        logger.info("="*80)

    async def _enrich_record(self, record):
        """Attempt to fill missing fields for a record"""
        url = record.get('source_url')
        uni_name = record.get('university_name')

        try:
            # Fetch fresh content
            async with AsyncWebCrawler(
                cache_type=CacheMode.DISABLED,
                verbose=False
            ) as crawler:
                result = await crawler.arun(
                    url=url,
                    timeout=30,
                    wait_until='networkidle'
                )

                if result.status_code != 200:
                    return None

                # Extract only missing fields
                missing_fields = {}
                if not record.get('min_gpa'):
                    missing_fields['min_gpa'] = True
                if not record.get('tuition_fee'):
                    missing_fields['tuition_fee'] = True
                if not record.get('application_deadline'):
                    missing_fields['application_deadline'] = True

                if not missing_fields:
                    return None

                # Use LLM to extract only what's missing
                enriched = await self._llm_enrich(
                    result.markdown,
                    uni_name,
                    list(missing_fields.keys())
                )

                if enriched:
                    # Update record
                    update_dict = {k: v for k, v in enriched.items() if v}
                    if update_dict:
                        self.collection.update_one(
                            {'_id': record['_id']},
                            {'$set': update_dict}
                        )
                        logger.info(f"   ✓ Updated {uni_name}: {list(update_dict.keys())}")
                        return True

        except Exception as e:
            logger.warning(f"   ✗ Enrichment failed for {uni_name}: {str(e)[:60]}")

        return None

    async def _llm_enrich(self, content: str, uni_name: str, missing_fields: List[str]) -> Dict:
        """Use LLM to extract only specific missing fields"""

        field_descriptions = {
            'min_gpa': 'Minimum GPA requirement',
            'tuition_fee': 'Annual tuition fee',
            'application_deadline': 'Application deadline or intake dates'
        }

        fields_to_extract = {k: field_descriptions[k] for k in missing_fields if k in field_descriptions}

        prompt = f"""Extract ONLY these specific fields from the content. Return ONLY JSON.

University: {uni_name}
Fields needed: {', '.join(fields_to_extract.keys())}

Content: {content[:10000]}

Return ONLY valid JSON with null for not found:
{{
    {', '.join(f'"{k}": null' for k in fields_to_extract.keys())}
}}"""

        try:
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.1
            )

            response_text = response.choices[0].message.content.strip()
            if '```json' in response_text:
                data = json.loads(response_text.split('```json')[1].split('```')[0].strip())
            else:
                data = json.loads(response_text)

            return data

        except Exception as e:
            logger.warning(f"   ⚠ LLM enrichment failed: {str(e)[:60]}")
            return None

    def export_for_analysis(self, filepath: str = "university_data.json"):
        """Export all data for analysis"""
        logger.info(f"\n💾 Exporting data to {filepath}")

        data = list(self.collection.find({}, {'_id': 0}))

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"   ✓ Exported {len(data)} records")

    def generate_confidence_report(self):
        """Generate confidence analysis report"""
        logger.info("\n" + "="*80)
        logger.info("📊 EXTRACTION CONFIDENCE REPORT")
        logger.info("="*80)

        records = list(self.collection.find({}))

        confidence_buckets = {
            '90-100%': 0,
            '70-90%': 0,
            '50-70%': 0,
            '<50%': 0
        }

        for record in records:
            conf = record.get('extraction_confidence', 0)
            if conf >= 0.9:
                confidence_buckets['90-100%'] += 1
            elif conf >= 0.7:
                confidence_buckets['70-90%'] += 1
            elif conf >= 0.5:
                confidence_buckets['50-70%'] += 1
            else:
                confidence_buckets['<50%'] += 1

        for bucket, count in confidence_buckets.items():
            pct = (count / len(records) * 100) if records else 0
            bar_length = int(pct / 5)
            bar = "█" * bar_length
            logger.info(f"   {bucket:10} {bar:20} {count:3} ({pct:5.1f}%)")

        logger.info("="*80)

    def get_universities_needing_retry(self) -> List[str]:
        """Get list of universities that should be retried"""

        low_conf = list(self.collection.find(
            {'extraction_confidence': {'$lt': 0.6}},
            {'university_name': 1, 'source_url': 1}
        ))

        return [(r['university_name'], r['source_url']) for r in low_conf]

    def show_data_gaps(self):
        """Show detailed data gaps analysis"""
        logger.info("\n" + "="*80)
        logger.info("🔍 DETAILED DATA GAPS ANALYSIS")
        logger.info("="*80)

        # Get all records
        records = list(self.collection.find({}))

        if not records:
            logger.info("❌ No data found in database")
            return

        # Analyze field completeness
        fields_to_check = [
            'program_name', 'min_gpa', 'english_requirement', 'tuition_fee',
            'duration', 'application_deadline', 'intake_months',
            'program_description', 'specializations', 'faculty_research_areas',
            'work_experience_required', 'prerequisites', 'program_format',
            'scholarship_info', 'career_outcomes', 'top_recruiters',
            'average_salary', 'accreditation'
        ]

        field_stats = {}
        for field in fields_to_check:
            filled = sum(1 for r in records if r.get(field))
            pct = filled / len(records) * 100
            field_stats[field] = {'filled': filled, 'total': len(records), 'percentage': pct}

        logger.info(f"\n📋 Field Completeness ({len(records)} records):")
        logger.info("-" * 60)

        for field, stats in sorted(field_stats.items(), key=lambda x: x[1]['percentage'], reverse=True):
            bar_length = int(stats['percentage'] / 5)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            field_name = field.replace('_', ' ').title()
            logger.info(f"   {field_name:25} {bar} {stats['filled']:2}/{stats['total']} ({stats['percentage']:5.1f}%)")

        logger.info("\n" + "="*80)

    def cleanup_duplicates(self):
        """Remove duplicate records based on university name"""
        logger.info("\n🧹 CLEANING UP DUPLICATES")

        # Find duplicates
        pipeline = [
            {'$group': {'_id': '$university_name', 'count': {'$sum': 1}, 'docs': {'$push': '$_id'}}},
            {'$match': {'count': {'$gt': 1}}}
        ]

        duplicates = list(self.collection.aggregate(pipeline))

        if not duplicates:
            logger.info("✓ No duplicates found")
            return

        logger.info(f"Found {len(duplicates)} universities with duplicates")

        removed = 0
        for dup in duplicates:
            uni_name = dup['_id']
            doc_ids = dup['docs']

            # Keep the one with highest confidence
            docs = list(self.collection.find({'_id': {'$in': doc_ids}}))
            docs.sort(key=lambda x: x.get('extraction_confidence', 0), reverse=True)

            # Remove all except the first (highest confidence)
            to_remove = [doc['_id'] for doc in docs[1:]]
            if to_remove:
                self.collection.delete_many({'_id': {'$in': to_remove}})
                removed += len(to_remove)
                logger.info(f"   Removed {len(to_remove)} duplicates for {uni_name}")

        logger.info(f"✓ Removed {removed} duplicate records")

async def main():
    monitor = ScraperMonitor()

    # Analyze quality
    quality = monitor.analyze_data_quality()

    # Show detailed gaps
    monitor.show_data_gaps()

    # Generate confidence report
    monitor.generate_confidence_report()

    # If data exists, try to fill gaps
    if quality['total'] > 0:
        # await monitor.fill_missing_data()
        pass

    # Clean up duplicates
    monitor.cleanup_duplicates()

    # Export for analysis
    monitor.export_for_analysis("university_data_export.json")

    # Get universities needing retry
    retry_list = monitor.get_universities_needing_retry()
    if retry_list:
        logger.info("\n" + "="*80)
        logger.info("🔄 UNIVERSITIES RECOMMENDED FOR RETRY:")
        logger.info("="*80)
        for uni, url in retry_list:
            logger.info(f"   {uni}")
            logger.info(f"      {url}")

    logger.info("\n✓ Monitoring complete\n")

if __name__ == "__main__":
    asyncio.run(main())
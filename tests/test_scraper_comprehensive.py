"""
Comprehensive Test Suite for University Recommendation System Scraper
Tests data gathering capabilities, validation, and generates a detailed success report
"""

import asyncio
import json
import time
import logging
import sys
from datetime import datetime
from typing import Dict, List, Any
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_report.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ScraperTestSuite:
    """Comprehensive test suite for the university scraper"""
    
    def __init__(self):
        """Initialize test suite"""
        self.test_results = {
            'tests': [],
            'summary': {},
            'timestamp': datetime.now().isoformat()
        }
        self.mongo_client = None
        self.db = None
        self.test_start_time = None
        self.test_end_time = None
        
    def setup(self) -> bool:
        """Setup test environment"""
        logger.info("=" * 80)
        logger.info("INITIALIZING TEST SUITE")
        logger.info("=" * 80)
        
        try:
            # Connect to MongoDB
            mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
            self.mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            
            # Verify connection
            self.mongo_client.admin.command('ping')
            logger.info("[OK] MongoDB connection established")
            
            # Get database
            self.db = self.mongo_client['university_scraper']
            logger.info("[OK] Database connected: university_scraper")
            
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to setup: {e}")
            return False
    
    def test_mongodb_connection(self) -> Dict[str, Any]:
        """Test 1: MongoDB Connection"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 1: MongoDB Connection")
        logger.info("=" * 80)
        
        try:
            start = time.time()
            self.mongo_client.admin.command('ping')
            duration = time.time() - start
            
            result = {
                'test': 'MongoDB Connection',
                'status': 'PASS',
                'duration_ms': duration * 1000,
                'details': 'Successfully connected to MongoDB'
            }
            logger.info(f"[PASS] Connection successful (Duration: {duration*1000:.2f}ms)")
            return result
            
        except Exception as e:
            result = {
                'test': 'MongoDB Connection',
                'status': 'FAIL',
                'error': str(e)
            }
            logger.error(f"[FAIL] {e}")
            return result
    
    def test_database_integrity(self) -> Dict[str, Any]:
        """Test 2: Database Integrity"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 2: Database Integrity")
        logger.info("=" * 80)
        
        try:
            collections = self.db.list_collection_names()
            logger.info(f"[OK] Found {len(collections)} collections: {collections}")
            
            # Check for programs collection
            if 'programs' in collections:
                logger.info("[OK] 'programs' collection exists")
                
                # Check collection stats
                programs_count = self.db['programs'].count_documents({})
                logger.info(f"[OK] Program records in database: {programs_count}")
                
                result = {
                    'test': 'Database Integrity',
                    'status': 'PASS',
                    'collections': collections,
                    'program_count': programs_count,
                    'details': f'Database is healthy with {programs_count} programs'
                }
                return result
            else:
                result = {
                    'test': 'Database Integrity',
                    'status': 'WARNING',
                    'collections': collections,
                    'details': 'Programs collection not found'
                }
                logger.warning("[WARNING] Programs collection not found")
                return result
                
        except Exception as e:
            result = {
                'test': 'Database Integrity',
                'status': 'FAIL',
                'error': str(e)
            }
            logger.error(f"[FAIL] {e}")
            return result
    
    def test_data_schema_validation(self) -> Dict[str, Any]:
        """Test 3: Data Schema Validation"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 3: Data Schema Validation")
        logger.info("=" * 80)
        
        try:
            collection = self.db['programs']
            sample_programs = list(collection.find().limit(10))
            
            if not sample_programs:
                result = {
                    'test': 'Data Schema Validation',
                    'status': 'WARNING',
                    'sample_count': 0,
                    'details': 'No programs found in database'
                }
                logger.warning("[WARNING] No programs in database")
                return result
            
            # Check schema
            required_fields = [
                'university_name',
                'program_name',
                'program_url',
                'country',
                'confidence_score'
            ]
            
            valid_count = 0
            invalid_programs = []
            
            for program in sample_programs:
                missing_fields = [f for f in required_fields if f not in program]
                if not missing_fields:
                    valid_count += 1
                else:
                    invalid_programs.append({
                        'program_name': program.get('program_name', 'Unknown'),
                        'missing_fields': missing_fields
                    })
            
            logger.info(f"[OK] Validated {len(sample_programs)} sample programs")
            logger.info(f"[OK] Valid records: {valid_count}/{len(sample_programs)}")
            
            if invalid_programs:
                logger.warning(f"[WARNING] {len(invalid_programs)} programs with missing fields")
                for prog in invalid_programs[:3]:  # Show first 3
                    logger.warning(f"  - {prog['program_name']}: Missing {prog['missing_fields']}")
            
            result = {
                'test': 'Data Schema Validation',
                'status': 'PASS' if valid_count == len(sample_programs) else 'WARNING',
                'total_checked': len(sample_programs),
                'valid_count': valid_count,
                'invalid_count': len(invalid_programs),
                'details': f'{valid_count}/{len(sample_programs)} records are valid'
            }
            return result
            
        except Exception as e:
            result = {
                'test': 'Data Schema Validation',
                'status': 'FAIL',
                'error': str(e)
            }
            logger.error(f"[FAIL] {e}")
            return result
    
    def test_data_extraction_coverage(self) -> Dict[str, Any]:
        """Test 4: Data Extraction Coverage"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 4: Data Extraction Coverage")
        logger.info("=" * 80)
        
        try:
            collection = self.db['programs']
            
            # Universities expected to have data
            expected_universities = [
                'Harvard University',
                'Stanford University',
                'University of Cambridge',
                'University of Oxford',
                'Imperial College London',
                'ETH Zurich',
                'EPFL',
                'Technical University of Munich',
                'University of Toronto',
                'University of British Columbia',
                'Australian National University',
                'Peking University',
                'Tsinghua University'
            ]
            
            coverage_data = []
            total_programs = 0
            
            for uni in expected_universities:
                count = collection.count_documents({'university_name': uni})
                status = 'OK' if count > 0 else 'NO DATA'
                coverage_data.append({
                    'university': uni,
                    'program_count': count,
                    'status': status
                })
                total_programs += count
                logger.info(f"[{status}] {uni}: {count} programs")
            
            universities_with_data = sum(1 for c in coverage_data if c['program_count'] > 0)
            coverage_percentage = (universities_with_data / len(expected_universities)) * 100
            
            logger.info(f"\n[OK] Coverage: {universities_with_data}/{len(expected_universities)} universities")
            logger.info(f"[OK] Total programs: {total_programs}")
            logger.info(f"[OK] Coverage percentage: {coverage_percentage:.1f}%")
            
            result = {
                'test': 'Data Extraction Coverage',
                'status': 'PASS' if coverage_percentage >= 70 else 'WARNING',
                'universities_with_data': universities_with_data,
                'total_universities': len(expected_universities),
                'coverage_percentage': coverage_percentage,
                'total_programs_extracted': total_programs,
                'details': f'{universities_with_data} out of {len(expected_universities)} universities have data'
            }
            return result
            
        except Exception as e:
            result = {
                'test': 'Data Extraction Coverage',
                'status': 'FAIL',
                'error': str(e)
            }
            logger.error(f"[FAIL] {e}")
            return result
    
    def test_data_quality_metrics(self) -> Dict[str, Any]:
        """Test 5: Data Quality Metrics"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 5: Data Quality Metrics")
        logger.info("=" * 80)
        
        try:
            collection = self.db['programs']
            programs = list(collection.find().limit(100))
            
            if not programs:
                result = {
                    'test': 'Data Quality Metrics',
                    'status': 'WARNING',
                    'details': 'No programs to analyze'
                }
                logger.warning("[WARNING] No programs to analyze")
                return result
            
            # Analyze data quality
            metrics = {
                'total_analyzed': len(programs),
                'avg_confidence_score': 0.0,
                'programs_with_description': 0,
                'programs_with_duration': 0,
                'programs_with_requirements': 0,
                'programs_with_fees': 0,
                'programs_with_deadline': 0,
                'unique_countries': set(),
                'unique_universities': set()
            }
            
            confidence_scores = []
            
            for prog in programs:
                # Confidence score
                if 'confidence_score' in prog:
                    confidence_scores.append(prog['confidence_score'])
                
                # Field coverage
                if prog.get('description'):
                    metrics['programs_with_description'] += 1
                if prog.get('duration'):
                    metrics['programs_with_duration'] += 1
                if prog.get('admission_requirements'):
                    metrics['programs_with_requirements'] += 1
                if prog.get('tuition_fees'):
                    metrics['programs_with_fees'] += 1
                if prog.get('application_deadline'):
                    metrics['programs_with_deadline'] += 1
                
                # Unique values
                if 'country' in prog:
                    metrics['unique_countries'].add(prog['country'])
                if 'university_name' in prog:
                    metrics['unique_universities'].add(prog['university_name'])
            
            # Calculate averages
            if confidence_scores:
                metrics['avg_confidence_score'] = sum(confidence_scores) / len(confidence_scores)
            
            metrics['unique_countries'] = len(metrics['unique_countries'])
            metrics['unique_universities'] = len(metrics['unique_universities'])
            
            # Log metrics
            logger.info(f"[OK] Programs analyzed: {metrics['total_analyzed']}")
            logger.info(f"[OK] Average confidence score: {metrics['avg_confidence_score']:.2f}")
            logger.info(f"[OK] Programs with description: {metrics['programs_with_description']}/{metrics['total_analyzed']}")
            logger.info(f"[OK] Programs with duration: {metrics['programs_with_duration']}/{metrics['total_analyzed']}")
            logger.info(f"[OK] Programs with requirements: {metrics['programs_with_requirements']}/{metrics['total_analyzed']}")
            logger.info(f"[OK] Programs with fees: {metrics['programs_with_fees']}/{metrics['total_analyzed']}")
            logger.info(f"[OK] Programs with deadline: {metrics['programs_with_deadline']}/{metrics['total_analyzed']}")
            logger.info(f"[OK] Unique countries: {metrics['unique_countries']}")
            logger.info(f"[OK] Unique universities: {metrics['unique_universities']}")
            
            # Calculate overall quality score (0-100)
            field_coverage_score = (
                (metrics['programs_with_description'] / metrics['total_analyzed']) * 20 +
                (metrics['programs_with_duration'] / metrics['total_analyzed']) * 20 +
                (metrics['programs_with_requirements'] / metrics['total_analyzed']) * 20 +
                (metrics['programs_with_fees'] / metrics['total_analyzed']) * 20 +
                (metrics['programs_with_deadline'] / metrics['total_analyzed']) * 20
            )
            
            overall_quality = (metrics['avg_confidence_score'] * 50) + (field_coverage_score / 5 * 50)
            
            result = {
                'test': 'Data Quality Metrics',
                'status': 'PASS' if overall_quality >= 60 else 'WARNING',
                'metrics': {
                    'total_analyzed': metrics['total_analyzed'],
                    'avg_confidence_score': round(metrics['avg_confidence_score'], 2),
                    'description_coverage': f"{(metrics['programs_with_description']/metrics['total_analyzed']*100):.1f}%",
                    'duration_coverage': f"{(metrics['programs_with_duration']/metrics['total_analyzed']*100):.1f}%",
                    'requirements_coverage': f"{(metrics['programs_with_requirements']/metrics['total_analyzed']*100):.1f}%",
                    'fees_coverage': f"{(metrics['programs_with_fees']/metrics['total_analyzed']*100):.1f}%",
                    'deadline_coverage': f"{(metrics['programs_with_deadline']/metrics['total_analyzed']*100):.1f}%",
                    'unique_countries': metrics['unique_countries'],
                    'unique_universities': metrics['unique_universities']
                },
                'overall_quality_score': round(overall_quality, 2),
                'details': f'Data quality score: {overall_quality:.1f}/100'
            }
            
            logger.info(f"\n[OK] Overall Data Quality Score: {overall_quality:.1f}/100")
            return result
            
        except Exception as e:
            result = {
                'test': 'Data Quality Metrics',
                'status': 'FAIL',
                'error': str(e)
            }
            logger.error(f"[FAIL] {e}")
            return result
    
    def test_groq_api_integration(self) -> Dict[str, Any]:
        """Test 6: Groq API Integration"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 6: Groq API Integration")
        logger.info("=" * 80)
        
        try:
            from groq import Groq
            
            api_key = os.getenv('GROQ_API_KEY')
            if not api_key:
                result = {
                    'test': 'Groq API Integration',
                    'status': 'FAIL',
                    'error': 'GROQ_API_KEY not set'
                }
                logger.error("[FAIL] GROQ_API_KEY not configured")
                return result
            
            client = Groq(api_key=api_key)
            
            # Test API call
            start = time.time()
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "user", "content": "Say 'API working' only"}
                ],
                max_tokens=20
            )
            duration = time.time() - start
            
            result_text = response.choices[0].message.content.strip()
            logger.info(f"[OK] API response: {result_text}")
            logger.info(f"[OK] Response time: {duration*1000:.2f}ms")
            
            result = {
                'test': 'Groq API Integration',
                'status': 'PASS',
                'model': 'llama-3.1-8b-instant',
                'response_time_ms': duration * 1000,
                'details': 'Groq API is working correctly'
            }
            return result
            
        except Exception as e:
            result = {
                'test': 'Groq API Integration',
                'status': 'FAIL',
                'error': str(e)
            }
            logger.error(f"[FAIL] {e}")
            return result
    
    def test_network_connectivity(self) -> Dict[str, Any]:
        """Test 7: Network Connectivity"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 7: Network Connectivity")
        logger.info("=" * 80)
        
        try:
            import requests
            
            urls_to_test = [
                ('Harvard', 'https://www.harvard.edu/'),
                ('Google', 'https://www.google.com/'),
                ('Groq API', 'https://api.groq.com/')
            ]
            
            results = []
            for name, url in urls_to_test:
                try:
                    start = time.time()
                    response = requests.head(url, timeout=5)
                    duration = time.time() - start
                    status_code = response.status_code
                    results.append({
                        'name': name,
                        'url': url,
                        'status_code': status_code,
                        'response_time_ms': duration * 1000,
                        'status': 'OK' if status_code < 400 else 'SLOW'
                    })
                    logger.info(f"[OK] {name}: {status_code} ({duration*1000:.2f}ms)")
                except Exception as e:
                    results.append({
                        'name': name,
                        'url': url,
                        'status': 'FAIL',
                        'error': str(e)
                    })
                    logger.warning(f"[WARNING] {name}: {e}")
            
            successful = sum(1 for r in results if r.get('status') in ['OK', 'SLOW'])
            
            result = {
                'test': 'Network Connectivity',
                'status': 'PASS' if successful >= 2 else 'WARNING',
                'endpoints_tested': len(results),
                'endpoints_working': successful,
                'details': f'{successful}/{len(results)} endpoints reachable'
            }
            return result
            
        except Exception as e:
            result = {
                'test': 'Network Connectivity',
                'status': 'WARNING',
                'error': str(e)
            }
            logger.error(f"[WARNING] {e}")
            return result
    
    def run_all_tests(self) -> bool:
        """Run all tests"""
        self.test_start_time = time.time()
        
        if not self.setup():
            logger.error("Setup failed, cannot proceed with tests")
            return False
        
        tests = [
            self.test_mongodb_connection,
            self.test_database_integrity,
            self.test_data_schema_validation,
            self.test_data_extraction_coverage,
            self.test_data_quality_metrics,
            self.test_groq_api_integration,
            self.test_network_connectivity
        ]
        
        for test_func in tests:
            try:
                result = test_func()
                self.test_results['tests'].append(result)
            except Exception as e:
                logger.error(f"Test {test_func.__name__} failed: {e}")
                self.test_results['tests'].append({
                    'test': test_func.__name__,
                    'status': 'FAIL',
                    'error': str(e)
                })
        
        self.test_end_time = time.time()
        return True
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        passed = sum(1 for t in self.test_results['tests'] if t.get('status') == 'PASS')
        failed = sum(1 for t in self.test_results['tests'] if t.get('status') == 'FAIL')
        warnings = sum(1 for t in self.test_results['tests'] if t.get('status') == 'WARNING')
        total = len(self.test_results['tests'])
        
        self.test_results['summary'] = {
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'warnings': warnings,
            'success_rate': f"{(passed/total)*100:.1f}%" if total > 0 else "0%",
            'duration_seconds': self.test_end_time - self.test_start_time if self.test_end_time else 0,
            'timestamp': datetime.now().isoformat()
        }
        
        return self.test_results
    
    def print_report(self):
        """Print formatted test report"""
        report = self.generate_report()
        summary = report['summary']
        
        print("\n" + "=" * 80)
        print("COMPREHENSIVE TEST REPORT - UNIVERSITY SCRAPER")
        print("=" * 80)
        print(f"\nTest Execution Time: {report['timestamp']}")
        print(f"Total Duration: {summary['duration_seconds']:.2f} seconds")
        print(f"\nTest Results:")
        print(f"  ✓ Passed:   {summary['passed']}/{summary['total_tests']}")
        print(f"  ✗ Failed:   {summary['failed']}/{summary['total_tests']}")
        print(f"  ⚠ Warnings: {summary['warnings']}/{summary['total_tests']}")
        print(f"  Success Rate: {summary['success_rate']}")
        
        print(f"\nDetailed Results:")
        print("-" * 80)
        
        for test in report['tests']:
            status_symbol = "✓" if test.get('status') == 'PASS' else "✗" if test.get('status') == 'FAIL' else "⚠"
            print(f"\n{status_symbol} {test.get('test', 'Unknown Test')}")
            print(f"  Status: {test.get('status')}")
            
            if test.get('details'):
                print(f"  Details: {test.get('details')}")
            
            if test.get('metrics'):
                print(f"  Metrics:")
                for key, value in test['metrics'].items():
                    print(f"    - {key}: {value}")
            
            if test.get('error'):
                print(f"  Error: {test.get('error')}")
        
        print("\n" + "=" * 80)
        print("END OF REPORT")
        print("=" * 80 + "\n")
    
    def save_report_json(self, filename: str = "test_report.json"):
        """Save report as JSON"""
        report = self.generate_report()
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Report saved to {filename}")
    
    def cleanup(self):
        """Cleanup resources"""
        if self.mongo_client:
            self.mongo_client.close()
            logger.info("MongoDB connection closed")


def main():
    """Main test execution"""
    test_suite = ScraperTestSuite()
    
    try:
        # Run all tests
        test_suite.run_all_tests()
        
        # Generate and print report
        test_suite.print_report()
        
        # Save report
        test_suite.save_report_json()
        
        # Return exit code based on results
        summary = test_suite.test_results['summary']
        if summary['failed'] > 0:
            return 1
        else:
            return 0
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return 1
    finally:
        test_suite.cleanup()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

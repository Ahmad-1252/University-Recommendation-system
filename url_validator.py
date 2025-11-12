import asyncio
import aiohttp
import logging
from typing import List, Tuple, Dict, Optional
from urllib.parse import urlparse, urljoin
from enum import Enum
from dotenv import load_dotenv
import os
from tqdm.asyncio import tqdm
import json
from datetime import datetime

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('url_validator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ValidationResult(Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"
    FORBIDDEN = "forbidden"
    SERVER_ERROR = "server_error"
    CONNECTION_ERROR = "connection_error"
    REDIRECT = "redirect"
    UNKNOWN = "unknown"

class URLValidator:
    def __init__(self):
        self.timeout = int(os.getenv('VALIDATION_TIMEOUT', '15'))
        self.max_redirects = int(os.getenv('MAX_REDIRECTS', '5'))
        self.user_agent = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    async def validate_url(self, url: str) -> Tuple[ValidationResult, Optional[str], Optional[int]]:
        """Validate a single URL and return result, final URL, and status code"""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={'User-Agent': self.user_agent}
            ) as session:
                async with session.get(url, allow_redirects=True, max_redirects=self.max_redirects) as response:
                    final_url = str(response.url)

                    if response.status == 200:
                        return ValidationResult.SUCCESS, final_url, response.status
                    elif response.status == 301 or response.status == 302:
                        return ValidationResult.REDIRECT, final_url, response.status
                    elif response.status == 403:
                        return ValidationResult.FORBIDDEN, final_url, response.status
                    elif response.status == 404:
                        return ValidationResult.NOT_FOUND, final_url, response.status
                    elif response.status >= 500:
                        return ValidationResult.SERVER_ERROR, final_url, response.status
                    else:
                        return ValidationResult.UNKNOWN, final_url, response.status

        except asyncio.TimeoutError:
            return ValidationResult.TIMEOUT, None, None
        except aiohttp.ClientError as e:
            logger.warning(f"Connection error for {url}: {str(e)}")
            return ValidationResult.CONNECTION_ERROR, None, None
        except Exception as e:
            logger.error(f"Unexpected error validating {url}: {str(e)}")
            return ValidationResult.UNKNOWN, None, None

    async def validate_universities(self, universities: List[Tuple[str, str, str, str]]) -> Dict:
        """Validate all university URLs"""
        logger.info(f"\n🔍 VALIDATING {len(universities)} UNIVERSITY URLs")
        logger.info("="*80)

        results = {}
        tasks = []

        for name, country, tier, url in universities:
            tasks.append(self._validate_single_university(name, country, tier, url))

        # Process with progress bar
        validation_results = await tqdm.gather(*tasks, desc="Validating URLs")

        # Organize results
        for result in validation_results:
            results.update(result)

        return results

    async def _validate_single_university(self, name: str, country: str, tier: str, url: str) -> Dict:
        """Validate a single university URL with suggestions"""
        logger.info(f"🔗 Testing: {name} ({country}) - {tier.upper()}")

        result, final_url, status_code = await self.validate_url(url)

        university_result = {
            name: {
                'original_url': url,
                'result': result.value,
                'final_url': final_url,
                'status_code': status_code,
                'country': country,
                'tier': tier,
                'suggestions': []
            }
        }

        # Generate suggestions for failed URLs
        if result != ValidationResult.SUCCESS:
            suggestions = await self._generate_url_suggestions(url, name)
            university_result[name]['suggestions'] = suggestions

        # Log result
        if result == ValidationResult.SUCCESS:
            logger.info(f"   ✓ SUCCESS: {status_code}")
        elif result == ValidationResult.REDIRECT:
            logger.info(f"   ↪ REDIRECT: {status_code} → {final_url}")
        elif result == ValidationResult.TIMEOUT:
            logger.warning(f"   ⏱ TIMEOUT: No response within {self.timeout}s")
        elif result == ValidationResult.NOT_FOUND:
            logger.warning(f"   ✗ NOT FOUND: {status_code}")
        elif result == ValidationResult.FORBIDDEN:
            logger.warning(f"   🚫 FORBIDDEN: {status_code}")
        else:
            logger.warning(f"   ⚠ {result.value.upper()}: {status_code}")

        if university_result[name]['suggestions']:
            logger.info(f"   💡 Suggestions: {len(university_result[name]['suggestions'])} alternatives")

        return university_result

    async def _generate_url_suggestions(self, original_url: str, university_name: str) -> List[str]:
        """Generate alternative URL suggestions"""
        suggestions = []
        parsed = urlparse(original_url)

        # Common university URL patterns
        base_patterns = [
            "/admissions",
            "/admissions/graduate",
            "/study/postgraduate",
            "/prospective-students",
            "/prospective-students/graduate",
            "/education",
            "/education/graduate",
            "/programs",
            "/programs/graduate",
            "/academics",
            "/graduate-study",
            "/postgraduate",
            "/masters",
            "/msc",
            "/computer-science",
            "/computing"
        ]

        # Try different base URLs
        base_urls = [
            f"https://{parsed.netloc}",
            f"https://www.{parsed.netloc.replace('www.', '')}",
            f"https://{parsed.netloc.replace('www.', '')}"
        ]

        for base in base_urls:
            for pattern in base_patterns:
                suggestion = urljoin(base, pattern)
                if suggestion != original_url:
                    suggestions.append(suggestion)

        # University-specific patterns
        uni_specific = self._get_university_specific_patterns(university_name, parsed.netloc)
        suggestions.extend(uni_specific)

        # Remove duplicates and limit to top 10
        suggestions = list(set(suggestions))[:10]

        # Validate suggestions (check if they exist)
        valid_suggestions = []
        for suggestion in suggestions[:5]:  # Only check first 5
            try:
                result, _, status = await self.validate_url(suggestion)
                if result == ValidationResult.SUCCESS:
                    valid_suggestions.append(suggestion)
            except:
                continue

        return valid_suggestions[:3]  # Return top 3 working suggestions

    def _get_university_specific_patterns(self, university_name: str, domain: str) -> List[str]:
        """Generate university-specific URL patterns"""
        patterns = []

        # Oxford
        if 'oxford' in university_name.lower():
            patterns.extend([
                "https://www.cs.ox.ac.uk/admissions/msc-programs/",
                "https://www.ox.ac.uk/study/graduate-study",
                "https://www.cs.ox.ac.uk/graduate-study"
            ])

        # Cambridge
        elif 'cambridge' in university_name.lower():
            patterns.extend([
                "https://www.cam.ac.uk/study-at-cambridge",
                "https://www.cst.cam.ac.uk/prospective/postgraduate",
                "https://www.cl.cam.ac.uk/admissions/mphil/"
            ])

        # Imperial
        elif 'imperial' in university_name.lower():
            patterns.extend([
                "https://www.imperial.ac.uk/study/pg/computing/",
                "https://www.imperial.ac.uk/computing/prospective-students/",
                "https://www.imperial.ac.uk/study/postgraduate-2024/"
            ])

        # ETH Zurich
        elif 'eth' in university_name.lower():
            patterns.extend([
                "https://www.inf.ethz.ch/studies/master.html",
                "https://www.ethz.ch/en/studies/master.html",
                "https://www.ethz.ch/en/studies/en/master/computer-science.html"
            ])

        # UCL
        elif 'ucl' in university_name.lower():
            patterns.extend([
                "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/msc-computer-science",
                "https://www.ucl.ac.uk/study/graduate-programmes",
                "https://www.cs.ucl.ac.uk/prospective_students/msc/"
            ])

        # Generic patterns for other universities
        else:
            base = f"https://{domain}"
            patterns.extend([
                f"{base}/study/postgraduate",
                f"{base}/admissions/graduate",
                f"{base}/prospective/postgraduate",
                f"{base}/education/postgraduate"
            ])

        return patterns

    def generate_report(self, results: Dict) -> str:
        """Generate a comprehensive validation report"""
        report = []
        report.append("="*80)
        report.append("📊 URL VALIDATION REPORT")
        report.append("="*80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Summary statistics
        total = len(results)
        success_count = sum(1 for r in results.values() if r['result'] == 'success')
        redirect_count = sum(1 for r in results.values() if r['result'] == 'redirect')
        error_count = total - success_count - redirect_count

        report.append("📈 SUMMARY STATISTICS")
        report.append("-" * 40)
        report.append(f"Total URLs tested: {total}")
        report.append(f"✓ Working URLs: {success_count} ({success_count/total*100:.1f}%)")
        report.append(f"↪ Redirects: {redirect_count} ({redirect_count/total*100:.1f}%)")
        report.append(f"✗ Errors: {error_count} ({error_count/total*100:.1f}%)")
        report.append("")

        # By tier
        tiers = {}
        for uni_data in results.values():
            tier = uni_data['tier']
            result = uni_data['result']
            if tier not in tiers:
                tiers[tier] = {'total': 0, 'success': 0}
            tiers[tier]['total'] += 1
            if result == 'success':
                tiers[tier]['success'] += 1

        report.append("📍 BY TIER")
        report.append("-" * 40)
        for tier, stats in sorted(tiers.items()):
            pct = stats['success'] / stats['total'] * 100
            report.append(f"{tier.upper()}: {stats['success']}/{stats['total']} ({pct:.1f}%)")
        report.append("")

        # Detailed results
        report.append("🔍 DETAILED RESULTS")
        report.append("-" * 40)

        # Successful URLs
        successful = [(name, data) for name, data in results.items() if data['result'] == 'success']
        if successful:
            report.append("\n✓ SUCCESSFUL URLs:")
            for name, data in successful:
                report.append(f"  • {name} ({data['country']})")
                if data['final_url'] != data['original_url']:
                    report.append(f"    ↪ {data['final_url']}")

        # Redirected URLs
        redirected = [(name, data) for name, data in results.items() if data['result'] == 'redirect']
        if redirected:
            report.append("\n↪ REDIRECTED URLs:")
            for name, data in redirected:
                report.append(f"  • {name} ({data['country']})")
                report.append(f"    {data['original_url']}")
                report.append(f"    ↪ {data['final_url']}")

        # Failed URLs with suggestions
        failed = [(name, data) for name, data in results.items() if data['result'] not in ['success', 'redirect']]
        if failed:
            report.append("\n✗ FAILED URLs:")
            for name, data in failed:
                report.append(f"  • {name} ({data['country']}) - {data['result'].upper()}")
                report.append(f"    {data['original_url']}")

                if data['suggestions']:
                    report.append("    💡 Suggested alternatives:")
                    for i, suggestion in enumerate(data['suggestions'][:3], 1):
                        report.append(f"      {i}. {suggestion}")

        report.append("")
        report.append("="*80)

        return "\n".join(report)

    def export_results(self, results: Dict, filename: str = "url_validation_results.json"):
        """Export validation results to JSON"""
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': len(results),
                'successful': sum(1 for r in results.values() if r['result'] == 'success'),
                'redirected': sum(1 for r in results.values() if r['result'] == 'redirect'),
                'failed': sum(1 for r in results.values() if r['result'] not in ['success', 'redirect'])
            },
            'results': results
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Results exported to {filename}")

# ==================== MAIN ====================

# Import universities from the enhanced scraper
try:
    from uni_scraper_enhanced import UNIVERSITIES
except ImportError:
    # Fallback if the enhanced scraper isn't available
    from enum import Enum
    class UniversityTier(str, Enum):
        TOP = "top"
        STRONG = "strong"
        MEDIUM = "medium"

    UNIVERSITIES = [
        # TOP TIER
        ("University of Oxford", "UK", UniversityTier.TOP, "https://www.cs.ox.ac.uk/admissions/msc-programs/"),
        ("University of Cambridge", "UK", UniversityTier.TOP, "https://www.cam.ac.uk/postgraduate/"),
        ("Imperial College London", "UK", UniversityTier.TOP, "https://www.imperial.ac.uk/study/pg/computing/"),
        ("ETH Zurich", "Switzerland", UniversityTier.TOP, "https://www.inf.ethz.ch/studies/master.html"),
        ("UCL", "UK", UniversityTier.TOP, "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/msc-computer-science"),
        ("Université PSL", "France", UniversityTier.TOP, "https://www.psl.eu/programs"),
        ("Technical University of Munich", "Germany", UniversityTier.TOP, "https://www.in.tum.de/master-programs/"),
        ("EPFL", "Switzerland", UniversityTier.TOP, "https://www.epfl.ch/en/education/master/"),

        # STRONG TIER
        ("University of Edinburgh", "UK", UniversityTier.STRONG, "https://www.ed.ac.uk/studying/postgraduate/degrees"),
        ("University of Manchester", "UK", UniversityTier.STRONG, "https://www.manchester.ac.uk/study/postgraduate/"),
        ("King's College London", "UK", UniversityTier.STRONG, "https://www.kcl.ac.uk/admissions/graduate"),
        ("Delft University of Technology", "Netherlands", UniversityTier.STRONG, "https://www.tudelft.nl/en/education/programmes/masters/cse/msc-computer-science/"),
        ("University of Glasgow", "UK", UniversityTier.STRONG, "https://www.gla.ac.uk/postgraduate/"),
        ("University of Leeds", "UK", UniversityTier.STRONG, "https://www.leeds.ac.uk/postgraduate"),
        ("University of Amsterdam", "Netherlands", UniversityTier.STRONG, "https://www.uva.nl/en/education/master-s-degrees"),
        ("LMU Munich", "Germany", UniversityTier.STRONG, "https://www.en.uni-muenchen.de/students/"),
        ("University of Warwick", "UK", UniversityTier.STRONG, "https://warwick.ac.uk/study/postgraduate/"),
        ("Heidelberg University", "Germany", UniversityTier.STRONG, "https://www.uni-heidelberg.de/en/studies"),

        # MEDIUM TIER
        ("Utrecht University", "Netherlands", UniversityTier.MEDIUM, "https://www.uu.nl/en/masters"),
        ("University of Tartu", "Estonia", UniversityTier.MEDIUM, "https://www.ut.ee/en/admissions"),
        ("National and Kapodistrian University of Athens", "Greece", UniversityTier.MEDIUM, "https://www.uoa.gr/"),
        ("KU Leuven", "Belgium", UniversityTier.MEDIUM, "https://www.kuleuven.be/english/admissions"),
        ("Leiden University", "Netherlands", UniversityTier.MEDIUM, "https://www.universiteitleiden.nl/en/admissions"),
    ]

async def main():
    logger.info("\n🚀 UNIVERSITY URL VALIDATOR")
    logger.info("="*80)

    validator = URLValidator()

    # Validate all URLs
    results = await validator.validate_universities(UNIVERSITIES)

    # Generate and display report
    report = validator.generate_report(results)
    print(report)

    # Export results
    validator.export_results(results)

    logger.info("\n✓ URL validation complete!")
    logger.info("📄 Check 'url_validation_results.json' for detailed results")
    logger.info("📋 Review the report above for suggested fixes")

if __name__ == "__main__":
    asyncio.run(main())
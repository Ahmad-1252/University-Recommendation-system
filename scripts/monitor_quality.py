#!/usr/bin/env python3
"""Quality monitoring script for university program data."""

import logging
import sys
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.analyzers.quality_analyzer import QualityAnalyzer
from src.core.config import get_settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/quality_monitor.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main quality monitoring function."""
    settings = get_settings()

    logger.info("Starting quality monitoring")

    try:
        analyzer = QualityAnalyzer()

        # Generate comprehensive quality report
        report = analyzer.generate_quality_report()

        # Save report to file
        reports_dir = Path("data/exports")
        reports_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"quality_report_{timestamp}.json"

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Quality report saved to: {report_file}")

        # Print summary to console
        summary = report['summary']
        print("\n" + "="*50)
        print("QUALITY MONITORING REPORT")
        print("="*50)
        print(f"Generated: {report['generated_at']}")
        print(f"Total Programs: {summary['total_programs']}")
        print(".1f")
        print(".1f")
        print(f"Critical Issues: {summary['critical_issues']}")
        print(f"Recommendations: {summary['recommendations_count']}")
        print()

        # Show top issues
        if report['quality_analysis']['issues_found']:
            print("TOP ISSUES:")
            for issue in report['quality_analysis']['issues_found'][:5]:
                print(f"• {issue}")
            print()

        # Show recommendations
        if report['quality_analysis']['recommendations']:
            print("RECOMMENDATIONS:")
            for rec in report['quality_analysis']['recommendations'][:5]:
                print(f"• {rec}")
            print()

        # Coverage analysis
        coverage = report['coverage_analysis']
        if 'total_programs' in coverage:
            print("COVERAGE ANALYSIS:")
            print(f"• Universities Covered: {coverage['universities_covered']}")
            print(f"• Countries Covered: {coverage['countries_covered']}")
            print()

        # Freshness analysis
        freshness = report['freshness_analysis']
        print("DATA FRESHNESS:")
        print(f"• Fresh Programs (30 days): {freshness['fresh_programs']}")
        print(f"• Stale Programs: {freshness['stale_programs']}")
        print(".1f")
        print()

        print(f"Full report saved to: {report_file}")

    except Exception as e:
        logger.error(f"Quality monitoring failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
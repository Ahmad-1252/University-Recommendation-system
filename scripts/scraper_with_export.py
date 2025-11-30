"""
Enhanced Scraper with integrated data export to CSV, Excel, and MongoDB
This version ensures data is saved in multiple formats automatically
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main scraper
from uni_scraper_enhanced import EnhancedUniversityScraper, logger
from data_exporter import UniversityDataExporter
import time


async def scrape_and_export():
    """
    Main function that scrapes universities and exports data to all formats
    """
    start_time = time.time()
    
    logger.info("=" * 80)
    logger.info("STARTING SCRAPER WITH AUTOMATIC DATA EXPORT")
    logger.info("=" * 80)

    # Initialize scraper
    try:
        scraper = EnhancedUniversityScraper()
        logger.info("✓ Scraper initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize scraper: {e}")
        return

    # Initialize exporter
    try:
        exporter = UniversityDataExporter()
        if not exporter.connect_mongodb():
            logger.warning("⚠ MongoDB connection failed - will still export to files")
        logger.info("✓ Data exporter initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize exporter: {e}")
        return

    # Run the scraping process
    try:
        logger.info("Starting scraping process for all universities...")
        summary = await scraper.scrape_all_universities()

        # Update processing time
        summary['processing_time_seconds'] = time.time() - start_time

        # Display results
        logger.info("\n" + "=" * 80)
        logger.info("SCRAPING RESULTS")
        logger.info("=" * 80)
        logger.info(f"Universities processed: {summary['total_universities']}")
        logger.info(f"Successful: {summary['successful_universities']}")
        logger.info(f"Programs extracted: {summary['total_programs_extracted']}")
        logger.info(f"Programs saved to DB: {summary['programs_saved_to_db']}")
        logger.info(f"Average confidence: {summary['average_confidence']:.2f}")
        logger.info(f"Processing time: {summary['processing_time_seconds']:.2f} seconds")

        # Collect all programs for export
        all_programs = []
        for result in summary['results']:
            if result['programs']:
                all_programs.extend(result['programs'])

        if all_programs:
            logger.info(f"\nTotal programs collected: {len(all_programs)}")
            logger.info("Starting data export to multiple formats...\n")

            # Export to all formats
            export_results = exporter.export_all_formats(all_programs)

            # Display export results
            logger.info("\n" + "=" * 80)
            logger.info("DATA EXPORT RESULTS")
            logger.info("=" * 80)
            
            for format_name, success in export_results.items():
                status = "✓ SUCCESS" if success else "✗ FAILED"
                logger.info(f"{format_name.upper():20} {status}")

            # List exported files
            files = exporter.get_exported_files()
            if files:
                logger.info(f"\nExported files in 'exported_data/' directory:")
                for file in files[:15]:
                    file_path = os.path.join(exporter.export_dir, file)
                    file_size = os.path.getsize(file_path)
                    logger.info(f"  • {file} ({file_size:,} bytes)")
        else:
            logger.warning("No programs were extracted during scraping")

        # Detailed results
        logger.info("\n" + "=" * 80)
        logger.info("DETAILED RESULTS BY UNIVERSITY")
        logger.info("=" * 80)
        for result in summary['results']:
            status = "✓ SUCCESS" if result['success'] else "✗ FAILED"
            logger.info(f"{result['university']:40} {result['total_programs']:3} programs | Confidence: {result['confidence_score']:.2f} | {status}")

        logger.info("\n" + "=" * 80)
        logger.info("SCRAPING AND EXPORT COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.warning("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
    finally:
        # Cleanup
        exporter.close()
        logger.info("Data exporter closed")


def main():
    """Main entry point"""
    # Set Windows event loop policy for compatibility
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Run async main
    asyncio.run(scrape_and_export())


if __name__ == "__main__":
    main()

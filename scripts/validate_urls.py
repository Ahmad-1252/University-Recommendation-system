#!/usr/bin/env python3
"""URL validation script for university program pages."""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.constants import UNIVERSITY_URLS
from src.services.validation_service import ValidationService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("logs/url_validation.log")],
)

logger = logging.getLogger(__name__)


async def main():
    """Main URL validation function."""
    logger.info("Starting URL validation")

    validator = ValidationService()

    # Get URLs to validate
    urls = list(UNIVERSITY_URLS.values())
    logger.info(f"Validating {len(urls)} URLs")

    try:
        # Validate all URLs
        results = await validator.validate_urls_batch(urls)

        # Categorize results
        valid_urls = []
        invalid_urls = []

        for url, (is_valid, reason) in results.items():
            if is_valid:
                valid_urls.append((url, reason))
            else:
                invalid_urls.append((url, reason))

        # Print results
        print("\n" + "=" * 60)
        print("URL VALIDATION REPORT")
        print("=" * 60)
        print(f"Total URLs: {len(urls)}")
        print(f"Valid URLs: {len(valid_urls)}")
        print(f"Invalid URLs: {len(invalid_urls)}")
        print()

        if valid_urls:
            print("✅ VALID URLS:")
            for url, reason in valid_urls:
                university = next(
                    (k for k, v in UNIVERSITY_URLS.items() if v == url), "Unknown"
                )
                print(f"• {university}: {url}")
            print()

        if invalid_urls:
            print("❌ INVALID URLS:")
            for url, reason in invalid_urls:
                university = next(
                    (k for k, v in UNIVERSITY_URLS.items() if v == url), "Unknown"
                )
                print(f"• {university}: {reason}")
                print(f"  URL: {url}")
            print()

        # Save results to file
        results_file = Path("data/exports/url_validation_results.json")
        results_file.parent.mkdir(parents=True, exist_ok=True)

        validation_results = {
            "summary": {
                "total_urls": len(urls),
                "valid_urls": len(valid_urls),
                "invalid_urls": len(invalid_urls),
                "validation_timestamp": str(asyncio.get_event_loop().time()),
            },
            "valid_urls": [
                {
                    "university": next(
                        (k for k, v in UNIVERSITY_URLS.items() if v == url), "Unknown"
                    ),
                    "url": url,
                    "reason": reason,
                }
                for url, reason in valid_urls
            ],
            "invalid_urls": [
                {
                    "university": next(
                        (k for k, v in UNIVERSITY_URLS.items() if v == url), "Unknown"
                    ),
                    "url": url,
                    "reason": reason,
                }
                for url, reason in invalid_urls
            ],
        }

        import json

        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(validation_results, f, indent=2, ensure_ascii=False)

        print(f"Results saved to: {results_file}")

        # Exit with error code if any URLs are invalid
        if invalid_urls:
            logger.warning(f"{len(invalid_urls)} URLs failed validation")
            sys.exit(1)

    except Exception as e:
        logger.error(f"URL validation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

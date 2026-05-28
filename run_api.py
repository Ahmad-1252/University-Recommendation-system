# ! env\Scripts\activate
"""Script to run the FastAPI server."""

import logging

# Add src to path
import sys
from pathlib import Path

import uvicorn

src_path = str(Path(__file__).parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("Starting University Recommendation System API")
    uvicorn.run(
        "api.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )

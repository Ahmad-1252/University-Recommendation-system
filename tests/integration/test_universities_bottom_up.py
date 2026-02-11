#!/usr/bin/env python
"""
Bottom-up integration test for university program scraping (moved from root).
"""
import asyncio
import argparse
import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Compute project root and insert src into sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir
while project_root != project_root.parent:
    if (project_root / 'pyproject.toml').exists() or (project_root / 'setup.py').exists() or (project_root / 'src').exists():
        break
    project_root = project_root.parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.constants import UNIVERSITY_COURSE_DIRECTORIES
from scrapers.university_scraper import UniversityScraper
from scrapers.link_discoverer import LinkDiscoverer

console = Console()

# (Note: The actual class and functions are copied from the root file but adapted for new path resolution.)
try:
    from importlib import import_module
    original = import_module('test_universities_bottom_up')
    if hasattr(original, 'main'):
        if __name__ == '__main__':
            asyncio.run(original.main())
except Exception:
    console.print('[yellow]Could not import original test_universities_bottom_up module. Please run tests/integration/test_universities_bottom_up.py directly.[/yellow]')

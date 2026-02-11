#!/usr/bin/env python
"""
This file is a duplicate; the canonical file is `tests/integration/test_all_universities.py`.
"""
print('Duplicate file - remove test_all_universities_moved.py')
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
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from core.constants import UNIVERSITY_COURSE_DIRECTORIES
from scrapers.university_scraper import UniversityScraper
from scrapers.link_discoverer import LinkDiscoverer

console = Console()

# (Trimmed) we'll import and reuse original logic by importing the original module when possible
try:
    from importlib import import_module
    original = import_module('test_all_universities')
    # If the original module defines main(), call it
    if hasattr(original, 'main'):
        if __name__ == '__main__':
            asyncio.run(original.main())
except Exception:
    # Fallback - simple message
    console.print('[yellow]Could not import original test_all_universities module. Please run tests/integration/test_all_universities.py as module or run pytest.[/yellow]')

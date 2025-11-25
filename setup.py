"""Setup script for the University Recommendation System."""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read requirements
def read_requirements(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="university-recommendation-system",
    version="1.0.0",
    author="University Recommendation System Team",
    author_email="team@university-recommendation.dev",
    description="AI-powered system for scraping and analyzing computer science programs from global universities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ahmad-1252/university-recommendation-system",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Education",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    keywords="university recommendation computer-science scraping ai llm",
    python_requires=">=3.8",
    install_requires=read_requirements('requirements.txt'),
    extras_require={
        'dev': [
            'pytest>=7.4.3',
            'pytest-asyncio>=0.21.1',
            'pytest-cov>=4.1.0',
            'black>=23.12.1',
            'ruff>=0.1.11',
            'mypy>=1.7.1',
            'pre-commit>=3.5.0',
        ],
        'docs': [
            'sphinx>=7.2.6',
            'sphinx-rtd-theme>=1.3.0',
        ],
        'all': [
            'university-recommendation-system[dev,docs]',
        ],
    },
    entry_points={
        'console_scripts': [
            'urs=src.cli.commands:cli',
            'scrape-universities=scripts.run_scraper:main',
            'validate-urls=scripts.validate_urls:main',
            'monitor-quality=scripts.monitor_quality:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
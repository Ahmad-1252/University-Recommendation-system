# 🏛️ University Recommendation System

A comprehensive AI-powered system for scraping and analyzing computer science programs from global universities. Built with modern Python architecture, featuring LLM-powered data extraction, MongoDB storage, and interactive CLI tools.

## 🚀 Features

### Core Capabilities
- **AI-Powered Scraping**: Groq LLM (Llama 3.1) for intelligent data extraction from unstructured web content
- **Concurrent Processing**: AsyncIO and aiohttp for high-performance web scraping
- **Data Validation**: Pydantic models with comprehensive field validation
- **Quality Monitoring**: Automated data quality assessment and gap analysis
- **Interactive CLI**: Rich terminal interface for data exploration and analysis
- **Multi-Format Export**: CSV, JSON, and Excel export capabilities

### Advanced Features
- **25+ Universities**: Comprehensive coverage of top global computer science programs
- **Confidence Scoring**: 0-100% confidence scores for all extracted data
- **Repository Pattern**: Clean database abstraction with MongoDB
- **Error Recovery**: Robust retry logic with exponential backoff
- **Type Safety**: Full type hints and mypy validation
- **Testing Framework**: Comprehensive pytest suite with async support

## 📋 System Requirements

- **Python**: 3.8+
- **Database**: MongoDB (local or Atlas)
- **API**: Groq API key
- **Memory**: 4GB+ RAM recommended
- **Storage**: 2GB+ free space

## 🛠️ Installation

### 1. Clone Repository
```bash
git clone https://github.com/ahmad-1252/university-recommendation-system.git
cd university-recommendation-system
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your actual values
```

Required environment variables:
```env
MONGO_CONNECTION_STRING=mongodb://localhost:27017
GROQ_API_KEY=your_groq_api_key_here
```

### 4. Install for Development (Optional)
```bash
pip install -e .[dev]
```

## 🎯 Quick Start

### 1. Validate URLs
```bash
python scripts/validate_urls.py
```

### 2. Run Full Scraper
```bash
python scripts/run_scraper.py
```

### 3. Monitor Quality
```bash
python scripts/monitor_quality.py
```

### 4. Interactive Dashboard
```bash
python -m src.cli.commands dashboard
```

## 📊 Data Structure

### University Program Model
```python
{
    "university_name": "Stanford University",
    "program_name": "MS in Computer Science",
    "degree_type": "Master of Science",
    "country": "United States",
    "city": "Stanford, CA",

    # Academic Requirements
    "gpa_requirement_min": 3.5,
    "language_requirements": {
        "toefl_min": 100,
        "ielts_min": 7.0
    },

    # Financial Information
    "tuition_fees": {
        "domestic_per_year": 65000,
        "international_per_year": 65000,
        "currency": "USD"
    },

    # Program Details
    "duration_years": 2.0,
    "program_description": "Comprehensive CS program...",
    "specializations": ["AI", "Systems", "Theory"],
    "research_interests": ["Machine Learning", "Computer Vision"],

    # Rankings & Reputation
    "rankings": {
        "qs_world_ranking": 3,
        "the_world_ranking": 4,
        "us_news_ranking": 3
    },

    # Metadata
    "source_url": "https://cs.stanford.edu/",
    "confidence_score": 0.92,
    "data_completeness": 0.85,
    "last_updated": "2025-11-13T10:30:00Z"
}
```

## 🏗️ Project Architecture

```
university-recommendation-system/
├── src/
│   ├── core/                 # Configuration & shared utilities
│   │   ├── config.py        # Pydantic settings
│   │   ├── constants.py     # URLs, metadata, enums
│   │   └── exceptions.py    # Custom exceptions
│   ├── models/              # Data models
│   │   └── university.py    # Pydantic models
│   ├── database/            # Data persistence
│   │   ├── mongodb.py       # Connection management
│   │   └── repositories.py  # Repository pattern
│   ├── scrapers/            # Web scraping logic
│   │   ├── base_scraper.py  # Abstract scraper
│   │   ├── university_scraper.py  # Main scraper
│   │   ├── content_extractor.py   # LLM extraction
│   │   └── link_discoverer.py     # Link discovery
│   ├── services/            # Business logic
│   │   ├── llm_service.py   # Groq API client
│   │   ├── validation_service.py  # Data validation
│   │   └── enrichment_service.py  # Data enrichment
│   ├── analyzers/           # Data analysis
│   │   └── quality_analyzer.py    # Quality metrics
│   └── cli/                 # Command-line interface
│       ├── dashboard.py     # Interactive dashboard
│       ├── data_viewer.py   # Data browser
│       └── commands.py      # CLI commands
├── scripts/                 # Executable scripts
│   ├── run_scraper.py       # Main scraping script
│   ├── monitor_quality.py   # Quality monitoring
│   └── validate_urls.py     # URL validation
├── tests/                   # Test suite
├── data/                    # Data files
│   └── exports/            # Exported data
├── logs/                   # Application logs
├── docs/                   # Documentation
├── .env.example           # Environment template
├── pyproject.toml         # Project configuration
├── setup.py              # Package setup
└── requirements.txt      # Dependencies
```

## 🎮 CLI Usage

### Interactive Dashboard
```bash
urs dashboard
```
Features:
- Real-time system status
- Data overview and statistics
- Recent activity monitoring
- Quick action menu

### Data Viewer
```bash
urs view
```
Capabilities:
- Search programs by keywords
- Browse by university
- View detailed program information
- Export filtered results

### Search Programs
```bash
# Search by query
urs search "machine learning"

# Filter by country
urs search --country "Germany" "computer science"

# Filter by degree type
urs search --degree "Master of Science" "AI"
```

### Scrape Data
```bash
# Scrape specific URLs
urs scrape https://cs.stanford.edu/ https://cs.berkeley.edu/

# Scrape from file
urs scrape --file urls.txt

# Control concurrency
urs scrape --concurrent 3 urls.txt
```

### Validate URLs
```bash
urs validate https://cs.stanford.edu/
urs validate --file university_urls.txt
```

### Export Data
```bash
# Export all data
urs export

# Export specific formats
urs export --format csv --format json

# Custom output directory
urs export --output ./my_exports
```

### Quality Analysis
```bash
urs analyze
```
Provides:
- Data completeness metrics
- Quality score analysis
- Coverage statistics
- Improvement recommendations

## 🔧 Configuration

### Environment Variables
```env
# Database
MONGO_CONNECTION_STRING=mongodb://localhost:27017
DATABASE_NAME=university_db
COLLECTION_NAME=programs

# LLM Service
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama3-70b-8192
LLM_TIMEOUT=30

# Scraping
SCRAPE_TIMEOUT=30
MAX_CONCURRENT_REQUESTS=5
RATE_LIMIT_DELAY=2.0

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/app.log

# Export
EXPORT_DIR=data/exports
```

### Advanced Configuration
The system uses Pydantic settings for configuration management. All settings can be overridden via environment variables or configuration files.

## 🧪 Testing

### Run Test Suite
```bash
pytest
```

### Run with Coverage
```bash
pytest --cov=src --cov-report=html
```

### Run Specific Tests
```bash
pytest tests/test_scrapers/
pytest tests/test_services/test_llm_service.py
```

## 📊 Performance & Quality

### Expected Metrics
- **Success Rate**: 85-95% URL processing
- **Data Completeness**: 80%+ field coverage
- **Confidence Scores**: 75%+ average
- **Processing Speed**: 50-100 URLs/hour

### Quality Monitoring
```bash
# Generate quality report
urs analyze

# Monitor data freshness
python scripts/monitor_quality.py
```

## 🐛 Troubleshooting

### Common Issues

#### MongoDB Connection Failed
```bash
# Check MongoDB status
brew services list | grep mongodb

# Or for local installation
sudo systemctl status mongod
```

#### Groq API Errors
```bash
# Check API key
echo $GROQ_API_KEY

# Test API connection
python -c "from groq import Groq; Groq().models.list()"
```

#### Low Success Rates
- Verify URLs are accessible
- Check for anti-bot measures
- Reduce concurrent requests
- Increase timeouts

#### Memory Issues
- Reduce `MAX_CONCURRENT_REQUESTS`
- Process URLs in smaller batches
- Monitor system resources

### Debug Mode
```bash
export LOG_LEVEL=DEBUG
urs scrape --verbose
```

## 🚀 Deployment

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "scripts/run_scraper.py"]
```

### Production Setup
```bash
# Install production dependencies only
pip install --no-dev -r requirements.txt

# Set production environment
export DEBUG=false
export LOG_LEVEL=WARNING

# Use production MongoDB
export MONGO_CONNECTION_STRING=mongodb+srv://...
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure code passes linting: `ruff check` and `mypy`
5. Submit a pull request

### Development Setup
```bash
# Install development dependencies
pip install -e .[dev]

# Run pre-commit hooks
pre-commit install

# Format code
black src/
ruff check --fix src/
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Groq** for providing fast LLM inference
- **MongoDB** for reliable document storage
- **Crawl4AI** for web scraping capabilities
- **Pydantic** for data validation
- **Rich** for beautiful CLI interfaces

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/ahmad-1252/university-recommendation-system/issues)
- **Documentation**: [Read the Docs](https://university-recommendation-system.readthedocs.io/)
- **Discussions**: [GitHub Discussions](https://github.com/ahmad-1252/university-recommendation-system/discussions)

---

**Built with ❤️ for students and researchers worldwide**
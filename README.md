# 🏗️ Enhanced University Scraper System

A comprehensive AI-powered web scraping system for collecting university computer science program data with advanced retry logic, confidence scoring, and interactive data analysis.

## 🚀 Features

### Core Capabilities
- **Multi-Strategy Scraping**: 5-level fallback system for maximum data extraction
- **AI-Powered Extraction**: Groq LLM with multi-step processing for accurate data parsing
- **Confidence Scoring**: Quality assessment for all extracted data (0-100%)
- **Interactive Analysis**: CLI tools for searching, filtering, and comparing universities
- **Data Quality Monitoring**: Automated gap analysis and recovery systems

### Advanced Features
- **URL Validation**: Pre-scraping validation with alternative URL suggestions
- **Retry Logic**: Exponential backoff with multiple extraction strategies
- **Data Enrichment**: Automatic filling of missing critical fields
- **Duplicate Handling**: Smart deduplication based on confidence scores
- **Export Tools**: JSON export for external analysis

## 📋 System Requirements

- Python 3.8+
- MongoDB (local or Atlas)
- Groq API key
- Internet connection

## 🛠️ Installation

### 1. Clone and Setup
```bash
git clone <repository-url>
cd university-recommendation-system
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Update `.env` file with your credentials:
```env
GROQ_API_KEY="your_groq_api_key_here"
MONGODB_URI="your_mongodb_connection_string"
GROQ_MODEL="llama-3.1-70b-versatile"
DATABASE_NAME="University-Recommendator"
COLLECTION_NAME="University_Data"
```

### 4. Install Playwright Browsers
```bash
playwright install
```

## 🎯 Usage Guide

### Step 1: Validate URLs (Recommended)
Before scraping, validate all university URLs:
```bash
python url_validator.py
```
This will:
- Test URL accessibility
- Identify broken links
- Suggest alternative URLs
- Generate validation report

### Step 2: Run Enhanced Scraper
Execute the main scraping process:
```bash
python uni_scraper_enhanced.py
```
Features:
- Processes 25 universities concurrently
- 5-level retry logic per university
- Multi-step LLM extraction
- Confidence scoring
- Progress tracking

### Step 3: Monitor Data Quality
Analyze scraped data and identify gaps:
```bash
python scraper_monitor.py
```
Provides:
- Data completeness analysis
- Confidence score distribution
- Missing field identification
- Duplicate cleanup

### Step 4: Interactive Data Exploration
Explore and analyze the collected data:
```bash
python data_viewer.py
```

## 📊 Data Structure

### University Program Schema
```python
{
    "university_name": "University of Oxford",
    "program_name": "MSc Computer Science",
    "country": "UK",
    "tier": "top",

    # Requirements
    "min_gpa": "3.5/4.0",
    "english_requirement": "TOEFL 100+",
    "tuition_fee": "£30,000/year",
    "scholarship_info": "Available for international students",

    # Program Details
    "program_description": "Advanced computer science program...",
    "duration": "2 years",
    "specializations": ["AI", "Data Science", "Cybersecurity"],
    "program_format": "Full-time",

    # Career Info
    "career_outcomes": "85% employment within 6 months",
    "top_recruiters": ["Google", "Microsoft", "Amazon"],
    "average_salary": "£75,000",

    # Metadata
    "source_url": "https://...",
    "extraction_confidence": 0.85,
    "scraped_at": "2025-11-09T12:00:00Z"
}
```

## 🔧 Configuration Options

### Environment Variables
- `GROQ_MODEL`: LLM model (default: llama-3.1-70b-versatile)
- `SCRAPE_TIMEOUT`: Page load timeout in seconds (default: 40)
- `RATE_LIMIT_DELAY`: Delay between requests (default: 0.5)
- `VALIDATION_TIMEOUT`: URL validation timeout (default: 15)

### Scraping Strategies
1. **Standard Crawl**: Basic page scraping
2. **JavaScript Render**: Wait for dynamic content
3. **Aggressive Extraction**: Combined content processing
4. **Alternative URLs**: Try related university pages
5. **Multi-LLM**: Enhanced extraction with multiple prompts

## 📈 Performance Metrics

### Expected Results
- **Success Rate**: 80-95% (with retry logic)
- **Average Confidence**: 75-85%
- **Processing Time**: 2-4 minutes for 25 universities
- **Data Fields**: 15-20 per university record

### Confidence Scoring
- **90-100%**: High-quality, complete data
- **70-90%**: Good data with minor gaps
- **50-70%**: Acceptable data, some missing fields
- **<50%**: Low-quality, needs re-scraping

## 🐛 Troubleshooting

### Common Issues

#### 1. "Connection timeout" errors
**Solution**: Increase timeout in `.env`:
```env
SCRAPE_TIMEOUT=60
```

#### 2. "LLM extraction failed" messages
**Solution**: Switch to simpler model:
```env
GROQ_MODEL=llama-3.1-70b-versatile
```

#### 3. Low confidence scores
**Solution**:
- Check URL validity
- Ensure pages have program information
- Try alternative URLs

#### 4. MongoDB connection errors
**Solution**: Verify connection string format:
```env
MONGODB_URI="mongodb+srv://username:password@cluster.mongodb.net/"
```

### Debug Mode
Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📊 Analysis & Reporting

### Data Quality Reports
```bash
python scraper_monitor.py
```
Generates:
- Field completeness analysis
- Confidence distribution charts
- Missing data identification
- Duplicate detection

### Export Data
```bash
python data_viewer.py
# Select option 11: Export data to JSON
```

### Interactive Queries
```bash
python data_viewer.py
```
Available operations:
- Search by country/tier
- Compare universities
- Find scholarships
- GPA requirement analysis
- Export filtered results

## 🔄 Data Recovery

### Automatic Recovery
The monitor can attempt to fill missing data:
```bash
python scraper_monitor.py
# Enable fill_missing_data() call
```

### Manual Re-scraping
For specific universities with low confidence:
```bash
python uni_scraper_enhanced.py
# Modify university list to target specific schools
```

## 📁 Project Structure

```
university-recommendation-system/
├── uni_scraper_enhanced.py    # Main scraper with retry logic
├── url_validator.py           # URL validation tool
├── scraper_monitor.py         # Data quality monitoring
├── data_viewer.py             # Interactive data explorer
├── database.py                # MongoDB operations (legacy)
├── schema.py                  # Pydantic models (legacy)
├── main.py                    # Simple runner (legacy)
├── requirements.txt           # Dependencies
├── .env                       # Configuration
├── README.md                  # This file
├── scraper.log                # Execution logs
└── *.json                     # Export files
```

## 🚀 Advanced Usage

### Custom University List
Modify `UNIVERSITIES` list in `uni_scraper_enhanced.py`:
```python
UNIVERSITIES = [
    ("Your University", "Country", UniversityTier.TOP, "https://..."),
    # Add more universities
]
```

### Custom Extraction Prompts
Modify LLM prompts in `AdvancedUniversityScraper` class for domain-specific extraction.

### Batch Processing
For large university lists, implement chunked processing:
```python
# Process in batches of 10
for i in range(0, len(universities), 10):
    batch = universities[i:i+10]
    # Process batch
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review scraper.log for errors
3. Validate URLs before scraping
4. Ensure MongoDB connection is active

## 🎯 Next Steps

1. **URL Validation**: Always run `url_validator.py` first
2. **Enhanced Scraping**: Use `uni_scraper_enhanced.py` for production
3. **Quality Monitoring**: Regular runs of `scraper_monitor.py`
4. **Data Analysis**: Use `data_viewer.py` for insights

---

**System designed for reliability, quality, and scalability in university data extraction.**
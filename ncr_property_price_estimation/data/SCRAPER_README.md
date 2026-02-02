# MagicBricks Scraper - Quick Start Guide

## 🚀 Overview

The **MagicBricks NCR Property Scraper** is an enterprise-grade web scraper that collects real estate data from MagicBricks.com for the National Capital Region (NCR) of India.

**Key Features:**
- ✅ **Checkpoint/Resume**: Automatically resumes from interruptions
- ✅ **Rotating Logs**: Professional logging with automatic rotation (10MB max, 5 backups)
- ✅ **Data Validation**: Deduplication and quality checks
- ✅ **Statistics Tracking**: Monitor progress and performance
- ✅ **Graceful Shutdown**: Ctrl+C safe - always saves data before exit
- ✅ **Anti-Blocking**: User-agent rotation, randomized delays, rate limiting

## 📁 File Structure

```
ncr_property_price_estimation/data/
├── ingestion.py              # ⭐ MAIN SCRAPER (MagicBricks - Enterprise Edition)
├── 99acres_scraper.py        # 99acres scraper (Selenium-based, backup)
├── magicbricks_scraper.py    # Old MagicBricks scraper (deprecated)
└── config.yaml               # Configuration file (for 99acres)
```

## 🎯 Quick Start

### 1. Run the Scraper

```bash
# Navigate to project root
cd "d:\DATA SCIENCE\ncr_property_price_estimation"

# Run the scraper
python -m ncr_property_price_estimation.data.ingestion
```

### 2. Monitor Progress

The scraper will:
- Load existing data to avoid duplicates
- Resume from last checkpoint if interrupted
- Display progress for each city and page
- Save data every 10 pages
- Take coffee breaks every 20 pages (2 minutes)

### 3. Interrupt and Resume

Press **Ctrl+C** to stop the scraper gracefully. It will:
- Save all pending data to CSV
- Save current progress to checkpoint
- Display statistics summary

To resume, simply run the scraper again:
```bash
python -m ncr_property_price_estimation.data.ingestion
```

It will automatically resume from where it left off!

## 📊 Output Files

All files are saved to: `data/raw/`

### Data Files
- **`magicbricks_NCR_ML.csv`** - Main output CSV with all scraped listings
- **`magicbricks_checkpoint.json`** - Progress checkpoint for resume capability

### Log Files (in `data/raw/logs/`)
- **`magicbricks.log`** - Main log file (all levels)
- **`magicbricks_errors.log`** - Error log only
- Logs automatically rotate when exceeding 10MB (keeps 5 backups)

## 🔧 Configuration

The scraper is configured with sensible defaults:

```python
# Batch size: Save every 10 pages
# Coffee breaks: Every 20 pages (2 minutes)
# Max pages per city: 200
# Request timeout: 30 seconds
# Retry attempts: 3
```

To modify, edit the constants in `ingestion.py`.

## 🏙️ Cities Covered

The scraper collects data for 11 NCR cities:
1. Noida
2. Gurgaon
3. Greater Noida
4. Ghaziabad
5. Faridabad
6. New Delhi
7. Delhi
8. Bhiwadi
9. Meerut
10. Panipat
11. Sonipat

## 📋 Data Fields Extracted

Each listing includes:

**Basic Info:**
- Title, URL, City, Location
- Price (raw text + numeric value)
- Area (raw text + numeric sq.ft)

**Property Details:**
- Property Type (Apartment, Villa, Builder Floor, Plot)
- Bedrooms, Bathrooms, Balconies
- Floor number
- Facing direction

**Amenities:**
- Pooja Room, Servant Room, Store Room
- Swimming Pool, Gym, Lift
- Parking, Vastu Compliant

**Other:**
- Furnishing status (Fully/Semi/Unfurnished)
- Source (MagicBricks)
- Scraped Date

## 🛡️ Anti-Blocking Measures

The scraper includes several anti-blocking features:
- **User-Agent Rotation**: Randomly rotates between 4 different user agents
- **Random Delays**: 2-5 seconds between requests
- **Exponential Backoff**: On errors, waits longer before retrying
- **Coffee Breaks**: 2-minute breaks every 20 pages
- **CAPTCHA Detection**: Automatically waits if CAPTCHA detected

## 📈 Statistics

After completion (or interruption), the scraper displays:
- Total listings scraped
- Total pages processed
- Number of errors
- Elapsed time
- Scraping rate (listings/hour)
- Breakdown by city

## 🐛 Troubleshooting

### Scraper not resuming?
- Check if `magicbricks_checkpoint.json` exists in `data/raw/`
- Verify the checkpoint file is valid JSON

### No data being saved?
- Check logs in `data/raw/logs/magicbricks.log`
- Ensure you have write permissions to `data/raw/`

### CAPTCHA detected?
- The scraper will automatically wait 2 minutes
- If persistent, try increasing delays in the code

### Too many errors?
- Check `magicbricks_errors.log` for details
- Verify internet connection
- MagicBricks may have changed their HTML structure

## 🔄 Comparison: Old vs New Scraper

| Feature | Old (`magicbricks_scraper.py`) | New (`ingestion.py`) |
|---------|-------------------------------|---------------------|
| Logging | Basic file logging | Rotating file handlers |
| Checkpoint | Basic JSON checkpoint | Enterprise checkpoint system |
| Data Buffer | Immediate CSV writes | Batched writes (10x faster) |
| Statistics | Basic counters | Comprehensive stats tracking |
| Error Handling | Simple try/catch | Exponential backoff + retry |
| Shutdown | Manual save | Graceful shutdown (Ctrl+C safe) |
| User Agent | Single static UA | Rotating UA pool |
| Code Quality | Functional | Production-ready |

## 📝 Notes

- The old `magicbricks_scraper.py` is deprecated but kept for reference
- The `99acres_scraper.py` is a backup of the original Selenium-based scraper
- Both scrapers save to different CSV files and can run independently

## 🚦 Next Steps

After scraping:
1. Check data quality: `python preview_data.py`
2. Process data: Move to `data/processed/`
3. Feature engineering: Use `ncr_property_price_estimation/features.py`
4. Model training: Use `ncr_property_price_estimation/modeling/train.py`

---

**Happy Scraping! 🏠📊**

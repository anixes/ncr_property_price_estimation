# Quick Test Script for MagicBricks Scraper

This script tests the enhanced scraper by running it for just 1 page to verify functionality.

```python
# test_scraper.py
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ingestion import MagicBricksScraper, setup_logging

def test_scraper():
    """Test the scraper with a single page."""
    setup_logging()
    
    print("="*60)
    print("🧪 Testing MagicBricks Scraper")
    print("="*60)
    
    scraper = MagicBricksScraper()
    
    # Test with just Noida, 1 page
    test_url = 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=Noida&page={}'
    
    print("\n📍 Testing with Noida (1 page only)...")
    scraper.scrape_city("Noida", test_url, start_page=1, max_pages=1)
    
    print("\n✅ Test complete!")
    print(f"📊 Scraped {len(scraper.seen_urls)} total listings")
    print(scraper.stats.get_summary())

if __name__ == "__main__":
    test_scraper()
```

## Run the test:

```bash
cd "d:\DATA SCIENCE\ncr_property_price_estimation\ncr_property_price_estimation\data"
python test_scraper.py
```

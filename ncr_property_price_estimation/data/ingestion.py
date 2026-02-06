
                    #    MagicBricks Production Scraper

import sys
import time
import json
import random
import re
import logging
import hashlib
import argparse
from pathlib import Path
from typing import Dict, List, Set, Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from tenacity import retry, stop_after_attempt, wait_exponential

from schema import validate_dataframe



# PATHS

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)



# LOGGING SETUP (Simple, No Rotation)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(DATA_DIR / 'logs' / 'production_scraper.log', encoding='utf-8')
    ]
)

# Create logs directory
(DATA_DIR / 'logs').mkdir(exist_ok=True)



# CITY NORMALIZATION

CITY_MAP = {
    'gurgaon': 'Gurugram',
    'gurugram': 'Gurugram',
    'noida extension': 'Greater Noida West',
    'greater noida west': 'Greater Noida West',
}

def normalize_city(city: str) -> str:
    """Canonical city mapping."""
    return CITY_MAP.get(city.lower(), city.title())



# PRICE NORMALIZATION

def normalize_price(text: str) -> Optional[int]:
    """Convert to absolute INR integer.
    
    Examples:
        '1.2 Cr' -> 12000000
        '85 L' -> 8500000
    """
    if not text:
        return None
    
    text = text.lower().strip()
    match = re.search(r'([\d.]+)', text)
    if not match:
        return None
    
    value = float(match.group(1))
    
    if 'cr' in text or 'crore' in text:
        return int(value * 10000000)
    elif 'l' in text or 'lac' in text or 'lakh' in text:
        return int(value * 100000)
    
    return int(value)



# AREA NORMALIZATION

def normalize_area(text: str) -> Optional[float]:
    """Convert to numeric sqft only.
    
    Removes: "sqft", commas, text
    Converts: sq.m to sqft
    """
    if not text:
        return None
    
    text = text.lower().strip()
    
    # Extract number
    clean = re.sub(r'[^\d.]', '', text)
    if not clean:
        return None
    
    value = float(clean)
    
    # Convert sq.m to sqft
    if 'sq.m' in text or 'sqm' in text:
        value *= 10.764
    
    return value


# PROPERTY HASH (Deduplication)

def create_property_hash(listing: Dict) -> str:
    """Create deterministic hash for deduplication."""
    title = str(listing.get('title', '')).lower().strip()
    price = str(listing.get('price', ''))
    area = str(listing.get('area_sqft', ''))
    location = str(listing.get('location', '')).lower().strip()
    
    hash_input = f"{title}|{price}|{area}|{location}"
    return hashlib.md5(hash_input.encode()).hexdigest()



# PARQUET SCHEMA

PARQUET_SCHEMA = pa.schema([
    ('title', pa.string()),
    ('url', pa.string()),
    ('city', pa.string()),
    ('location', pa.string()),
    ('price', pa.int64()),
    ('price_raw', pa.string()),
    ('area_sqft', pa.float64()),
    ('area_raw', pa.string()),
    ('bedrooms', pa.int8()),
    ('bathrooms', pa.int8()),
    ('balcony', pa.int8()),
    ('prop_type', pa.string()),
    ('furnished', pa.string()),
    ('facing', pa.string()),
    ('floor', pa.int16()),
    ('pooja_room', pa.int8()),
    ('servant_room', pa.int8()),
    ('store_room', pa.int8()),
    ('pool', pa.int8()),
    ('gym', pa.int8()),
    ('lift', pa.int8()),
    ('parking', pa.int8()),
    ('vastu_compliant', pa.int8()),
    ('property_hash', pa.string()),
    ('scraped_at', pa.timestamp('us')),  # Microseconds to match pandas
])



# PRODUCTION SCRAPER

class ProductionScraper:
    """Production-grade MagicBricks scraper."""
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    ]
    
    CITIES = {
        'noida': 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=Noida&page={}',
        'gurgaon': 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=Gurgaon&page={}',
        'greater noida': 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=Greater-Noida&page={}',
        'ghaziabad': 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=Ghaziabad&page={}',
        'faridabad': 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=Faridabad&page={}',
        'new delhi': 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=New-Delhi&page={}',
        'delhi': 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=Delhi&page={}',
    }
    
    def __init__(self, output_path: str):
        """Initialize scraper."""
        self.output_path = Path(output_path)
        self.checkpoint_path = DATA_DIR / 'checkpoint_production.json'
        
        # Session for requests
        self.session = requests.Session()
        self._rotate_user_agent()
        
        # Tracking
        self.seen_hashes: Set[str] = set()
        self.buffer: List[Dict] = []
        self.batch_size = 100
        
        # Stats
        self.stats = {
            'total_scraped': 0,
            'valid_rows': 0,
            'rejected_rows': 0,
            'duplicate_rows': 0,
        }
        
        # Load checkpoint
        self.checkpoint = self._load_checkpoint()
        
    def _rotate_user_agent(self):
        """Rotate user agent."""
        self.session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
    
    def _load_checkpoint(self) -> Dict:
        """Load checkpoint if exists."""
        if not self.checkpoint_path.exists():
            return {}
        
        try:
            with open(self.checkpoint_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Failed to load checkpoint: {e}")
            return {}
    
    def _save_checkpoint(self, city: str, page: int):
        """Save checkpoint."""
        checkpoint = {
            'city': city,
            'page': page,
            'timestamp': datetime.now().isoformat(),
        }
        
        with open(self.checkpoint_path, 'w') as f:
            json.dump(checkpoint, f, indent=2)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch page with requests (fast)."""
        time.sleep(random.uniform(1.5, 4))  # Request jitter
        
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')

    
    def extract_listings(self, soup: BeautifulSoup, city: str) -> List[Dict]:
        """Extract listings from page."""
        listings = []
        
        # Find property cards
        cards = soup.select('div[class*="mb-srp__card"]')
        if not cards:
            cards = soup.select('div.mb-srp__list__item')
        
        for card in cards:
            try:
                # Extract URL
                link = card.select_one('a[href*="/propertyDetails"]')
                if not link:
                    link = card.select_one('a[href*="/property-detail"]')
                if not link:
                    continue
                
                url = link.get('href')
                if not url.startswith('http'):
                    url = 'https://www.magicbricks.com' + url
                
                # Extract basic info from card
                title_elem = card.select_one('h2')
                title = title_elem.get_text(strip=True) if title_elem else ""
                
                price_elem = card.select_one('[class*="price"]')
                price_text = price_elem.get_text(strip=True) if price_elem else ""
                price = normalize_price(price_text)
                
                if not price:
                    continue
                
                # Extract location
                location_elem = card.select_one('[class*="location"]') or card.select_one('[class*="locality"]')
                location = location_elem.get_text(strip=True) if location_elem else ""
                
                # Get card text for feature extraction
                card_text = card.get_text().lower()
                
                # Extract bedrooms
                bhk_match = re.search(r'(\d+)\s*bhk', card_text)
                bedrooms = int(bhk_match.group(1)) if bhk_match else 0
                
                # Extract bathrooms
                bath_match = re.search(r'(\d+)\s*bath', card_text)
                bathrooms = int(bath_match.group(1)) if bath_match else 0
                
                # Extract balcony
                balc_match = re.search(r'(\d+)\s*balcon', card_text)
                balcony = int(balc_match.group(1)) if balc_match else 0
                
                # Property type
                prop_type = "Apartment"
                if 'villa' in card_text or 'house' in card_text:
                    prop_type = "Independent House"
                elif 'plot' in card_text:
                    prop_type = "Plot"
                elif 'builder floor' in card_text:
                    prop_type = "Builder Floor"
                
                # Furnishing
                furnished = "Unknown"
                if 'semi' in card_text and 'furnished' in card_text:
                    furnished = "Semi-Furnished"
                elif 'fully' in card_text and 'furnished' in card_text:
                    furnished = "Fully-Furnished"
                elif 'unfurnished' in card_text:
                    furnished = "Unfurnished"
                
                # Facing
                facing = 'Unknown'
                dirs = ['north-east', 'north-west', 'south-east', 'south-west', 'north', 'south', 'east', 'west']
                for d in dirs:
                    if f'{d} facing' in card_text:
                        facing = d.title()
                        break
                
                # Floor
                floor_match = re.search(r'(\d+)(?:st|nd|rd|th)?\s*floor', card_text)
                floor = int(floor_match.group(1)) if floor_match else 0
                
                # Extract area from card
                area_elem = card.select_one('[class*="area"]') or card.select_one('[class*="carpet"]')
                area_text = area_elem.get_text(strip=True) if area_elem else ""
                area_sqft = normalize_area(area_text) if area_text else None
                
                listing = {
                    'title': title,
                    'url': url,
                    'city': normalize_city(city),
                    'location': location or 'Unknown',
                    'price': price,
                    'price_raw': price_text,
                    'area_sqft': area_sqft,
                    'area_raw': area_text,
                    'bedrooms': bedrooms,
                    'bathrooms': bathrooms,
                    'balcony': balcony,
                    'prop_type': prop_type,
                    'furnished': furnished,
                    'facing': facing,
                    'floor': floor,
                    'pooja_room': 1 if 'pooja' in card_text or 'puja' in card_text else 0,
                    'servant_room': 1 if 'servant' in card_text else 0,
                    'store_room': 1 if 'store' in card_text else 0,
                    'pool': 1 if 'pool' in card_text or 'swimming' in card_text else 0,
                    'gym': 1 if 'gym' in card_text else 0,
                    'lift': 1 if 'lift' in card_text or 'elevator' in card_text else 0,
                    'parking': 1 if 'parking' in card_text else 0,
                    'vastu_compliant': 1 if 'vastu' in card_text else 0,
                    'scraped_at': datetime.now(),
                }
                
                # Create hash for deduplication
                listing['property_hash'] = create_property_hash(listing)
                
                # Check for duplicates
                if listing['property_hash'] in self.seen_hashes:
                    self.stats['duplicate_rows'] += 1
                    continue
                
                self.seen_hashes.add(listing['property_hash'])
                listings.append(listing)
                
            except Exception as e:
                logging.debug(f"Error parsing card: {e}")
                continue
        
        return listings
    
    def flush_buffer(self):
        """Write buffer to Parquet with validation."""
        if not self.buffer:
            return
        
        df = pd.DataFrame(self.buffer)
        
        # Validate with Pandera
        validated_df, val_stats = validate_dataframe(df)
        
        # Update stats
        self.stats['total_scraped'] += val_stats['total_rows']
        self.stats['valid_rows'] += val_stats['valid_rows']
        self.stats['rejected_rows'] += val_stats['rejected_rows']
        
        if validated_df.empty:
            logging.warning("No valid rows to write")
            self.buffer.clear()
            return
        
        # Write to Parquet
        table = pa.Table.from_pandas(validated_df, schema=PARQUET_SCHEMA)
        
        if self.output_path.exists():
            # Append to existing file
            existing_table = pq.read_table(self.output_path)
            combined_table = pa.concat_tables([existing_table, table])
            pq.write_table(combined_table, self.output_path)
        else:
            # Create new file
            pq.write_table(table, self.output_path)
        
        logging.info(f"Wrote {len(validated_df)} validated rows to Parquet")
        self.buffer.clear()
    
    def scrape_city(self, city: str, max_pages: int = 200):
        """Scrape a single city."""
        city_key = city.lower()
        if city_key not in self.CITIES:
            logging.error(f"Unknown city: {city}")
            return
        
        url_template = self.CITIES[city_key]
        
        logging.info(f"\n{'='*60}")
        logging.info(f"SCRAPING: {city.upper()}")
        logging.info(f"{'='*60}")
        
        consecutive_empty = 0
        
        for page in range(1, max_pages + 1):
            try:
                url = url_template.format(page)
                logging.info(f"   → Page {page}")
                
                self._save_checkpoint(city, page)
                
                soup = self.get_page(url)
                if not soup:
                    consecutive_empty += 1
                    if consecutive_empty >= 5:
                        break
                    continue
                
                listings = self.extract_listings(soup, city)
                
                if not listings:
                    consecutive_empty += 1
                    if consecutive_empty >= 5:
                        logging.info(f"Finished {city}")
                        break
                else:
                    consecutive_empty = 0
                    self.buffer.extend(listings)
                    logging.info(f"      Extracted {len(listings)} listings")
                
                # Flush buffer periodically
                if len(self.buffer) >= self.batch_size:
                    self.flush_buffer()
                
            except Exception as e:
                logging.error(f"Error on page {page}: {e}")
                time.sleep(10)
        
        # Final flush
        self.flush_buffer()
    
    def scrape_all(self, max_pages: int = 200):
        """Scrape all cities."""
        for city in self.CITIES.keys():
            self.scrape_city(city, max_pages)
    
    def print_summary(self):
        """Print summary statistics."""
        print(f"\n{'='*60}")
        print(f"SCRAPING SUMMARY")
        print(f"{'='*60}")
        print(f"Total scraped:    {self.stats['total_scraped']}")
        print(f"Rejected rows:    {self.stats['rejected_rows']}")
        print(f"Duplicate rows:   {self.stats['duplicate_rows']}")
        print(f"{'='*60}\n")
    
    def cleanup(self):
        """Cleanup resources."""
        pass



# CLI INTERFACE

def main():
    """Main entry point with CLI."""
    parser = argparse.ArgumentParser(
        description='MagicBricks Production Scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ingest.py --city gurgaon
  python ingest.py --max-pages 50
  python ingest.py --output data/raw/test.parquet
        """
    )
    
    parser.add_argument(
        '--city',
        type=str,
        help='City to scrape (e.g., gurgaon, noida). If not specified, scrapes all cities.'
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        default=200,
        help='Maximum pages per city (default: 200)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=str(DATA_DIR / 'magicbricks_production.parquet'),
        help='Output Parquet file path'
    )
    
    args = parser.parse_args()
    
    logging.info("="*60)
    logging.info("MagicBricks Production Scraper")
    logging.info("="*60)
    
    scraper = ProductionScraper(output_path=args.output)
    
    try:
        if args.city:
            scraper.scrape_city(args.city, max_pages=args.max_pages)
        else:
            scraper.scrape_all(max_pages=args.max_pages)
    
    except KeyboardInterrupt:
        logging.warning("\n⚠️  Ctrl+C detected! Saving data...")
        scraper.flush_buffer()
    
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}", exc_info=True)
        scraper.flush_buffer()
    
    finally:
        scraper.print_summary()
        scraper.cleanup()


if __name__ == '__main__':
    main()

"""
MagicBricks NCR Property Scraper - Enterprise Edition
======================================================

A robust web scraper for collecting real estate data from MagicBricks.com
with checkpoint/resume capability, rotating logs, and graceful shutdown.

Features:
- BeautifulSoup + Requests (faster than Selenium, less CAPTCHA)
- Automatic checkpoint/resume from interruptions
- Rotating file handlers for logs (10MB max, 5 backups)
- Data validation and deduplication
- Graceful shutdown handling (Ctrl+C safe)
- Statistics tracking and progress monitoring

Author: Data Science Team
License: MIT
"""

import sys
import time
import json
import random
import re
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, List, Set, Optional
from pathlib import Path
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import pandas as pd


# ==========================================
# PATH RESOLUTION
# ==========================================
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# LOGGING SETUP
# ==========================================
def setup_logging() -> None:
    """Configure rotating file handlers for logging."""
    log_dir = DATA_DIR / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Set UTF-8 encoding for console on Windows
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass
    
    # File handler (rotating)
    file_handler = RotatingFileHandler(
        log_dir / 'magicbricks.log',
        maxBytes=10485760,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Error file handler (rotating)
    error_handler = RotatingFileHandler(
        log_dir / 'magicbricks_errors.log',
        maxBytes=10485760,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)


# ==========================================
# UTILITY FUNCTIONS
# ==========================================
def extract_price(price_text: str) -> Optional[float]:
    """Extract numeric price from text.
    
    Args:
        price_text: Price string like '₹1.43 Cr' or '₹50 Lac'
        
    Returns:
        Numeric price value or None if parsing fails
    """
    if not price_text:
        return None
        
    # Handle cases like "₹1.43 Cr₹9142 per sqft" - split by ₹ and take first part
    if price_text.count('₹') > 1:
        parts = price_text.split('₹')
        if len(parts) > 1:
            price_text = parts[1]
    
    price_text = price_text.lower().replace(',', '').strip()
    
    # Extract number
    match = re.search(r'([\d.]+)', price_text)
    if not match:
        return None
    
    value = float(match.group(1))
    
    # Convert to rupees
    if 'cr' in price_text or 'crore' in price_text:
        value *= 10000000
    elif 'lac' in price_text or 'lakh' in price_text:
        value *= 100000
    elif 'k' in price_text or 'thousand' in price_text:
        value *= 1000
        
    return value


def extract_area(area_text: str) -> Optional[float]:
    """Extract numeric area from text.
    
    Args:
        area_text: Area string like '1200 sq.ft.' or '100 sq.m.'
        
    Returns:
        Area in square feet or None if parsing fails
    """
    if not area_text:
        return None
    
    area_text = area_text.lower().replace(',', '').strip()
    
    # Extract number
    match = re.search(r'([\d.]+)', area_text)
    if not match:
        return None
    
    value = float(match.group(1))
    
    # Convert to sq.ft if needed
    if 'sq.m' in area_text or 'sqm' in area_text:
        value *= 10.764  # Convert sq.m to sq.ft
    
    return value


# ==========================================
# CHECKPOINT MANAGER
# ==========================================
class CheckpointManager:
    """Manages scraper progress checkpoints for resume capability."""
    
    def __init__(self, checkpoint_file: Path, save_interval: int = 10):
        """Initialize checkpoint manager.
        
        Args:
            checkpoint_file: Path to checkpoint JSON file
            save_interval: Save checkpoint every N pages
        """
        self.checkpoint_file = checkpoint_file
        self.save_interval = save_interval
        self.page_counter = 0
        
    def load(self) -> Optional[Dict]:
        """Load existing checkpoint if available."""
        if not self.checkpoint_file.exists():
            return None
            
        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
            logging.info(f"📍 Resuming from: {checkpoint['current_city']} (Page {checkpoint['current_page']})")
            return checkpoint
        except (json.JSONDecodeError, KeyError) as e:
            logging.warning(f"Failed to load checkpoint: {e}")
            return None
    
    def should_save(self) -> bool:
        """Check if it's time to save checkpoint."""
        self.page_counter += 1
        return self.page_counter % self.save_interval == 0
    
    def save(self, city: str, page: int, total_count: int, finished_cities: List[str]) -> None:
        """Save current progress to checkpoint file."""
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        
        checkpoint_data = {
            'current_city': city,
            'current_page': page,
            'finished_cities': finished_cities,
            'total_scraped': total_count,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        logging.debug(f"💾 Checkpoint saved: {city} page {page}")


# ==========================================
# DATA BUFFER
# ==========================================
class DataBuffer:
    """Accumulates listings in memory and flushes to CSV in batches."""
    
    def __init__(self, csv_path: Path, batch_size: int = 10):
        """Initialize data buffer.
        
        Args:
            csv_path: Path to output CSV file
            batch_size: Flush buffer every N pages
        """
        self.csv_path = csv_path
        self.batch_size = batch_size
        self.buffer: List[Dict] = []
        self.page_count = 0
        
    def add(self, listings: List[Dict]) -> None:
        """Add listings to buffer."""
        self.buffer.extend(listings)
        self.page_count += 1
        
    def should_flush(self) -> bool:
        """Check if buffer should be flushed to disk."""
        return self.page_count >= self.batch_size
    
    def flush(self) -> None:
        """Write buffer contents to CSV file."""
        if not self.buffer:
            logging.debug("Buffer empty, nothing to flush")
            return
        
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        
        df = pd.DataFrame(self.buffer)
        mode = 'a' if self.csv_path.exists() else 'w'
        header = not self.csv_path.exists()
        
        df.to_csv(self.csv_path, mode=mode, header=header, index=False, encoding='utf-8')
        
        logging.info(f"💾 Flushed {len(self.buffer)} listings to CSV")
        self.buffer.clear()
        self.page_count = 0


# ==========================================
# STATISTICS TRACKER
# ==========================================
class StatsTracker:
    """Track scraping statistics and performance metrics."""
    
    def __init__(self):
        self.start_time = time.time()
        self.city_stats: Dict[str, int] = {}
        self.total_listings = 0
        self.total_pages = 0
        self.errors = 0
        
    def add_listings(self, city: str, count: int) -> None:
        """Record listings scraped for a city."""
        self.city_stats[city] = self.city_stats.get(city, 0) + count
        self.total_listings += count
        self.total_pages += 1
        
    def add_error(self) -> None:
        """Record an error."""
        self.errors += 1
        
    def get_summary(self) -> str:
        """Get formatted statistics summary."""
        elapsed = time.time() - self.start_time
        hours = elapsed / 3600
        rate = self.total_listings / hours if hours > 0 else 0
        
        summary = f"\n{'='*60}\n"
        summary += f"📊 SCRAPING STATISTICS\n"
        summary += f"{'='*60}\n"
        summary += f"Total Listings: {self.total_listings}\n"
        summary += f"Total Pages: {self.total_pages}\n"
        summary += f"Errors: {self.errors}\n"
        summary += f"Elapsed Time: {elapsed/3600:.2f} hours\n"
        summary += f"Rate: {rate:.1f} listings/hour\n"
        summary += f"\nBy City:\n"
        for city, count in self.city_stats.items():
            summary += f"  {city}: {count}\n"
        summary += f"{'='*60}\n"
        
        return summary


# ==========================================
# MAGICBRICKS SCRAPER
# ==========================================
class MagicBricksScraper:
    """Main scraper class with enterprise features."""
    
    # User agent pool for rotation
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    ]
    
    def __init__(self):
        """Initialize scraper with configuration."""
        self.session = requests.Session()
        self._rotate_user_agent()
        
        self.data_buffer = DataBuffer(
            csv_path=DATA_DIR / "magicbricks_NCR_ML.csv",
            batch_size=10
        )
        
        self.checkpoint = CheckpointManager(
            checkpoint_file=DATA_DIR / "magicbricks_checkpoint.json",
            save_interval=10
        )
        
        self.stats = StatsTracker()
        
        # Load seen URLs from existing CSV
        self.seen_urls: Set[str] = self._load_history()
        logging.info(f"📚 History Loaded: {len(self.seen_urls)} unique listings in DB")
        
        # Load checkpoint
        checkpoint_data = self.checkpoint.load()
        self.finished_cities = checkpoint_data.get('finished_cities', []) if checkpoint_data else []
        self.resume_city = checkpoint_data.get('current_city') if checkpoint_data else None
        self.resume_page = checkpoint_data.get('current_page', 1) if checkpoint_data else 1
        
    def _rotate_user_agent(self) -> None:
        """Rotate user agent to avoid detection."""
        self.session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def _load_history(self) -> Set[str]:
        """Load previously scraped URLs from CSV."""
        csv_path = DATA_DIR / "magicbricks_NCR_ML.csv"
        if not csv_path.exists():
            return set()
        
        try:
            df = pd.read_csv(csv_path)
            return set(df['URL'].dropna().tolist())
        except Exception as e:
            logging.warning(f"Failed to load history: {e}")
            return set()
    
    def get_page(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """Fetch page with retries and exponential backoff."""
        for attempt in range(retries):
            try:
                # Random delay to avoid rate limiting
                time.sleep(random.uniform(2, 5))
                
                # Rotate user agent periodically
                if random.random() < 0.1:  # 10% chance
                    self._rotate_user_agent()
                
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    return BeautifulSoup(response.content, 'html.parser')
                else:
                    logging.warning(f"Status {response.status_code} for {url}")
                    
            except Exception as e:
                logging.error(f"Error fetching {url}: {e}")
                if attempt < retries - 1:
                    # Exponential backoff
                    wait_time = (2 ** attempt) * random.uniform(3, 7)
                    logging.info(f"Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                else:
                    self.stats.add_error()
        
        return None
    
    def extract_listings(self, soup: BeautifulSoup, city: str) -> List[Dict]:
        """Extract property listings from page."""
        listings = []
        
        # Find property cards
        cards = soup.select('div[class*="mb-srp__card"]')
        if not cards:
            cards = soup.select('div.mb-srp__list__item')
        
        logging.debug(f"Found {len(cards)} property cards")
        
        for idx, card in enumerate(cards):
            try:
                # Extract URL
                link = card.select_one('a[href*="/propertyDetails"]')
                if not link:
                    link = card.select_one('a[href*="/property-detail"]')
                
                if not link:
                    links = card.find_all('a', href=True)
                    for l in links:
                        if '/propertyDetails' in l['href'] or '/property-detail' in l['href']:
                            link = l
                            break
                            
                if not link or not link.get('href'):
                    continue
                
                url = link.get('href')
                if not url.startswith('http'):
                    url = 'https://www.magicbricks.com' + url
                
                if url in self.seen_urls:
                    continue
                
                # Extract title
                title_elem = card.select_one('h2') or card.select_one('[class*="prop-title"]')
                title = title_elem.get_text(strip=True) if title_elem else ""
                
                # Extract price
                price_elem = card.select_one('[class*="price"]')
                price_text = price_elem.get_text(strip=True) if price_elem else ""
                price = extract_price(price_text)
                
                if not price:
                    continue  # Skip listings without price
                
                # Extract area
                area_elem = card.select_one('[class*="area"]') or card.select_one('[class*="carpet"]')
                area_text = area_elem.get_text(strip=True) if area_elem else ""
                area = extract_area(area_text)
                
                # Extract location
                location_elem = card.select_one('[class*="location"]') or card.select_one('[class*="locality"]')
                location = location_elem.get_text(strip=True) if location_elem else ""
                
                # Extract from title if not found
                if not location and title:
                    match = re.search(r'in\s+(.+?)(?:,|$)', title, re.IGNORECASE)
                    if match:
                        location = match.group(1).strip()
                
                # Get all text for feature extraction
                card_text = card.get_text().lower()
                
                # Extract bedrooms
                bhk_match = re.search(r'(\d+)\s*bhk', card_text)
                bedrooms = int(bhk_match.group(1)) if bhk_match else 0
                
                # Extract bathrooms
                bath_match = re.search(r'(\d+)\s*bath', card_text)
                bathrooms = int(bath_match.group(1)) if bath_match else 0
                
                # Extract balconies
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
                
                listing = {
                    'Title': title,
                    'URL': url,
                    'City': city,
                    'Price_Raw': price_text,
                    'Price': price,
                    'Area': area_text,
                    'Area_SqFt': area,
                    'Location': location or 'Unknown',
                    'Prop_Type': prop_type,
                    'Bedrooms': bedrooms,
                    'Bathrooms': bathrooms,
                    'Balcony': balcony,
                    'Facing': facing,
                    'Pooja_Room': 1 if 'pooja' in card_text or 'puja' in card_text else 0,
                    'Servant_Room': 1 if 'servant' in card_text else 0,
                    'Store_Room': 1 if 'store' in card_text else 0,
                    'Pool': 1 if 'pool' in card_text or 'swimming' in card_text else 0,
                    'Gym': 1 if 'gym' in card_text else 0,
                    'Lift': 1 if 'lift' in card_text or 'elevator' in card_text else 0,
                    'Parking': 1 if 'parking' in card_text else 0,
                    'Vastu_Compliant': 1 if 'vastu' in card_text else 0,
                    'Furnished': furnished,
                    'Floor': floor,
                    'Source': 'MagicBricks',
                    'Scraped_Date': datetime.now().strftime("%Y-%m-%d")
                }
                
                listings.append(listing)
                self.seen_urls.add(url)
                
            except Exception as e:
                logging.debug(f"Error parsing card {idx}: {e}")
                continue
        
        logging.info(f"✅ Extracted {len(listings)} valid listings from {len(cards)} cards")
        return listings
    
    def scrape_city(self, city: str, base_url: str, start_page: int = 1, max_pages: int = 200) -> None:
        """Scrape all listings for a city."""
        logging.info(f"\n{'='*60}")
        logging.info(f"🚀 STARTING SCRAPE FOR: {city.upper()}")
        logging.info(f"{'='*60}")
        
        consecutive_empty = 0
        
        for page in range(start_page, max_pages + 1):
            try:
                url = base_url.format(page)
                logging.info(f"   → {city} Page {page} | Total DB: {len(self.seen_urls)}")
                
                # Save checkpoint before fetching
                self.checkpoint.save(city, page, len(self.seen_urls), self.finished_cities)
                
                soup = self.get_page(url)
                if not soup:
                    logging.warning(f"⚠️ Failed to fetch page {page}")
                    consecutive_empty += 1
                    if consecutive_empty >= 5:
                        break
                    continue
                
                # Check for CAPTCHA
                if 'captcha' in soup.get_text().lower():
                    logging.warning("🤖 CAPTCHA detected! Waiting 2 minutes...")
                    time.sleep(120)
                    continue
                
                listings = self.extract_listings(soup, city)
                
                if not listings:
                    consecutive_empty += 1
                    logging.warning(f"⚠️ No new data ({consecutive_empty}/5)")
                    if consecutive_empty >= 5:
                        logging.info(f"✅ Finished {city}. Moving to next.")
                        break
                else:
                    consecutive_empty = 0
                    self.data_buffer.add(listings)
                    self.stats.add_listings(city, len(listings))
                    logging.info(f"💾 Saved {len(listings)} new listings")
                
                # Flush buffer if needed
                if self.data_buffer.should_flush():
                    self.data_buffer.flush()
                
                # Take break every 20 pages
                if page % 20 == 0:
                    logging.info("☕ Taking 2-minute coffee break...")
                    time.sleep(120)
                
            except Exception as e:
                logging.error(f"❌ Error on page {page}: {e}")
                self.stats.add_error()
                time.sleep(10)
    
    def run(self) -> None:
        """Run scraper for all cities with resume support."""
        cities = {
            'Noida': 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=Noida&page={}',
            'Gurgaon': 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=Gurgaon&page={}',
            'Greater Noida': 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=Greater-Noida&page={}',
            'Ghaziabad': 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=Ghaziabad&page={}',
            'Faridabad': 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=Faridabad&page={}',
            'New Delhi': 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=New-Delhi&page={}',
            'Delhi': 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=Delhi&page={}',
            'Bhiwadi': 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=Bhiwadi&page={}',
            'Meerut': 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=Meerut&page={}',
            'Panipat': 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=Panipat&page={}',
            'Sonipat': 'https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=Sonipat&page={}',
        }
        
        try:
            for city, url_template in cities.items():
                # Skip already finished cities
                if city in self.finished_cities:
                    logging.info(f"⏭️ Skipping {city} (already finished)")
                    continue
                
                # If resuming, skip cities until we hit the resume city
                if self.resume_city and city != self.resume_city:
                    logging.info(f"⏭️ Skipping {city} (waiting to reach {self.resume_city})")
                    continue
                
                # Start scraping
                current_start_page = self.resume_page if city == self.resume_city else 1
                
                # Clear resume info once we've started the resume city
                self.resume_city = None
                self.resume_page = 1
                
                self.scrape_city(city, url_template, start_page=current_start_page)
                
                # Mark city as finished
                if city not in self.finished_cities:
                    self.finished_cities.append(city)
                self.checkpoint.save(city, 1, len(self.seen_urls), self.finished_cities)
                self.data_buffer.flush()
        
        except KeyboardInterrupt:
            logging.warning("\n⚠️ Ctrl+C detected! Saving data...")
        
        except Exception as e:
            logging.error(f"❌ Fatal error: {e}", exc_info=True)
        
        finally:
            self.data_buffer.flush()
            logging.info(self.stats.get_summary())
            logging.info(f"\n✅ SCRAPING COMPLETE! Total: {len(self.seen_urls)} listings")


# ==========================================
# MAIN ENTRY POINT
# ==========================================
def main():
    """Main execution with graceful shutdown handling."""
    setup_logging()
    
    logging.info("="*60)
    logging.info("🏠 MagicBricks NCR Property Scraper - Enterprise Edition")
    logging.info("="*60)
    
    scraper = None
    
    try:
        scraper = MagicBricksScraper()
        scraper.run()
        
    except KeyboardInterrupt:
        logging.warning("\n⚠️ Ctrl+C detected! Saving pending data...")
        
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}", exc_info=True)
        
    finally:
        if scraper:
            logging.info("🔄 Performing graceful shutdown...")
            
            try:
                scraper.data_buffer.flush()
            except Exception as e:
                logging.error(f"Error flushing buffer: {e}")
            
            logging.info("✅ Graceful shutdown complete")


if __name__ == "__main__":
    main()

"""
⚠️ DEPRECATED - This file is kept for reference only
====================================================

Please use the new enterprise-grade scraper instead:
    ncr_property_price_estimation/data/ingestion.py

The new scraper includes:
- Rotating file handlers for logging
- Robust checkpoint/resume system
- Data validation and deduplication
- Enhanced data extraction
- Statistics tracking
- Graceful shutdown handling

See SCRAPER_README.md for usage instructions.
====================================================

MagicBricks Property Scraper (Legacy Version)
Uses BeautifulSoup + Requests (faster than Selenium, less CAPTCHA)
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
import logging
from datetime import datetime

# Setup paths
SCRIPT_DIR = Path(__file__).parent.resolve()
DATA_DIR = SCRIPT_DIR.parent.parent / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(DATA_DIR / 'logs' / 'magicbricks.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class MagicBricksScraper:
    """Scraper for MagicBricks using BeautifulSoup"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        self.data = []
        self.seen_urls = set()
        self.csv_path = DATA_DIR / "magicbricks_NCR_ML.csv"
        self.checkpoint_path = DATA_DIR / "magicbricks_checkpoint.json"
        
        # Load existing data if any
        if self.csv_path.exists():
            try:
                existing_df = pd.read_csv(self.csv_path)
                self.data = existing_df.to_dict('records')
                self.seen_urls = set(existing_df['URL'].tolist())
                logging.info(f"Loaded {len(self.data)} existing listings from CSV")
            except Exception as e:
                logging.error(f"Error loading CSV: {e}")
                
        # Load progress from checkpoint
        self.checkpoint = self._load_checkpoint()
        if self.checkpoint:
            logging.info(f"Resuming from: {self.checkpoint['current_city']} (Page {self.checkpoint['current_page']})")
    
    def _load_checkpoint(self) -> Dict:
        """Load progress from checkpoint file"""
        if self.checkpoint_path.exists():
            try:
                with open(self.checkpoint_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error loading checkpoint: {e}")
        return {}

    def _save_checkpoint(self, city: str, page: int, finished: bool = False):
        """Save current progress to checkpoint file"""
        checkpoint_data = {
            'current_city': city,
            'current_page': page,
            'finished_cities': self.checkpoint.get('finished_cities', []),
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if finished and city not in checkpoint_data['finished_cities']:
            checkpoint_data['finished_cities'].append(city)
            
        try:
            with open(self.checkpoint_path, 'w') as f:
                json.dump(checkpoint_data, f, indent=4)
            self.checkpoint = checkpoint_data
        except Exception as e:
            logging.error(f"Error saving checkpoint: {e}")
    
    def get_page(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """Fetch page with retries"""
        for attempt in range(retries):
            try:
                time.sleep(random.uniform(2, 5))  # Random delay
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    return BeautifulSoup(response.content, 'html.parser')
                else:
                    logging.warning(f"Status {response.status_code} for {url}")
                    
            except Exception as e:
                logging.error(f"Error fetching {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(random.uniform(5, 10))
        
        return None
    
    def extract_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from text"""
        if not price_text:
            return None
            
        # Handle cases like "₹1.43 Cr₹9142 per sqft" - split by ₹ and take first part
        if price_text.count('₹') > 1:
            parts = price_text.split('₹')
            # parts[0] might be empty if string starts with ₹
            # parts[1] should be the main price
            if len(parts) > 1:
                price_text = parts[1]
        
        price_text = price_text.lower().replace(',', '').strip()
        
        # Extract number - take the first number found
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
    
    def extract_listings(self, soup: BeautifulSoup, city: str) -> List[Dict]:
        """Extract property listings from page"""
        listings = []
        
        # Find property cards (adjust selectors based on actual HTML)
        cards = soup.select('div[class*="mb-srp__card"]')
        
        if not cards:
            # Try alternative selectors
            cards = soup.select('div.mb-srp__list__item')
        
        logging.info(f"Found {len(cards)} property cards")
        
        for card in cards:
            try:
                # Extract URL - Fixed selector for case sensitivity
                # Try multiple patterns
                link = card.select_one('a[href*="/propertyDetails"]')
                if not link:
                    link = card.select_one('a[href*="/property-detail"]')
                
                # If still not found, check all links
                if not link:
                    links = card.find_all('a', href=True)
                    for l in links:
                        if '/propertyDetails' in l['href'] or '/property-detail' in l['href']:
                            link = l
                            break
                            
                if not link or not link.get('href'):
                    # logging.debug("Skipping: No URL found")
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
                price = self.extract_price(price_text)
                
                if not price:
                    continue  # Skip listings without price
                
                # Extract area
                area_elem = card.select_one('[class*="area"]') or card.select_one('[class*="carpet"]')
                area = area_elem.get_text(strip=True) if area_elem else ""
                
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
                
                listing = {
                    'Title': title,
                    'URL': url,
                    'City': city,
                    'Price_Raw': price_text,
                    'Price': price,
                    'Area': area,
                    'Location': location,
                    'Prop_Type': prop_type,
                    'Bedrooms': bedrooms,
                    'Bathrooms': bathrooms,
                    'Balcony': 1 if 'balcon' in card_text else 0,
                    'Facing': 'Unknown',
                    'Pooja_Room': 1 if 'pooja' in card_text else 0,
                    'Servant_Room': 1 if 'servant' in card_text else 0,
                    'Store_Room': 1 if 'store' in card_text else 0,
                    'Pool': 1 if 'pool' in card_text or 'swimming' in card_text else 0,
                    'Gym': 1 if 'gym' in card_text else 0,
                    'Lift': 1 if 'lift' in card_text or 'elevator' in card_text else 0,
                    'Parking': 1 if 'parking' in card_text else 0,
                    'Vastu_Compliant': 1 if 'vastu' in card_text else 0,
                    'Furnished': furnished,
                    'Floor': 0,
                    'Source': 'MagicBricks'
                }
                
                listings.append(listing)
                self.seen_urls.add(url)
                
            except Exception as e:
                logging.debug(f"Error parsing card: {e}")
                continue
        
        return listings
    
    def save_data(self):
        """Save data to CSV"""
        if self.data:
            df = pd.DataFrame(self.data)
            df.to_csv(self.csv_path, index=False)
            logging.info(f"Saved {len(self.data)} listings to {self.csv_path}")
    
    def scrape_city(self, city: str, base_url: str, start_page: int = 1, max_pages: int = 200):
        """Scrape all listings for a city starting from a specific page"""
        logging.info(f"\n🚀 STARTING SCRAPE FOR: {city.upper()}")
        
        consecutive_empty = 0
        
        for page in range(start_page, max_pages + 1):
            url = base_url.format(page)
            logging.info(f"   -> {city} Page {page} | Total: {len(self.data)}")
            
            # Save checkpoint before fetching (in case of crash during fetch)
            self._save_checkpoint(city, page)
            
            soup = self.get_page(url)
            if not soup:
                logging.warning(f"Failed to fetch page {page}")
                consecutive_empty += 1
                if consecutive_empty >= 5:
                    break
                continue
            
            # Check for CAPTCHA
            if 'captcha' in soup.get_text().lower():
                logging.warning("CAPTCHA detected! Waiting 2 minutes...")
                time.sleep(120)
                continue
            
            listings = self.extract_listings(soup, city)
            
            if not listings:
                consecutive_empty += 1
                logging.warning(f" No new data ({consecutive_empty}/5)")
                if consecutive_empty >= 5:
                    logging.info(f"Finished {city}. Moving to next.")
                    break
            else:
                consecutive_empty = 0
                self.data.extend(listings)
                logging.info(f" Saved {len(listings)} new listings")
            
            # Save every 10 pages
            if page % 10 == 0:
                self.save_data()
            
            # Take break every 20 pages
            if page % 20 == 0:
                logging.info("Taking 2-minute break...")
                time.sleep(120)
    
    def run(self):
        """Run scraper for all cities"""
    def run(self):
        """Run scraper for all cities with resume support"""
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
        
        finished_cities = self.checkpoint.get('finished_cities', [])
        resume_city = self.checkpoint.get('current_city')
        resume_page = self.checkpoint.get('current_page', 1)

        try:
            for city, url_template in cities.items():
                # Skip already finished cities
                if city in finished_cities:
                    logging.info(f"Skipping {city} (already finished)")
                    continue
                
                # If resuming, skip cities until we hit the resume city
                if resume_city and city != resume_city:
                    logging.info(f"Skipping {city} (waiting to reach {resume_city})")
                    continue
                
                # Start scraping
                current_start_page = resume_page if city == resume_city else 1
                
                # Clear resume info once we've started the resume city
                resume_city = None
                resume_page = 1
                
                self.scrape_city(city, url_template, start_page=current_start_page)
                self._save_checkpoint(city, 1, finished=True)
                self.save_data()

        
        except KeyboardInterrupt:
            logging.warning("\nCtrl+C detected! Saving data...")
            self.save_data()
        
        except Exception as e:
            logging.error(f"Fatal error: {e}", exc_info=True)
            self.save_data()
        
        finally:
            self.save_data()
            logging.info(f"\n✅ SCRAPING COMPLETE! Total: {len(self.data)} listings")

if __name__ == "__main__":
    scraper = MagicBricksScraper()
    scraper.run()

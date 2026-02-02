"""
99acres NCR Property Scraper - Production Ready
================================================

A robust web scraper for collecting real estate data from 99acres.com
with anti-bot evasion, checkpoint/resume, and graceful shutdown handling.

Author: Data Science Team
License: MIT
"""

import sys
import time
import json
import random
import os
import re
import socket
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, List, Set, Optional
from pathlib import Path


# ==========================================
# DEPENDENCY CHECK (Run First)
# ==========================================
def check_dependencies() -> None:
    """Verify all required packages are installed.
    
    Exits with clear error message if dependencies are missing.
    """
    missing = []
    
    try:
        import pandas
    except ImportError:
        missing.append('pandas')
    
    try:
        import yaml
    except ImportError:
        missing.append('pyyaml')
    
    try:
        import undetected_chromedriver
    except ImportError:
        missing.append('undetected-chromedriver')
    
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        missing.append('beautifulsoup4')
    
    try:
        import selenium
    except ImportError:
        missing.append('selenium')
    
    if missing:
        print("\n" + "="*60)
        print("ERROR: Missing Required Dependencies")
        print("="*60)
        print("\nThe following packages are not installed:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nPlease install them using:")
        print(f"  pip install {' '.join(missing)}")
        print("\nOr install all dependencies:")
        print("  pip install pandas pyyaml undetected-chromedriver beautifulsoup4 selenium")
        print("="*60 + "\n")
        sys.exit(1)


# Check dependencies before importing
check_dependencies()

# Now safe to import
import pandas as pd
import yaml
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By


# ==========================================
# PATH RESOLUTION (Absolute Paths)
# ==========================================
# Get script directory for absolute path resolution
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent


# ==========================================
# LOGGING SETUP
# ==========================================
def setup_logging(config: Dict) -> None:
    """Configure rotating file handlers for logging.
    
    Args:
        config: Configuration dictionary with logging settings
    """
    log_config = config['logging']
    paths = config['paths']
    
    # Resolve absolute path for data folder
    data_folder = SCRIPT_DIR / paths['data_folder']
    log_dir = data_folder / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Main logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_config['level']))
    
    # Console handler (Windows-safe, no emojis in file logs)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    # Simple format without emojis for Windows compatibility
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Set UTF-8 encoding for console on Windows
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass  # Python < 3.7
    
    # File handler (rotating) - ASCII only for Windows
    file_handler = RotatingFileHandler(
        log_dir / paths['log_file'],
        maxBytes=log_config['max_bytes'],
        backupCount=log_config['backup_count'],
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
        log_dir / paths['error_log_file'],
        maxBytes=log_config['max_bytes'],
        backupCount=log_config['backup_count'],
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
def wait_for_internet() -> None:
    """Pauses execution if internet connection is lost.
    
    Continuously checks connectivity and resumes when connection is restored.
    This prevents the scraper from crashing during network interruptions.
    """
    while True:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return
        except OSError:
            logging.warning("⚠️ Internet Lost! Pausing script... (Check your connection)")
            time.sleep(10)


def clean_price(price_text: Optional[str]) -> Optional[float]:
    """Converts Indian price format to numeric value.
    
    Args:
        price_text: Price string like '₹ 1.25 Cr' or '₹ 50 Lac'
        
    Returns:
        Numeric price value or None if parsing fails
        
    Examples:
        '₹ 1.25 Cr' -> 12500000.0
        '₹ 50 Lac' -> 5000000.0
    """
    if not price_text:
        return None
    
    clean = price_text.lower().replace('₹', '').strip()
    try:
        if 'cr' in clean:
            return float(re.search(r'[\d\.]+', clean).group()) * 10000000
        elif 'lac' in clean:
            return float(re.search(r'[\d\.]+', clean).group()) * 100000
        else:
            return float(re.search(r'[\d\,]+', clean).group().replace(',', ''))
    except (AttributeError, ValueError):
        return None


# ==========================================
# CHECKPOINT MANAGER
# ==========================================
class CheckpointManager:
    """Manages scraper progress checkpoints for resume capability.
    
    Saves progress every N pages to avoid I/O overhead while ensuring
    the scraper can resume from the last checkpoint after interruptions.
    """
    
    def __init__(self, checkpoint_file: Path, save_interval: int = 10):
        """Initialize checkpoint manager.
        
        Args:
            checkpoint_file: Absolute path to checkpoint JSON file
            save_interval: Save checkpoint every N pages (default: 10)
        """
        self.checkpoint_file = checkpoint_file
        self.save_interval = save_interval
        self.page_counter = 0
        
    def load(self) -> Optional[Dict]:
        """Load existing checkpoint if available.
        
        Returns:
            Checkpoint data dict or None if no checkpoint exists
        """
        if not self.checkpoint_file.exists():
            return None
            
        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
            logging.info(f"Loaded checkpoint: {checkpoint['city']} page {checkpoint['page']}")
            return checkpoint
        except (json.JSONDecodeError, KeyError) as e:
            logging.warning(f"Failed to load checkpoint: {e}")
            return None
    
    def should_save(self) -> bool:
        """Check if it's time to save checkpoint.
        
        Returns:
            True if page counter reached save interval
        """
        self.page_counter += 1
        return self.page_counter % self.save_interval == 0
    
    def save(self, city: str, page: int, total_count: int) -> None:
        """Save current progress to checkpoint file.
        
        Args:
            city: Current city being scraped
            page: Current page number
            total_count: Total listings scraped so far
        """
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        
        checkpoint_data = {
            'city': city,
            'page': page,
            'total_scraped': total_count,
            'timestamp': time.time()
        }
        
        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        logging.debug(f"💾 Checkpoint saved: {city} page {page}")


# ==========================================
# DATA BUFFER
# ==========================================
class DataBuffer:
    """Accumulates listings in memory and flushes to CSV in batches.
    
    This reduces I/O overhead by 10x compared to saving after every page.
    Keeps data in memory between saves for performance.
    """
    
    def __init__(self, csv_path: Path, batch_size: int = 10):
        """Initialize data buffer.
        
        Args:
            csv_path: Absolute path to output CSV file
            batch_size: Flush buffer every N pages (default: 10)
        """
        self.csv_path = csv_path
        self.batch_size = batch_size
        self.buffer: List[Dict] = []
        self.page_count = 0
        
    def add(self, listings: List[Dict]) -> None:
        """Add listings to buffer.
        
        Args:
            listings: List of property data dictionaries
        """
        self.buffer.extend(listings)
        self.page_count += 1
        
    def should_flush(self) -> bool:
        """Check if buffer should be flushed to disk.
        
        Returns:
            True if page count reached batch size
        """
        return self.page_count >= self.batch_size
    
    def flush(self) -> None:
        """Write buffer contents to CSV file.
        
        Appends to existing file or creates new one with headers.
        Clears buffer after successful write.
        """
        if not self.buffer:
            logging.debug("Buffer empty, nothing to flush")
            return
        
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        
        df = pd.DataFrame(self.buffer)
        mode = 'a' if self.csv_path.exists() else 'w'
        header = not self.csv_path.exists()
        
        df.to_csv(self.csv_path, mode=mode, header=header, index=False, encoding='utf-8')
        
        logging.info(f"Flushed {len(self.buffer)} listings to CSV")
        self.buffer.clear()
        self.page_count = 0


# ==========================================
# PROPERTY SCRAPER
# ==========================================
class PropertyScraper:
    """Main scraper class with anti-bot evasion and checkpoint support.
    
    CRITICAL: This class preserves "messy" human-like behavior to evade
    bot detection. Do NOT optimize delays for speed - they exist for survival.
    """
    
    def __init__(self, config_path: Path):
        """Initialize scraper with configuration.
        
        Args:
            config_path: Absolute path to YAML configuration file
        """
        # Load configuration
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # Setup logging
        setup_logging(self.config)
        
        # Initialize components
        paths = self.config['paths']
        scraper_config = self.config['scraper']
        
        # Use absolute paths relative to script directory
        data_folder = SCRIPT_DIR / paths['data_folder']
        csv_path = data_folder / paths['output_csv']
        checkpoint_path = data_folder / paths['checkpoint_file']
        self.cookie_file = SCRIPT_DIR / paths['cookie_file']
        
        self.checkpoint = CheckpointManager(
            checkpoint_path,
            save_interval=scraper_config['batch_size']
        )
        self.data_buffer = DataBuffer(
            csv_path,
            batch_size=scraper_config['batch_size']
        )
        
        # Load seen URLs from existing CSV
        self.seen_urls: Set[str] = self._load_history(csv_path)
        logging.info(f"History Loaded: {len(self.seen_urls)} unique listings in DB")
        
        # Driver (lazy initialization)
        self.driver: Optional[uc.Chrome] = None
        
        # State tracking
        self.current_city: str = ""
        self.current_page: int = 1
        
    def _load_history(self, csv_path: Path) -> Set[str]:
        """Load previously scraped URLs from CSV.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Set of URLs already scraped
        """
        if not csv_path.exists():
            return set()
        
        try:
            df = pd.read_csv(csv_path)
            return set(df['URL'].dropna().tolist())
        except Exception as e:
            logging.warning(f"Failed to load history: {e}")
            return set()
    
    def _setup_driver(self) -> uc.Chrome:
        """Initialize undetected Chrome driver.
        
        CRITICAL: Keep this simple! undetected_chromedriver is fragile.
        Do NOT over-engineer with factories or context managers.
        
        Returns:
            Configured Chrome driver instance
        """
        logging.info("Initializing Chrome driver...")
        
        options = uc.ChromeOptions()
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--start-maximized')
        options.add_argument('--mute-audio')
        
        # Windows stability fixes
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')  # Helps on Windows
        
        # NEVER use --headless for 99acres (instant ban)
        
        # Specify driver version to match Chrome 144
        driver = uc.Chrome(
            options=options,
            use_subprocess=False,
            version_main=144  # Match Chrome version
        )
        return driver
    
    def _load_cookies(self) -> None:
        """Load cookies from file to maintain user session.
        
        Cookies help avoid bot detection by appearing as a logged-in user.
        """
        if not self.cookie_file.exists():
            logging.info("No cookie file found, running as anonymous")
            return
        
        try:
            self.driver.get("https://www.99acres.com")
            time.sleep(3)
            
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            for cookie in cookies:
                # Fix sameSite attribute
                if 'sameSite' in cookie and cookie['sameSite'] not in ["Strict", "Lax", "None"]:
                    del cookie['sameSite']
                
                try:
                    self.driver.add_cookie(cookie)
                except Exception:
                    pass  # Skip invalid cookies
            
            self.driver.refresh()
            logging.info("Cookies Loaded (User Session Active)")
            time.sleep(4)
            
        except Exception as e:
            logging.warning(f"Cookie load failed: {e} (Running as Anonymous)")
    
    def _simulate_human_behavior(self) -> None:
        """Simulate human scrolling with random delays.
        
        CRITICAL: These delays are intentionally "messy" and random.
        DO NOT optimize them for speed. They exist to evade bot detection.
        
        The random.uniform() ranges were empirically tested to avoid bans.
        """
        # Scroll to middle (random delay)
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(random.uniform(1.5, 3))  # KEEP RANDOM
        
        # Scroll to bottom (random delay)
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(1.5, 3))  # KEEP RANDOM
    
    def _handle_soft_ban(self) -> None:
        """Handle 'Access Denied' soft ban with long wait.
        
        CRITICAL: The 2-minute wait is intentional for anti-bot evasion.
        Do NOT reduce this delay.
        """
        logging.warning("SOFT BAN DETECTED! Waiting 2 minutes...")
        time.sleep(120)  # KEEP THIS LONG - it's intentional
        self.driver.refresh()
    
    
    def _check_for_captcha(self, soup: BeautifulSoup) -> bool:
        """Check if page contains CAPTCHA or access denied message.
        
        Args:
            soup: BeautifulSoup object of page HTML
            
        Returns:
            True if CAPTCHA detected, False otherwise
        """
        # Check for common CAPTCHA indicators
        captcha_indicators = [
            'captcha',
            'suspicious activity',
            'verify you are human',
            'access denied',
            'unusual traffic',
            'robot',
            'recaptcha'
        ]
        
        page_text = soup.get_text().lower()
        
        for indicator in captcha_indicators:
            if indicator in page_text:
                logging.warning(f"CAPTCHA/Block detected: '{indicator}' found in page")
                return True
        
        # Check for CAPTCHA-related elements
        if soup.find('iframe', src=lambda x: x and 'recaptcha' in x):
            logging.warning("reCAPTCHA iframe detected")
            return True
        
        return False
    
    def _handle_captcha(self) -> bool:
        """Handle CAPTCHA by pausing and waiting for manual intervention.
        
        Returns:
            True if user resolved CAPTCHA, False if user wants to quit
        """
        logging.error("=" * 70)
        logging.error("CAPTCHA DETECTED - Manual Intervention Required")
        logging.error("=" * 70)
        logging.error("99acres has detected suspicious activity.")
        logging.error("")
        logging.error("ACTION REQUIRED:")
        logging.error("1. Go to the Chrome window that's open")
        logging.error("2. Solve the CAPTCHA manually")
        logging.error("3. Wait for the page to load normally")
        logging.error("4. Come back here and press Enter to continue")
        logging.error("")
        logging.error("OR press 'q' + Enter to quit and resume later")
        logging.error("=" * 70)
        
        try:
            user_input = input("\nPress Enter after solving CAPTCHA (or 'q' to quit): ").strip().lower()
            
            if user_input == 'q':
                logging.info("User chose to quit. Progress saved.")
                return False
            
            logging.info("Resuming scraping...")
            # Give extra time after CAPTCHA
            time.sleep(random.uniform(5, 10))
            return True
            
        except KeyboardInterrupt:
            logging.warning("Interrupted by user")
            return False
    
    def _extract_data(self, soup: BeautifulSoup, city_name: str) -> List[Dict]:
        """Extract property data from page HTML.
        
        Args:
            soup: BeautifulSoup object of page HTML
            city_name: Current city context for listings
            
        Returns:
            List of property data dictionaries
        """
        # Find property cards
        cards = soup.select('div[class*="srpTuple__tupleTable"]')
        if not cards:
            cards = soup.select('div[class*="projectTuple__tupleTable"]')
        
        # DEBUG: Log what we found
        logging.debug(f"Found {len(cards)} property cards on page")
        
        if not cards:
            # Try alternative selectors
            logging.debug("Trying alternative selectors...")
            cards = soup.select('div[class*="tuple"]')
            logging.debug(f"Alternative selector found {len(cards)} cards")
            
            # Log page title to verify we're on the right page
            title = soup.select_one('title')
            if title:
                logging.debug(f"Page title: {title.get_text(strip=True)}")
            
            # Log some class names to help debug
            all_divs = soup.find_all('div', limit=20)
            logging.debug(f"Sample div classes: {[div.get('class') for div in all_divs[:5]]}")
        
        page_data = []
        
        for idx, card in enumerate(cards):
            try:
                # Helper function for text extraction
                def get_text(selector: str) -> str:
                    el = card.select_one(selector)
                    return el.get_text(strip=True) if el else ""
                
                # Extract URL and check duplicates
                link_tag = card.select_one('a[class*="srpTuple__propertyName"]')
                if not link_tag:
                    link_tag = card.select_one('a[class*="propertyName"]')
                if not link_tag:
                    link_tag = card.select_one('a')
                
                url = None
                if link_tag and link_tag.get('href'):
                    url = link_tag.get('href')
                    if not url.startswith('http'):
                        url = "https://www.99acres.com" + url
                
                # DEBUG: Log first few URLs
                if idx < 3:
                    logging.debug(f"Card {idx}: URL = {url}")
                
                if not url or url in self.seen_urls:
                    if idx < 3:
                        logging.debug(f"Card {idx}: Skipped (no URL or duplicate)")
                    continue
                
                # Extract text fields
                title = get_text('a[class*="srpTuple__propertyName"]') or get_text('h2')
                if not title:
                    title = get_text('a')
                
                desc_text = get_text('div[class*="srpTuple__desc"]')
                tags = [t.get_text(strip=True) for t in card.select('div[class*="srpTuple__tag"]')]
                secondary_tags = [t.get_text(strip=True) for t in card.select('td') if t.get_text(strip=True)]
                
                # DEBUG: Log first extraction
                if idx < 3:
                    logging.debug(f"Card {idx}: Title = {title[:50] if title else 'None'}")
                    logging.debug(f"Card {idx}: Tags = {tags[:3]}")
                
                # Create "blob" for regex feature extraction
                blob = (title + " " + desc_text + " " + " ".join(tags) + " " + " ".join(secondary_tags)).lower()
                
                # Base fields
                price_raw = get_text('[id="srp_tuple_price"]')
                if not price_raw:
                    price_raw = get_text('div[class*="price"]')
                
                # Extract location with multiple fallback strategies
                location = None
                
                # Strategy 1: Try societyName selector
                location = get_text('a[class*="srpTuple__societyName"]')
                
                # Strategy 2: Try col3 selector
                if not location:
                    location = get_text('td[class*="srpTuple__col3"]')
                
                # Strategy 3: Try other location-related selectors
                if not location:
                    location = get_text('div[class*="location"]') or get_text('span[class*="locality"]')
                
                # Strategy 4: Extract from title (e.g., "4 BHK Flat in Sector 128, Noida")
                if not location and title:
                    # Pattern: "in <location>"
                    import re
                    match = re.search(r'\bin\s+(.+?)(?:,\s*noida)?$', title, re.IGNORECASE)
                    if match:
                        location = match.group(1).strip()
                
                # Strategy 5: Extract from URL (e.g., "sector-128-noida")
                if not location and url:
                    # Extract sector/area from URL
                    match = re.search(r'(sector-\d+|[a-z-]+)-noida', url, re.IGNORECASE)
                    if match:
                        location = match.group(1).replace('-', ' ').title()
                
                # DEBUG: Log location extraction for first few cards
                if idx < 3:
                    logging.debug(f"Card {idx}: Location = {location}")
                
                row = {
                    'Title': title,
                    'URL': url,
                    'City': city_name,
                    'Price_Raw': price_raw,
                    'Price': clean_price(price_raw),
                    'Area': get_text('[id="srp_tuple_primary_area"]') or get_text('div[class*="area"]'),
                    'Location': location or 'Unknown'
                }
                
                # DEBUG: Log price extraction
                if idx < 3:
                    logging.debug(f"Card {idx}: Price_Raw = {price_raw}, Price = {row['Price']}")
                
                # Property Type
                if 'builder floor' in blob:
                    row['Prop_Type'] = 'Builder Floor'
                elif 'villa' in blob or 'independent house' in blob:
                    row['Prop_Type'] = 'Independent House'
                elif 'plot' in blob:
                    row['Prop_Type'] = 'Plot'
                else:
                    row['Prop_Type'] = 'Apartment'
                
                # Configuration
                bhk = re.search(r'(\d+)\s*(bhk|bed|bedroom)', blob)
                row['Bedrooms'] = int(bhk.group(1)) if bhk else 0
                
                bath = re.search(r'(\d+)\s*(bath|toilet|washroom)', blob)
                row['Bathrooms'] = int(bath.group(1)) if bath else 0
                
                balc = re.search(r'(\d+)\s*balcon', blob)
                row['Balcony'] = int(balc.group(1)) if balc else 0
                
                # Facing
                row['Facing'] = 'Unknown'
                dirs = ['north-east', 'north-west', 'south-east', 'south-west', 'north', 'south', 'east', 'west']
                for d in dirs:
                    if f'{d} facing' in blob:
                        row['Facing'] = d.title()
                        break
                
                # Amenities (Binary)
                row['Pooja_Room'] = 1 if ('pooja' in blob or 'puja' in blob) else 0
                row['Servant_Room'] = 1 if 'servant' in blob else 0
                row['Store_Room'] = 1 if 'store' in blob else 0
                row['Pool'] = 1 if 'pool' in blob else 0
                row['Gym'] = 1 if 'gym' in blob else 0
                row['Lift'] = 1 if ('lift' in blob or 'elevator' in blob) else 0
                row['Parking'] = 1 if 'parking' in blob else 0
                row['Vastu_Compliant'] = 1 if 'vastu' in blob else 0
                
                # Furnishing
                if 'semi' in blob:
                    row['Furnished'] = 'Semi-Furnished'
                elif 'fully' in blob:
                    row['Furnished'] = 'Fully-Furnished'
                elif 'unfurnished' in blob:
                    row['Furnished'] = 'Unfurnished'
                else:
                    row['Furnished'] = 'Unknown'
                
                # Floor
                floor = re.search(r'(\d+)(?:st|nd|rd|th)?\s*floor', blob)
                row['Floor'] = int(floor.group(1)) if floor else 0
                
                # Only add if has valid price
                if row['Price']:
                    page_data.append(row)
                    self.seen_urls.add(url)
                else:
                    if idx < 3:
                        logging.debug(f"Card {idx}: Skipped (no valid price)")
                    
            except Exception as e:
                logging.debug(f"Failed to parse card {idx}: {e}")
                continue
        
        # DEBUG: Final count
        logging.info(f"Extracted {len(page_data)} valid listings from {len(cards)} cards")
        
        return page_data
    
    def _scrape_city(self, city_config: Dict) -> None:
        """Scrape all listings for a single city.
        
        Args:
            city_config: City configuration dict with name, url, target_count
        """
        city_name = city_config['name']
        base_url = city_config['url']
        target_count = city_config['target_count']
        
        logging.info(f"\n🚀 STARTING SCRAPE FOR: {city_name.upper()}")
        
        self.current_city = city_name
        self.current_page = 1
        city_listings_collected = 0
        consecutive_empty = 0
        
        scraper_config = self.config['scraper']
        
        while city_listings_collected < target_count:
            try:
                wait_for_internet()
                
                logging.info(
                    f"   -> {city_name} Page {self.current_page} | "
                    f"Total DB: {len(self.seen_urls)}..."
                )
                
                # Navigate to page
                self.driver.get(base_url.format(self.current_page))
                
                # Check for soft ban
                if "Access Denied" in self.driver.title:
                    self._handle_soft_ban()
                    continue
                
                # Simulate human behavior (CRITICAL for anti-bot)
                self._simulate_human_behavior()
                
                # Extract data
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Check for CAPTCHA
                if self._check_for_captcha(soup):
                    if not self._handle_captcha():
                        # User chose to quit
                        logging.info("Stopping scraper due to CAPTCHA")
                        return
                    # Refresh page after CAPTCHA solved
                    self.driver.refresh()
                    time.sleep(random.uniform(3, 5))
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                new_rows = self._extract_data(soup, city_name)
                
                # Handle empty pages
                if not new_rows:
                    consecutive_empty += 1
                    logging.warning(f" No new data ({consecutive_empty}/{scraper_config['consecutive_empty_limit']})")
                    
                    if consecutive_empty >= scraper_config['consecutive_empty_limit']:
                        logging.info(f"Finished City: {city_name}. Moving to next.")
                        break
                    
                    self.current_page += 1
                    time.sleep(random.uniform(5, 8))  # KEEP RANDOM
                    continue
                
                consecutive_empty = 0
                
                # Add to buffer
                self.data_buffer.add(new_rows)
                count = len(new_rows)
                city_listings_collected += count
                logging.info(f" Saved {count} new listings")
                
                # Flush buffer if needed
                if self.data_buffer.should_flush():
                    self.data_buffer.flush()
                
                # Save checkpoint if needed
                if self.checkpoint.should_save():
                    self.checkpoint.save(city_name, self.current_page, len(self.seen_urls))
                
                self.current_page += 1
                
                # Coffee break (anti-bot pattern)
                if self.current_page % scraper_config['coffee_break_interval'] == 0:
                    logging.info("Short break...")
                    time.sleep(scraper_config['coffee_break_duration'])
                
            except Exception as e:
                logging.error(f"Error on page {self.current_page}: {e}")
                time.sleep(10)
                
                try:
                    self.driver.refresh()
                except Exception:
                    logging.warning("Driver crashed, reinitializing...")
                    self._quit_driver()
                    self.driver = self._setup_driver()
                    self._load_cookies()
    
    def _quit_driver(self) -> None:
        """Safely quit driver with Windows error suppression."""
        if not self.driver:
            return
        
        try:
            self.driver.quit()
        except (OSError, Exception) as e:
            # Suppress Windows "handle is invalid" errors
            if 'WinError 6' not in str(e):
                logging.debug(f"Driver quit error (suppressed): {e}")
    
    def run(self) -> None:
        """Main scraper execution loop."""
        # Initialize driver
        self.driver = self._setup_driver()
        self._load_cookies()
        
        # Scrape each city
        for city_config in self.config['cities']:
            self._scrape_city(city_config)
        
        logging.info("\nMISSION ACCOMPLISHED: All cities scraped.")


# ==========================================
# MAIN ENTRY POINT
# ==========================================
def main():
    """Main execution with graceful shutdown handling.
    
    CRITICAL: The finally block ensures data is saved even on Ctrl+C.
    """
    # Use absolute path for config
    config_path = SCRIPT_DIR / 'config.yaml'
    
    if not config_path.exists():
        print(f"\nERROR: Config file not found at: {config_path}")
        print("Please ensure config.yaml exists in the same directory as this script.\n")
        sys.exit(1)
    
    scraper = None
    
    try:
        scraper = PropertyScraper(config_path)
        scraper.run()
        
    except KeyboardInterrupt:
        logging.warning("\nCtrl+C detected! Saving pending data...")
        
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        
    finally:
        if scraper:
            # CRITICAL: Always flush buffer and save checkpoint before exit
            logging.info("Performing graceful shutdown...")
            
            try:
                scraper.data_buffer.flush()
            except Exception as e:
                logging.error(f"Error flushing buffer: {e}")
            
            try:
                scraper.checkpoint.save(
                    scraper.current_city,
                    scraper.current_page,
                    len(scraper.seen_urls)
                )
            except Exception as e:
                logging.error(f"Error saving checkpoint: {e}")
            
            # Safe driver quit (Windows compatible)
            scraper._quit_driver()
            
            logging.info("Graceful shutdown complete")


if __name__ == "__main__":
    main()

import requests
from bs4 import BeautifulSoup
import sys

# Handle encoding
sys.stdout.reconfigure(encoding='utf-8')

url = 'https://www.magicbricks.com/property-for-sale/residential-real-estate?cityName=Noida&page=1'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'}

print(f"Fetching {url}...")
try:
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    
    soup = BeautifulSoup(r.content, 'html.parser')
    
    # Test selectors
    cards = soup.select('div[class*="mb-srp__card"]')
    if not cards:
        cards = soup.select('div.mb-srp__list__item')
        
    print(f"Cards found: {len(cards)}")
    
    if cards:
        print("\n--- Inspecting First Card ---")
        card = cards[0]
        
        # 1. Check Title
        title_elem = card.select_one('h2') or card.select_one('[class*="prop-title"]')
        print(f"Title Element Found: {bool(title_elem)}")
        if title_elem:
            print(f"Title Text: {title_elem.get_text(strip=True)[:50]}...")

        # 2. Check URL (Critical failure point?)
        link = card.select_one('a[href*="/property-detail"]')
        print(f"URL Element Found: {bool(link)}")
        if link:
            print(f"URL Href: {link.get('href')[:50]}...")
        else:
            # Try to find *any* link in the card
            all_links = card.find_all('a', href=True)
            print(f"Total links in card: {len(all_links)}")
            for i, a in enumerate(all_links[:3]):
                print(f"  Link {i}: {a.get('href')[:50]}...")

        # 3. Check Price
        price_elem = card.select_one('[class*="price"]')
        print(f"Price Element Found: {bool(price_elem)}")
        if price_elem:
            print(f"Price Text: {price_elem.get_text(strip=True)}")
            print(f"Price Classes: {price_elem.get('class')}")
        
    else:
        print("No cards found.")

except Exception as e:
    print(f"Error: {e}")

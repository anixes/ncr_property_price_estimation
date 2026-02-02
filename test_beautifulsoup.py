"""
Test if 99acres serves full HTML or requires JavaScript rendering
"""
import requests
from bs4 import BeautifulSoup
import json

# Load your cookies
with open(r'd:\DATA SCIENCE\ncr_property_price_estimation\ncr_property_price_estimation\data\cookies.json', 'r') as f:
    cookies_list = json.load(f)

# Convert to requests format
cookies = {cookie['name']: cookie['value'] for cookie in cookies_list}

# Headers to mimic your browser exactly
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0',
}

# Test URL
url = "https://www.99acres.com/property-in-noida-ffid?page=1"

print("Testing if BeautifulSoup can get property listings...")
print(f"URL: {url}\n")

response = requests.get(url, headers=headers, cookies=cookies, timeout=30)
print(f"Status Code: {response.status_code}")
print(f"Response Size: {len(response.content)} bytes")

if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Check for CAPTCHA
    page_text = soup.get_text().lower()
    if 'captcha' in page_text or 'suspicious' in page_text:
        print("\n❌ CAPTCHA detected in response")
    else:
        print("\n✓ No CAPTCHA detected")
    
    # Try to find property cards
    cards = soup.select('div[class*="srpTuple__tupleTable"]')
    print(f"\nProperty cards found: {len(cards)}")
    
    if len(cards) > 0:
        print("\n✅ SUCCESS! BeautifulSoup can extract listings!")
        print("\nFirst card preview:")
        card = cards[0]
        title = card.select_one('a[class*="srpTuple__propertyName"]')
        price = card.select_one('[id="srp_tuple_price"]')
        print(f"  Title: {title.get_text(strip=True) if title else 'Not found'}")
        print(f"  Price: {price.get_text(strip=True) if price else 'Not found'}")
        
        # Save HTML for inspection
        with open('test_response.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("\n✓ Full HTML saved to: test_response.html")
        
    else:
        print("\n❌ No property cards found")
        print("\nPossible reasons:")
        print("  1. Page requires JavaScript rendering")
        print("  2. Different HTML structure")
        print("  3. Cookies expired")
        
        # Check if page has any content
        title = soup.select_one('title')
        print(f"\nPage title: {title.get_text() if title else 'No title'}")
        
        # Look for script tags that might load data
        scripts = soup.find_all('script')
        print(f"Script tags found: {len(scripts)}")
        
        # Save for manual inspection
        with open('test_response.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("\n✓ HTML saved to: test_response.html for inspection")
else:
    print(f"\n❌ Failed to fetch page: {response.status_code}")

print("\n" + "="*70)
print("CONCLUSION:")
print("="*70)
if len(cards) > 0:
    print("✅ BeautifulSoup approach WILL WORK!")
    print("   You can scrape without Selenium (much faster, less CAPTCHA)")
else:
    print("❌ BeautifulSoup approach WON'T WORK")
    print("   99acres requires JavaScript rendering")
    print("   Must use Selenium with better anti-detection strategies")

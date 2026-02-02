"""
Test script to inspect 99acres HTML structure and find correct selectors
"""
import requests
from bs4 import BeautifulSoup
import json

# Load cookies
with open(r'd:\DATA SCIENCE\ncr_property_price_estimation\ncr_property_price_estimation\data\cookies.json', 'r') as f:
    cookies_list = json.load(f)

# Convert to requests format
cookies = {cookie['name']: cookie['value'] for cookie in cookies_list}

# Headers to mimic browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://www.99acres.com/',
}

# Fetch first page of Noida
url = "https://www.99acres.com/property-in-noida-ffid?page=1"
print(f"Fetching: {url}")

response = requests.get(url, headers=headers, cookies=cookies)
print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find property cards
    cards = soup.select('div[class*="srpTuple__tupleTable"]')
    if not cards:
        cards = soup.select('div[class*="projectTuple__tupleTable"]')
    
    print(f"\nFound {len(cards)} property cards")
    
    if cards:
        print("\n" + "="*80)
        print("INSPECTING FIRST CARD")
        print("="*80)
        
        card = cards[0]
        
        # Print all classes in the card
        print("\nAll div classes in first card:")
        for div in card.find_all('div', limit=20):
            classes = div.get('class', [])
            if classes:
                text = div.get_text(strip=True)[:50]
                print(f"  {classes} -> {text}")
        
        print("\n" + "-"*80)
        print("All anchor tags:")
        for a in card.find_all('a'):
            classes = a.get('class', [])
            text = a.get_text(strip=True)[:50]
            print(f"  {classes} -> {text}")
        
        print("\n" + "-"*80)
        print("All td tags:")
        for td in card.find_all('td'):
            classes = td.get('class', [])
            text = td.get_text(strip=True)[:50]
            print(f"  {classes} -> {text}")
        
        print("\n" + "-"*80)
        print("Testing current selectors:")
        
        # Test current selectors
        title = card.select_one('a[class*="srpTuple__propertyName"]')
        print(f"\nTitle selector: {title.get_text(strip=True) if title else 'NOT FOUND'}")
        
        location1 = card.select_one('a[class*="srpTuple__societyName"]')
        print(f"Location selector 1 (societyName): {location1.get_text(strip=True) if location1 else 'NOT FOUND'}")
        
        location2 = card.select_one('td[class*="srpTuple__col3"]')
        print(f"Location selector 2 (col3): {location2.get_text(strip=True) if location2 else 'NOT FOUND'}")
        
        # Try alternative selectors
        print("\n" + "-"*80)
        print("Trying alternative selectors:")
        
        # Look for location-related classes
        location_keywords = ['location', 'locality', 'address', 'area', 'sector']
        for keyword in location_keywords:
            elements = card.select(f'[class*="{keyword}"]')
            if elements:
                print(f"\n  Found elements with '{keyword}':")
                for elem in elements[:3]:
                    print(f"    {elem.get('class')} -> {elem.get_text(strip=True)[:50]}")
        
        # Save first card HTML for manual inspection
        with open('first_card.html', 'w', encoding='utf-8') as f:
            f.write(str(card.prettify()))
        print("\n" + "="*80)
        print("First card HTML saved to: first_card.html")
        print("="*80)
    else:
        print("\nNo cards found! Page might be showing CAPTCHA or different structure.")
        print("\nPage title:", soup.select_one('title').get_text() if soup.select_one('title') else 'No title')
        
        # Save full page for inspection
        with open('full_page.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("Full page HTML saved to: full_page.html")
else:
    print(f"Failed to fetch page. Status: {response.status_code}")

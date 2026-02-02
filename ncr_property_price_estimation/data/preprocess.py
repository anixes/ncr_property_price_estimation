import pandas as pd
import re
import numpy as np
import os
from pathlib import Path


FILE_PATH = Path(__file__).resolve()
PROJECT_ROOT = FILE_PATH.parent.parent.parent 
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
INTERIM_DATA_DIR = PROJECT_ROOT / "data" / "interim"

# Ensure interim directory exists
os.makedirs(INTERIM_DATA_DIR, exist_ok=True)

def extract_features(input_filename, output_filename):
    input_path = RAW_DATA_DIR / input_filename
    output_path = INTERIM_DATA_DIR / output_filename
    
    print(f" Loading Raw Parquet: {input_path}")
    
    if not input_path.exists():
        print(f"Error: File not found at {input_path}")
        return

    # 1. READ PARQUET
    try:
        df = pd.read_parquet(input_path)
    except Exception as e:
        print(f"Error reading Parquet: {e}")
        return

    # Standardize column names
    df.columns = df.columns.str.lower().str.strip()
    if 'area_sqft' in df.columns and 'area' not in df.columns:
        df.rename(columns={'area_sqft': 'area'}, inplace=True)

    
    # 2. ROBUST LOCATION PARSING (Sector-First)
   
    print(" Extracting Location (Sector-First Logic)...")
    
    def parse_location(title):
        if not isinstance(title, str): return pd.Series(["Independent/Authority", None, "NCR"])
        
        # Step A: Clean the Title
        # Remove "3 BHK Flat for Sale in " to get the address part
        parts = re.split(r'\s+in\s+', title, flags=re.IGNORECASE)
        address_text = parts[-1] if len(parts) > 1 else title
        
        # Step B: Find the SECTOR first (The Anchor)
        # Matches: "Sector 70A", "Sector-15", "Sector 12"
        sector_match = re.search(r'(Sector\s?[-]?\s?\d+[A-Z]?)', address_text, re.IGNORECASE)
        
        society = "Independent/Authority"
        sector = None
        locality = address_text.split(',')[-1].strip() # Default to last word (City)

        if sector_match:
            sector = sector_match.group(1).title() # Standardize "Sector 70a" -> "Sector 70A"
            
            # Step C: Deduced Society
            # If "Godrej Woods, Sector 43", then "Godrej Woods" is before the sector.
            # We split the string using the Sector as the divider.
            pre_sector_part = address_text.split(sector_match.group(0))[0]
            
            # Clean up commas and spaces
            tokens = [t.strip() for t in pre_sector_part.split(',') if t.strip()]
            
            if tokens:
                potential_society = tokens[-1] # The thing immediately before the sector
                # Filter out generic words
                if len(potential_society) > 2 and "Flat" not in potential_society:
                    society = potential_society
        else:
            # Fallback: If no sector, try to grab the first named entity
            tokens = [t.strip() for t in address_text.split(',')]
            if len(tokens) > 1:
                society = tokens[0]

        return pd.Series([society, sector, locality])

    df[['society_name', 'sector', 'locality']] = df['title'].apply(parse_location)

   
    # 3. Sq Yard Fix
   
    print("Wm Recovering Area & Fixing Square Yards...")

    def parse_numbers(row):
        price = row.get('price')
        title = str(row.get('title', ''))
        raw_text = str(row.get('price_raw', ''))
        
        # A. Extract Rate from text
        rate = None
        rate_match = re.search(r'₹(\d+)\s*per sqft', raw_text)
        if rate_match:
            rate = float(rate_match.group(1))
            
        # B. Get Initial Area
        area = row.get('area')
        
        # C. Recovery Strategy 1: Title Search (Very Reliable)
        # Look for "1500 Sq-ft" in title if area is missing or suspicious (< 100)
        if pd.isna(area) or area < 100:
            title_area_match = re.search(r'(\d{3,5})\s*Sq\s*-?\s*ft', title, re.IGNORECASE)
            if title_area_match:
                area = float(title_area_match.group(1))

        # D. Recovery Strategy 2: Calculate from Price/Rate
        if (pd.isna(area) or area == 0) and pd.notnull(price) and rate and rate > 0:
            area = round(price / rate, 0)
            
        # E. THE SQUARE YARD FIX
        # Logic: If Rate > 1 Lakh AND Area < 500, user likely entered Yards.
        # Example: 160 Yards * 9 = 1440 Sqft.
        if pd.notnull(area) and pd.notnull(rate):
            if rate > 100000 and area < 500:
                area = area * 9
                rate = rate / 9  # Fix the rate too
        
        return pd.Series([rate, area])

    df[['price_per_sqft', 'area']] = df.apply(parse_numbers, axis=1)

   
    # 4. SAVE TO INTERIM (PARQUET)

    initial_count = len(df)
    
    # Filter: Drop rows where we still have NO price or NO area
    df = df.dropna(subset=['price', 'area'])
    
    # Optional: Clean up Society Names that are just "Sector X"
    mask = df['society_name'] == df['sector']
    df.loc[mask, 'society_name'] = 'Independent/Authority'

    final_count = len(df)
    
    print("-" * 30)
    print(f"✅ Extraction Complete.")
    print(f"   Input Rows: {initial_count}")
    print(f"   Clean Rows: {final_count}")
    print(f"   Dropped: {initial_count - final_count} (Unrecoverable)")
    print("-" * 30)
    
    df.to_parquet(output_path, index=False)
    print(f"💾 Saved Interim Parquet to: {output_path}")

if __name__ == "__main__":
    # Running from Project Root or subfolder works thanks to Path resolution
    INPUT_FILE = "magicbricks_production.parquet"
    OUTPUT_FILE = "ncr_properties_extracted.parquet"
    
    extract_features(INPUT_FILE, OUTPUT_FILE)
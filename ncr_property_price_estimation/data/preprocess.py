import pandas as pd
import re
import numpy as np
from pathlib import Path

# --- PROJECT ROOT DETECTION ---
FILE_PATH = Path(__file__).resolve()
PROJECT_ROOT = FILE_PATH.parent.parent.parent 
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
INTERIM_DATA_DIR = PROJECT_ROOT / "data" / "interim"
INTERIM_DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- REGEX PATTERNS ---
# Sector patterns (various formats)
SECTOR_PATTERNS = [
    r'Sector\s?[-]?\s?(\d+[A-Z]?)',  # "Sector 115", "Sector-43", "Sector 70A"
    r'Sec\s?[-]?\s?(\d+[A-Z]?)',     # "Sec 12", "Sec-15"
]

# Known area names that can serve as pseudo-sectors
KNOWN_AREAS = [
    r'DLF\s+Phase\s+\d+',
    r'Golf\s+Course\s+Road',
    r'Noida\s+Extension',
    r'Greater\s+Noida\s+West',
    r'Sohna\s+Road',
    r'MG\s+Road',
    r'Dwarka',
]


def extract_sector_from_url(url):
    """
    Extract sector information from MagicBricks URL.
    
    Args:
        url: Property URL
        
    Returns:
        str or None: Extracted sector (e.g., "Sector 115") or None
        
    Examples:
        "...Sector-115-in-Noida..." -> "Sector 115"
        "...Sector-43-in-Noida..." -> "Sector 43"
    """
    if not isinstance(url, str):
        return None
    
    # Pattern: Sector-115-in-Noida or Sector-43-in-Gurgaon
    match = re.search(r'Sector-(\d+[A-Z]?)-in-', url, re.IGNORECASE)
    if match:
        return f"Sector {match.group(1)}"
    
    return None


def parse_location(title, url=None):
    """
    Extract society name, sector, and locality from property title and URL.
    
    Strategy:
        1. Try extracting sector from title using regex patterns
        2. If not found, try extracting from URL
        3. If still not found, look for known area names
        4. Extract society name (text before sector)
        5. Extract locality (last token, usually city name)
    
    Args:
        title: Property title (e.g., "3 BHK in Godrej Woods, Sector 43, Noida")
        url: Property URL (optional, for fallback extraction)
        
    Returns:
        pd.Series: [society_name, sector, locality]
        
    Examples:
        "3 BHK in Sector 115, Noida" -> ["Independent/Authority", "Sector 115", "Noida"]
        "Villa in DLF Phase 2, Gurgaon" -> ["Independent/Authority", "DLF Phase 2", "Gurgaon"]
    """
    if not isinstance(title, str):
        return pd.Series(["Independent/Authority", None, "NCR"])
    
    # Step 1: Clean the title - extract address part after "in"
    parts = re.split(r'\s+in\s+', title, flags=re.IGNORECASE)
    address_text = parts[-1] if len(parts) > 1 else title
    
    # Split into tokens for processing
    tokens = [t.strip() for t in address_text.split(',') if t.strip()]
    locality = tokens[-1] if tokens else "NCR"
    
    # Initialize defaults
    society = "Independent/Authority"
    sector = None
    
    # Step 2: Try extracting sector from title using multiple patterns
    for pattern in SECTOR_PATTERNS:
        match = re.search(pattern, address_text, re.IGNORECASE)
        if match:
            sector_num = match.group(1)
            sector = f"Sector {sector_num}"
            
            # Extract society (text before sector)
            pre_sector_text = address_text.split(match.group(0))[0]
            pre_tokens = [t.strip() for t in pre_sector_text.split(',') if t.strip()]
            
            if pre_tokens:
                potential_society = pre_tokens[-1]
                # Filter out noise words
                if len(potential_society) > 2 and "Flat" not in potential_society:
                    society = potential_society
            
            break  # Found sector, stop searching
    
    # Step 3: If no sector found in title, try URL
    if not sector and url:
        sector = extract_sector_from_url(url)
    
    # Step 4: If still no sector, look for known area names
    if not sector:
        for area_pattern in KNOWN_AREAS:
            match = re.search(area_pattern, address_text, re.IGNORECASE)
            if match:
                sector = match.group(0)
                
                # If we have multiple tokens, first one might be society
                if len(tokens) >= 3:
                    society = tokens[0]
                
                break
    
    # Step 5: Last resort - use second-to-last token as sector
    # Example: ["Tata Primanti", "Sohna Road", "Gurgaon"] -> sector = "Sohna Road"
    if not sector and len(tokens) >= 2:
        potential_sector = tokens[-2]
        
        # Only use if it looks like a location (not generic words)
        if len(potential_sector) > 3 and "Flat" not in potential_sector:
            sector = potential_sector
            
            # If we have 3+ parts, first is likely society
            if len(tokens) >= 3:
                society = tokens[0]
    
    return pd.Series([society, sector, locality])


def recover_area_and_rate(row):
    """
    Recover missing area values and calculate price per sqft.
    
    Strategy:
        1. Try extracting area from title (e.g., "1500 Sq-ft")
        2. Calculate from price/rate if available
        3. Fix square yard confusion (rate > 100K and area < 500)
    
    Args:
        row: DataFrame row with price, title, price_raw, area columns
        
    Returns:
        pd.Series: [price_per_sqft, area]
    """
    price = row.get('price')
    title = str(row.get('title', ''))
    price_raw = str(row.get('price_raw', ''))
    area = row.get('area')
    
    # Extract rate from price_raw text (e.g., "₹9142 per sqft")
    rate = None
    rate_match = re.search(r'₹(\d+)\s*per sqft', price_raw)
    if rate_match:
        rate = float(rate_match.group(1))
    
    # Recovery Strategy 1: Extract from title
    # Look for patterns like "1500 Sq-ft", "2000 Sq ft"
    if pd.isna(area) or area < 100:
        title_area_match = re.search(r'(\d{3,5})\s*Sq\s*-?\s*ft', title, re.IGNORECASE)
        if title_area_match:
            area = float(title_area_match.group(1))
    
    # Recovery Strategy 2: Calculate from price and rate
    if (pd.isna(area) or area == 0) and pd.notnull(price) and rate and rate > 0:
        area = round(price / rate, 0)
    
    # Recovery Strategy 3: Fix square yard confusion
    # If rate is very high (>100K) and area is small (<500), likely entered in yards
    # Conversion: 1 square yard = 9 square feet
    if pd.notnull(area) and pd.notnull(rate):
        if rate > 100000 and area < 500:
            area = area * 9
            rate = rate / 9
    
    return pd.Series([rate, area])


def extract_features(input_filename, output_filename):
    """
    Main preprocessing pipeline: extract features from raw data.
    
    Steps:
        1. Load raw Parquet
        2. Extract location features (society, sector, locality)
        3. Recover missing area values
        4. Calculate price per sqft
        5. Save to interim Parquet
    
    Args:
        input_filename: Raw Parquet filename (in data/raw/)
        output_filename: Output Parquet filename (in data/interim/)
    """
    input_path = RAW_DATA_DIR / input_filename
    output_path = INTERIM_DATA_DIR / output_filename
    
    print(f">> Loading Raw Parquet: {input_path}")
    
    if not input_path.exists():
        print(f"ERROR: File not found at {input_path}")
        return
    
    # Load data
    try:
        df = pd.read_parquet(input_path)
    except Exception as e:
        print(f"ERROR: Reading Parquet: {e}")
        return
    
    # Standardize column names
    df.columns = df.columns.str.lower().str.strip()
    if 'area_sqft' in df.columns and 'area' not in df.columns:
        df.rename(columns={'area_sqft': 'area'}, inplace=True)
    
    # Extract location features
    print(">> Extracting Location Features (Title + URL)...")
    df[['society_name', 'sector', 'locality']] = df.apply(
        lambda row: parse_location(row['title'], row.get('url')), 
        axis=1
    )
    
    # Recover area and calculate price per sqft
    print(">> Recovering Area & Calculating Price/Sqft...")
    df[['price_per_sqft', 'area']] = df.apply(recover_area_and_rate, axis=1)
    
    # Drop rows with missing critical data
    initial_count = len(df)
    df = df.dropna(subset=['price', 'area'])
    final_count = len(df)
    
    # Clean up: If society name equals sector, reset to default
    mask = df['society_name'] == df['sector']
    df.loc[mask, 'society_name'] = 'Independent/Authority'
    
    # Statistics
    null_sectors = df['sector'].isna().sum()
    sector_from_url = df['sector'].notna().sum() - (df['sector'].notna() & df['title'].str.contains('Sector', case=False, na=False)).sum()
    
    print("-" * 60)
    print(f"COMPLETE: Preprocessing")
    print(f"   Total Rows:        {initial_count}")
    print(f"   Valid Rows:        {final_count}")
    print(f"   Dropped:           {initial_count - final_count}")
    print(f"   Null Sectors:      {null_sectors} ({null_sectors/final_count*100:.1f}%)")
    print(f"   Sectors from URL:  ~{sector_from_url}")
    print("-" * 60)
    
    # Save to interim
    df.to_parquet(output_path, index=False)
    print(f">> Saved to: {output_path}")


if __name__ == "__main__":
    extract_features("magicbricks_production.parquet", "ncr_properties_extracted.parquet")
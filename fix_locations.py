"""
Re-process existing CSV to extract locations from titles and URLs
"""
import pandas as pd
import re

# Load existing data
csv_path = r'd:\DATA SCIENCE\ncr_property_price_estimation\data\raw\99acres_NCR_ML_Final.csv'
df = pd.read_csv(csv_path)

print(f"Loaded {len(df)} listings")
print(f"Missing locations: {df['Location'].isna().sum()}")

def extract_location(row):
    """Extract location using multiple strategies"""
    title = row['Title']
    url = row['URL']
    
    # Strategy 1: Extract from title (e.g., "4 BHK Flat in Sector 128, Noida")
    if pd.notna(title):
        # Pattern: "in <location>"
        match = re.search(r'\bin\s+(.+?)(?:,\s*noida)?$', title, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            # Remove trailing comma if present
            location = location.rstrip(',').strip()
            return location
    
    # Strategy 2: Extract from URL (e.g., "sector-128-noida")
    if pd.notna(url):
        # Extract sector/area from URL
        match = re.search(r'(sector-\d+|[a-z-]+)-noida', url, re.IGNORECASE)
        if match:
            location = match.group(1).replace('-', ' ').title()
            return location
    
    return 'Unknown'

# Apply extraction
print("\nExtracting locations...")
df['Location'] = df.apply(extract_location, axis=1)

# Show results
print(f"\nAfter extraction:")
print(f"Missing locations: {(df['Location'] == 'Unknown').sum()}")
print(f"Valid locations: {(df['Location'] != 'Unknown').sum()}")

print("\nLocation distribution (top 10):")
print(df['Location'].value_counts().head(10))

# Save updated CSV
df.to_csv(csv_path, index=False)
print(f"\n✓ Updated CSV saved to: {csv_path}")

# Show sample
print("\nSample data:")
print(df[['Title', 'Location', 'Price']].head(10))

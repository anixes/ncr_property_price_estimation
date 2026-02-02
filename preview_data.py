"""Quick data preview script"""
import pandas as pd

df = pd.read_csv(r'd:\DATA SCIENCE\ncr_property_price_estimation\data\raw\99acres_NCR_ML_Final.csv')

print("=" * 70)
print("DATA PREVIEW - 99acres NCR Listings")
print("=" * 70)
print(f"\nTotal Rows: {len(df)}")
print(f"Columns ({len(df.columns)}): {list(df.columns)}")

print(f"\n{'='*70}")
print("PRICE STATISTICS (in Rupees)")
print("=" * 70)
print(f"  Min: Rs. {df['Price'].min():,.0f}")
print(f"  Max: Rs. {df['Price'].max():,.0f}")
print(f"  Mean: Rs. {df['Price'].mean():,.0f}")
print(f"  Median: Rs. {df['Price'].median():,.0f}")

print(f"\n{'='*70}")
print("BEDROOM DISTRIBUTION")
print("=" * 70)
print(df['Bedrooms'].value_counts().sort_index())

print(f"\n{'='*70}")
print("PROPERTY TYPES")
print("=" * 70)
print(df['Prop_Type'].value_counts())

print(f"\n{'='*70}")
print("SAMPLE LISTINGS (First 3)")
print("=" * 70)
print(df[['Title', 'Price', 'Bedrooms', 'Location']].head(3).to_string())

print(f"\n{'='*70}")
print("DATA QUALITY CHECK")
print("=" * 70)
print(f"Missing Values:")
print(df.isnull().sum()[df.isnull().sum() > 0])

print(f"\n{'='*70}")

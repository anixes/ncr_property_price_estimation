import pandera as pa
from pandera import Column, Check, DataFrameSchema


# =============================================================================
# PROPERTY VALIDATION SCHEMA
# =============================================================================
# Validates interim data from preprocess.py
# Rejects outliers and data quality issues before modeling

PROPERTY_SCHEMA = DataFrameSchema({
    
    # --- PRICE VALIDATION ---
    # Range: 5 Lakhs to 50 Crores (NCR luxury market)
    'price': Column(
        float,
        checks=[Check.in_range(500000, 500000000)],
        nullable=False,
        coerce=True,
    ),
    
    # --- AREA VALIDATION ---
    # Range: 100 to 10,000 sqft (catches parsing errors)
    # Rationale: 10K sqft is already a mansion, anything larger is likely an error
    'area': Column(
        float,
        checks=[Check.in_range(100, 10000)],
        nullable=False,
        coerce=True,
    ),
    
    # --- PRICE PER SQFT VALIDATION ---
    # Range: ₹1,500/sqft (Budget) to ₹50,000/sqft (Ultra Luxury)
    # Rejects calculation errors (e.g., tiny area causing huge rate)
    'price_per_sqft': Column(
        float,
        checks=[Check.in_range(1500, 50000)],
        nullable=False,  # Must exist (calculated in preprocess)
        coerce=True,
    ),
    
    # --- PHYSICAL SPECS ---
    'bedrooms': Column(
        int,
        checks=[Check.in_range(0, 15)],  # 0 for plots/studios
        nullable=False,
        coerce=True,
    ),
    
    'bathrooms': Column(
        int,
        checks=[Check.in_range(0, 15)],
        nullable=False,
        coerce=True,
    ),
    
    'balcony': Column(
        int,
        checks=[Check.in_range(0, 10)],
        nullable=False,
        coerce=True,
    ),
    
    # --- LOCATION VALIDATION ---
    # Society and locality are always extracted (fallback to defaults)
    'society_name': Column(
        str,
        checks=[Check.str_length(min_value=2)],
        nullable=False,
        coerce=True,
    ),
    
    # Sector can be null for non-sector areas (7.8% of data)
    'sector': Column(
        str,
        checks=[Check.str_length(min_value=2)],
        nullable=True,  # CRITICAL: Allow nulls for non-sector properties
        coerce=True,
    ),
    
    'locality': Column(
        str,
        checks=[Check.str_length(min_value=2)],
        nullable=False,
        coerce=True,
    ),
})


def validate_dataframe(df):
    """
    Validate dataframe against schema and separate clean vs rejected rows.
    
    Args:
        df: DataFrame to validate
        
    Returns:
        tuple: (clean_df, stats_dict)
        
    Stats Dict Keys:
        - total_rows: Input row count
        - valid_rows: Rows passing validation
        - dropped_rows: Rows rejected by schema
    """
    print(f">> Validating {len(df)} rows against schema...")
    
    try:
        # Lazy validation: runs all checks and reports all errors
        clean_df = PROPERTY_SCHEMA.validate(df, lazy=True)
        
        stats = {
            'total_rows': len(df),
            'valid_rows': len(clean_df),
            'dropped_rows': 0
        }
        
        print(">> SUCCESS: All rows passed validation")
        return clean_df, stats
    
    except pa.errors.SchemaErrors as e:
        # Identify failed rows
        failure_indices = e.failure_cases['index'].unique()
        clean_df = df.drop(index=failure_indices)
        
        stats = {
            'total_rows': len(df),
            'valid_rows': len(clean_df),
            'dropped_rows': len(failure_indices)
        }
        
        print(f">> VALIDATION: Dropped {len(failure_indices)} rows ({len(failure_indices)/len(df)*100:.1f}%)")
        
        # Group failures by column
        print("\n--- REJECTION REASONS ---")
        failures = e.failure_cases
        for col in failures['column'].unique():
            col_failures = failures[failures['column'] == col]
            count = len(col_failures)
            example = col_failures['failure_case'].iloc[0]
            print(f"  {col}: {count} failures (e.g., {example})")
        print("-" * 60)
        
        return clean_df, stats


if __name__ == "__main__":
    """Test validation on interim data and save to processed."""
    import pandas as pd
    from pathlib import Path
    
    # Paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
    PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    input_file = INTERIM_DIR / "ncr_properties_extracted.parquet"
    output_file = PROCESSED_DIR / "ncr_properties_cleaned.parquet"
    
    print("=" * 60)
    print("SCHEMA VALIDATION TEST")
    print("=" * 60)
    
    try:
        # Load interim data
        df = pd.read_parquet(input_file)
        print(f">> Loaded {len(df)} rows from interim")
        
        # Validate
        clean_df, stats = validate_dataframe(df)
        
        # Save processed data
        clean_df.to_parquet(output_file, index=False)
        
        print("\n" + "=" * 60)
        print("FINAL STATS")
        print("=" * 60)
        print(f"  Input:    {stats['total_rows']:,} rows")
        print(f"  Valid:    {stats['valid_rows']:,} rows")
        print(f"  Dropped:  {stats['dropped_rows']:,} rows ({stats['dropped_rows']/stats['total_rows']*100:.1f}%)")
        print("=" * 60)
        print(f"\n>> Saved clean data to: {output_file}")
        
    except FileNotFoundError:
        print(f"ERROR: Could not find {input_file}")
        print("Run preprocess.py first to generate interim data")

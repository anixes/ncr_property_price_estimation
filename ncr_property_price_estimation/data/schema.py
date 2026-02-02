"""
Simple Pandera Schema for Property Data Validation

Validates:
- Price: 5 lakh to 20 crore
- Area: 200 to 20,000 sqft (caps extremes to prevent parsing glitches)
- Bedrooms: 0 to 10 (0 for studios)
- Bathrooms: 0 to 10 (caps to prevent int8 overflow)
- Balcony: 0 to 5 (caps to prevent int8 overflow)
"""

import pandera as pa
from pandera import Column, Check, DataFrameSchema

# Simple validation schema - elegance over completeness
PROPERTY_SCHEMA = DataFrameSchema({
    'price': Column(
        int,
        checks=[
            Check.in_range(500000, 200000000, include_min=True, include_max=True),
        ],
        nullable=False,
        coerce=True,
    ),
    'area_sqft': Column(
        float,
        checks=[
            Check.in_range(200, 20000, include_min=True, include_max=True),  # Cap extremes
        ],
        nullable=True,  # Some listings may not have area
        coerce=True,
    ),
    'bedrooms': Column(
        int,
        checks=[
            Check.in_range(0, 10, include_min=True, include_max=True),  # 0 for studios
        ],
        nullable=False,
        coerce=True,
    ),
    'bathrooms': Column(
        int,
        checks=[
            Check.in_range(0, 10, include_min=True, include_max=True),  # Cap to prevent int8 overflow
        ],
        nullable=False,
        coerce=True,
    ),
    'balcony': Column(
        int,
        checks=[
            Check.in_range(0, 5, include_min=True, include_max=True),  # Cap to prevent int8 overflow
        ],
        nullable=False,
        coerce=True,
    ),
})


def validate_dataframe(df):
    """Validate dataframe and return valid rows + stats.
    
    Returns:
        tuple: (validated_df, stats_dict)
    """
    try:
        validated_df = PROPERTY_SCHEMA.validate(df, lazy=True)
        stats = {
            'total_rows': len(df),
            'valid_rows': len(validated_df),
            'rejected_rows': 0,
        }
        return validated_df, stats
        
    except pa.errors.SchemaErrors as e:
        # Get valid rows (exclude failures)
        failure_indices = set(e.failure_cases['index'].unique())
        valid_mask = ~df.index.isin(failure_indices)
        validated_df = df[valid_mask].copy()
        
        stats = {
            'total_rows': len(df),
            'valid_rows': len(validated_df),
            'rejected_rows': len(failure_indices),
        }
        
        # Log rejection summary
        print(f"\nWARNING: Validation Rejected {len(failure_indices)} rows:")
        for column in e.failure_cases['column'].unique():
            count = len(e.failure_cases[e.failure_cases['column'] == column])
            print(f"   - {column}: {count} failures")
        
        return validated_df, stats

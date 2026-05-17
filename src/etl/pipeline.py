"""
Production ETL Pipeline — Dubai Real Estate Transactions
=========================================================
This pipeline processes the full DLD Transactions CSV and loads
it into a DuckDB database for the AI Agent to query.

Architecture:
    STEP 1: LOAD        → Read raw CSV with only needed columns
    STEP 2: STANDARDIZE → Clean strings, cast dates, fix booleans
    STEP 3: CLEAN       → Drop noise columns, impute prices, fill gaps
    STEP 4: FEATURES    → Room extraction, usage flags, time features
    STEP 5: QUALITY     → Outlier flagging, market-clean filter
    STEP 6: EXPORT      → Save to DuckDB

Every transformation here was verified during EDA on a 100k sample
and validated against the full 1M+ row dataset.
"""

import pandas as pd
import re
import duckdb
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================

RAW_FILE = Path("data/raw/Transactions.csv")
DB_FILE = Path(os.getenv("DB_PATH", "data/processed/transactions.duckdb"))
TABLE_NAME = "transactions"

# Mapping raw DLD column names → professional, intuitive names
COLUMN_MAPPING = {
    # Transaction context
    "transaction_id": "transaction_id",
    "trans_group_en": "transaction_category",     # Sales, Mortgages, Gifts
    "procedure_name_en": "transaction_type",      # Specific sub-type (Delayed Sale, etc.)
    "instance_date": "transaction_date",

    # Property identity
    "property_type_en": "property_type",          # Unit, Villa, Land, Building
    "property_usage_en": "usage_type",            # Residential, Commercial, etc.
    "reg_type_en": "registration_type",           # Existing or Off-Plan

    # Location
    "area_name_en": "community",                  # The neighborhood (JVC, Marina, etc.)
    "nearest_landmark_en": "nearest_landmark",    # Proximity to landmarks
    "nearest_metro_en": "nearest_metro",          # Proximity to metro
    "nearest_mall_en": "nearest_mall",            # Proximity to malls

    # Property specs
    "rooms_en": "room_config",                    # Studio, 1 B/R, 2 B/R, etc.
    "has_parking": "has_parking",
    "procedure_area": "area_sqm",

    # Financials (Sales)
    "actual_worth": "price_aed",
    "meter_sale_price": "price_per_sqm",

    # Financials (Rent) — kept for rental queries
    "rent_value": "rent_aed",
    "meter_rent_price": "rent_per_sqm",
}

# Columns we decided to drop during EDA (noise/redundancy)
# property_subtype → redundant with property_type
# building_name   → too granular, 31% missing
# master_project  → too granular, 37% missing
# All Arabic columns, party columns, and internal IDs are excluded
# by simply not including them in COLUMN_MAPPING above.


# Master Data Mapping (DLD Official -> Commercial Popular)
# Bridges the gap between government zoning and popular market search names.
COMMUNITY_MAPPING = {
    'marsa dubai': 'dubai marina',
    'al thanyah fifth': 'jumeirah lake towers (jlt)',
    'al barsha south fourth': 'jumeirah village circle (jvc)',
    'burj khalifa': 'downtown dubai',
    'al warsan first': 'international city',
    'al hebiah fourth': 'jumeirah village circle (jvc)',
    'al thanyah third': 'the greens & views',
    'al thanayah fourth': 'the greens & views',
    'wadi al safa 5': 'dubailand',
    'nadd hessa': 'dubai silicon oasis (dso)',
    'hadaeq sheikh mohammed bin rashid': 'mohammed bin rashid city',
    'me\'aisem first': 'jumeirah village triangle (jvt)',
    'wadi al safa 6': 'liwan',
    'al hebiah fifth': 'damac hills',
    'al merkadh': 'meydan',
    'al hebiah third': 'damac hills',
    'al yelayiss 2': 'al furjan',
    'al khairan first': 'sobha hartland',
    'al hebiah first': 'motor city',
    'al barsha south fifth': 'jumeirah village circle (jvc)',
    'al barshaa south third': 'arjan',
    'wadi al safa 2': 'the villa',
    'wadi al safa 7': 'falcon city of wonders',
    'madinat al mataar': 'dubai south',
    'dubai investment park first': 'dubai investment park (dip)',
    'al yelayiss 1': 'al furjan',
    'wadi al safa 3': 'arabian ranches',
    'al thanyah first': 'dubai marina',
    'nad al shiba first': 'meydan',
    'al yufrah 2': 'damac hills 2',
    'al barshaa south second': 'arjan',
    'dubai investment park second': 'dubai investment park (dip)',
    'al yufrah 3': 'damac hills 2',
    'al jadaf': 'al jaddaf',
    'al wasl': 'city walk'
}


# ============================================================
# STEP 1: LOAD
# ============================================================
def load_raw_data(file_path: Path) -> pd.DataFrame:
    """Load the raw CSV, selecting only the columns we need."""
    print("STEP 1: Loading raw data...")

    df = pd.read_csv(
        file_path,
        encoding="latin-1",
        usecols=list(COLUMN_MAPPING.keys()),
        low_memory=False,
    )
    df = df.rename(columns=COLUMN_MAPPING)

    print(f"  ✓ Loaded {len(df):,} rows, {len(df.columns)} columns")
    return df


# ============================================================
# STEP 2: STANDARDIZE
# ============================================================
def standardize(df: pd.DataFrame) -> pd.DataFrame:
    """Clean strings, cast dates, fix booleans, extract IDs, and map communities."""
    print("STEP 2: Standardizing...")

    # 2a. String cleaning — lowercase + strip whitespace
    # Handles both 'object' and 'string' dtypes
    text_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in text_cols:
        df[col] = df[col].str.strip().str.lower()

    # 2b. Master Entity Mapping (DLD name -> Commercial popular name)
    if "community" in df.columns:
        df["community"] = df["community"].replace(COMMUNITY_MAPPING)
        print(f"  ✓ Standardized community names using master dictionary ({len(COMMUNITY_MAPPING)} mappings)")

    # 2c. Date casting
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")

    # 2d. Boolean fix for parking
    # Raw data has mixed types; we normalize to True/False
    df["has_parking"] = df["has_parking"].map(
        {"yes": True, "no": False, "true": True, "false": False, True: True, False: False}
    )

    # 2e. Transaction ID — extract numeric portion
    # Raw format: "xxx-xxx-xxx-12345" → "12345"
    if "transaction_id" in df.columns:
        df["transaction_id"] = df["transaction_id"].str.split("-").str[-1]

    print(f"  ✓ Standardized {len(text_cols)} text columns")
    print(f"  ✓ Date range: {df['transaction_date'].min()} → {df['transaction_date'].max()}")
    return df


# ============================================================
# STEP 3: CLEAN
# ============================================================
def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Impute missing values, fill location gaps."""
    print("STEP 3: Cleaning...")
    rows_before = len(df)

    # 3a. Price imputation — calculate from area * price_per_sqm if missing
    mask = (
        df["price_aed"].isnull()
        & df["area_sqm"].notnull()
        & df["price_per_sqm"].notnull()
    )
    df.loc[mask, "price_aed"] = df.loc[mask, "area_sqm"] * df.loc[mask, "price_per_sqm"]
    print(f"  ✓ Imputed {mask.sum():,} missing prices via calculation")

    # 3b. Fill location gaps with "unknown"
    # These are properties in areas without nearby metro/mall/landmarks
    location_cols = ["nearest_landmark", "nearest_metro", "nearest_mall"]
    df[location_cols] = df[location_cols].fillna("unknown")

    # 3c. Drop rows missing critical identity columns
    # Without date, category, or price, the row is useless for analytics
    df = df.dropna(subset=["transaction_date", "transaction_category", "price_aed"])

    print(f"  ✓ Dropped {rows_before - len(df):,} rows missing critical fields")
    print(f"  ✓ Remaining: {len(df):,} rows")
    return df


# ============================================================
# STEP 4: FEATURE ENGINEERING
# ============================================================
def extract_rooms(row) -> int:
    """
    Extract a numeric room count from the room_config text.

    Returns:
        0     → Studio
        1-9   → Number of bedrooms
        -1    → Commercial/Unknown (Shop, Office, Store, Gym, or missing Villa/Unit)
        -2    → Not Applicable (Land, Building — rooms don't exist)
    """
    room_text = str(row["room_config"]).lower().strip()
    prop_type = str(row["property_type"]).lower().strip()

    # Handle specific labels first
    if "studio" in room_text:
        return 0
    if "penthouse" in room_text:
        return 5
    if "single room" in room_text:
        return 1
    if any(x in room_text for x in ["shop", "office", "store", "gym"]):
        return -1

    # Handle the standard "X B/R" pattern
    digit = re.findall(r"\d+", room_text)
    if digit:
        return int(digit[0])

    # Handle NULLs based on property type
    if room_text == "nan":
        if any(x in prop_type for x in ["land", "building"]):
            return -2  # Not Applicable
        return -1      # Unknown (Villa/Unit without recorded rooms)

    return -1  # Catch-all


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create derived columns for analytics."""
    print("STEP 4: Building features...")

    # 4a. Room count extraction (verified against full dataset: 17 unique values)
    df["room_count"] = df.apply(extract_rooms, axis=1)

    # 4b. Usage type flags — handles hybrid categories like "residential / commercial"
    df["is_residential"] = df["usage_type"].str.contains("residential", na=False, case=False)
    df["is_commercial"] = df["usage_type"].str.contains("commercial", na=False, case=False)

    # 4c. Time features — enables trend analysis by year/quarter
    df["year"] = df["transaction_date"].dt.year
    df["month"] = df["transaction_date"].dt.month
    df["quarter"] = df["transaction_date"].dt.quarter

    print(f"  ✓ Room count distribution: {df['room_count'].value_counts().to_dict()}")
    print(f"  ✓ Years present: {sorted(df['year'].unique())}")
    return df


# ============================================================
# STEP 5: DATA QUALITY
# ============================================================
def apply_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Flag outliers without deleting them (Medallion Architecture principle)."""
    print("STEP 5: Applying quality flags...")

    # 5a. Price outliers — anything under 100k AED is likely a gift or token transfer
    df["is_outlier_price"] = df["price_aed"] < 100_000

    # 5b. Area outliers — nothing is smaller than 10sqm or larger than 10,000sqm
    df["is_outlier_area"] = (df["area_sqm"] < 10) | (df["area_sqm"] > 10_000)

    # 5c. Master filter — "Is this row safe for market analytics?"
    df["is_market_clean"] = (~df["is_outlier_price"]) & (~df["is_outlier_area"])

    clean_count = df["is_market_clean"].sum()
    outlier_count = len(df) - clean_count
    print(f"  ✓ Market-clean rows: {clean_count:,}")
    print(f"  ✓ Outliers flagged:  {outlier_count:,} ({outlier_count/len(df)*100:.2f}%)")
    return df


# ============================================================
# STEP 6: EXPORT TO DUCKDB
# ============================================================
def export_to_duckdb(df: pd.DataFrame, db_path: Path, table_name: str):
    """Save the cleaned DataFrame to a DuckDB database file."""
    print("STEP 6: Exporting to DuckDB...")

    # Ensure the output directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Connect and write
    con = duckdb.connect(str(db_path))
    con.execute(f"DROP TABLE IF EXISTS {table_name}")
    con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")

    # Verify
    row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    col_count = con.execute(f"SELECT COUNT(*) FROM information_schema.columns WHERE table_name = '{table_name}'").fetchone()[0]
    con.close()

    print(f"  ✓ Saved to: {db_path}")
    print(f"  ✓ Table '{table_name}': {row_count:,} rows, {col_count} columns")


# ============================================================
# FINAL REPORT
# ============================================================
def print_report(df: pd.DataFrame):
    """Print the final data quality sign-off report."""
    print("\n" + "=" * 50)
    print("         PIPELINE COMPLETE — QUALITY REPORT")
    print("=" * 50)

    clean_df = df[df["is_market_clean"]]

    report = {
        "Total Transactions": f"{len(df):,}",
        "Date Range": f"{df['transaction_date'].min().date()} → {df['transaction_date'].max().date()}",
        "Unique Communities": f"{df['community'].nunique()}",
        "Market-Clean Rows": f"{len(clean_df):,} ({len(clean_df)/len(df)*100:.1f}%)",
        "Outliers Flagged": f"{len(df) - len(clean_df):,}",
        "Null Prices": f"{df['price_aed'].isnull().sum()}",
        "Unknown Locations": f"{(df['nearest_metro'] == 'unknown').sum():,}",
    }

    for metric, value in report.items():
        print(f"  {metric:<25} {value}")

    # Variance reduction check (our EDA benchmark was 94%)
    old_std = df["price_per_sqm"].std()
    new_std = clean_df["price_per_sqm"].std()
    reduction = ((old_std - new_std) / old_std * 100)
    print(f"\n  Price/SQM Variance Reduction: {reduction:.2f}%")

    print("=" * 50)


# ============================================================
# MAIN EXECUTION
# ============================================================
if __name__ == "__main__":
    print("\n Dubai Real Estate ETL Pipeline Starting...\n")

    # Execute the pipeline
    df = load_raw_data(RAW_FILE)
    df = standardize(df)
    df = clean(df)
    df = build_features(df)
    df = apply_quality_flags(df)

    # Export and report
    export_to_duckdb(df, DB_FILE, TABLE_NAME)
    print_report(df)

    print("\n✅ Pipeline complete. Data is ready for the AI Agent.")

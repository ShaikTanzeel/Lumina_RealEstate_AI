import pandas as pd
import numpy as np

# Configuration
FILE_PATH = "data/raw/Transactions.csv"
SAMPLE_SIZE = 100000

# Mapping original names to cleaner, intuitive names
COLUMN_MAPPING = {
    "trans_group_en": "transaction_category",
    "procedure_name_en": "transaction_type",
    "instance_date": "transaction_date",
    "property_type_en": "property_type",
    "property_sub_type_en": "property_subtype",
    "property_usage_en": "usage_type",
    "reg_type_en": "registration_type",
    "area_name_en": "community",
    "building_name_en": "building_name",
    "master_project_en": "master_project",
    "nearest_metro_en": "nearest_metro",
    "nearest_mall_en": "nearest_mall",
    "rooms_en": "room_config",
    "has_parking": "has_parking",
    "procedure_area": "area_sqm",
    "actual_worth": "price_aed",
    "meter_sale_price": "price_per_sqm",
    "rent_value": "rent_aed",
    "meter_rent_price": "rent_per_sqm",
}

print("--- Professional EDA Started ---")
try:
    # 1. LOAD & RENAME
    # Only loading columns we care about to save memory
    df = pd.read_csv(
        FILE_PATH, 
        encoding="latin-1", 
        nrows=SAMPLE_SIZE, 
        usecols=list(COLUMN_MAPPING.keys()),
        low_memory=False
    )
    df = df.rename(columns=COLUMN_MAPPING)
    print(f"Loaded and renamed sample of {len(df):,} rows.")
except Exception as e:
    print(f"Error: {e}")
    exit()

# 2. VALIDATION (Using new names)
# Formula: price_aed / area_sqm = price_per_sqm
df['calc_price_per_sqm'] = df['price_aed'] / df['area_sqm']

# Check how many match (within a 1% tolerance)
matches = np.isclose(df['calc_price_per_sqm'], df['price_per_sqm'], rtol=1e-2).sum()
total_with_area = df[df['area_sqm'] > 0].shape[0]

print(f"\n[Validation] Area Consistency:")
print(f"Rows where (Price / Area) matches Price per SQM: {matches:,} ({matches/total_with_area:.1%})")

# 3. FINANCIAL ANALYSIS
print("\n[Financials] Median Values (AED):")
print(f"Median Price:      {df['price_aed'].median():,.0f}")
print(f"Median Rent:       {df['rent_aed'].median():,.0f}")
print(f"Median Price/SQM:  {df['price_per_sqm'].median():,.0f}")

# 4. CATEGORICAL DISTRIBUTION
print("\n[Categories] Top 5 Communities:")
print(df['community'].value_counts().head(5))

# 5. DATA QUALITY CHECK
print("\n[Quality] Missing Values (%):")
print((df.isnull().sum() / len(df) * 100).sort_values(ascending=False).head(5))

print("\n--- EDA Complete ---")

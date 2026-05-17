import pandas as pd
import duckdb

# Load the raw data
df = pd.read_csv('data/raw/Rentals.csv')

# --- STEP 1 (The rest of your code follows below) ---


# --- STEP 1: SELECT & RENAME ---
# We only keep the columns that add value and rename them for consistency
COLUMN_MAPPING = {
    "Rent": "rent_aed",
    "Beds": "room_count",
    "Baths": "bath_count",
    "Type": "property_type",
    "Area_in_sqft": "area_sqft",
    "Rent_per_sqft": "rent_per_sqft",
    "Frequency": "rent_frequency",
    "Furnishing": "furnishing_status",
    "Posted_date": "posted_date",
    "Location": "raw_location",
    "City": "city"
}

# Keep only the mapped columns and rename them
df = df[list(COLUMN_MAPPING.keys())].rename(columns=COLUMN_MAPPING)

print("\n[DONE] Step 1 Complete: Columns Standardized")
print(df.columns.tolist())

# --- STEP 2: SCOPING & NORMALIZATION ---
# 2a. Filter only for Dubai (to match our DLD data)
df = df[df['city'].str.lower() == 'dubai'].copy()

# 2b. String Normalization (Lower & Strip)
# This handles the 'text' columns automatically
text_cols = ['property_type', 'rent_frequency', 'furnishing_status', 'raw_location', 'city']
for col in text_cols:
    df[col] = df[col].str.lower().str.strip()
print(f"\n[DONE] Step 2 Complete: Filtered to Dubai ({len(df):,} rows remaining)")
print(df[['city', 'raw_location']].head())


print("\n--- RENT FREQUENCY AUDIT ---")
print(df['rent_frequency'].value_counts())


# --- STEP 4: AREA CONVERSION (Sqft -> Sqm) ---

# Conversion factor
SQFT_TO_SQM = 10.7639

df['area_sqm'] = df['area_sqft'] / SQFT_TO_SQM

# Also update the rent_per_sqm for accurate ROI later
df['rent_per_sqm'] = df['rent_aed'] / df['area_sqm']

print("\n[DONE] Step 4 Complete: Area converted to Square Meters")
print(df[['area_sqft', 'area_sqm', 'rent_per_sqm']].head())

# --- STEP 5: THE BRIDGE (RENAMING) ---
# Since the data is already clean, we just rename it to match our DLD table
df = df.rename(columns={'raw_location': 'community'})

print("\n[DONE] Step 5 Complete: Community column ready")
print(df['community'].value_counts().head(10))



#If this new dataset uses text like "1 Bedroom" or "Studio", our AI Agent will get confused.
print("\n--- ROOM COUNT VALUES ---")
print(df['room_count'].value_counts())


print("\n--- PROPERTY TYPES ---")
print(df['property_type'].value_counts())

# --- STEP 6: CATEGORICAL ALIGNMENT ---

# In this dataset, everything we see is residential
df['is_residential'] = True
df['is_commercial'] = False

# One last thing: In our Sales data, we had a 'year' column.
# Let's extract the year from the 'posted_date' so we can compare trends!
df['posted_date'] = pd.to_datetime(df['posted_date'], errors='coerce')
df['year'] = df['posted_date'].dt.year

print("\n[DONE] Step 6 Complete: Categorical flags and Year extracted")
print(df[['property_type', 'is_residential', 'year']].head())



# --- SCHEMA AUDIT: TRANSACTIONS vs RENTALS ---
print("\n--- [TABLE] SALES TABLE (Transactions) ---")
with duckdb.connect('data/processed/transactions.duckdb') as con:
    # Use DESCRIBE to see the columns and their types
    print(con.execute("DESCRIBE transactions").df()[['column_name', 'column_type']])
print("\n--- [TABLE] RENTAL TABLE (Current Dataframe) ---")
# Check our current dataframe types
print(df.dtypes)

# --- STEP 7: STATISTICAL AUDIT ---

print("\n--- RENTAL STATISTICS ---")
# This will show us the min, max, and average for Rent and Area
print(df[['rent_aed', 'area_sqm', 'room_count']].describe())


# --- STEP 7: QUALITY FILTERING (THE MASK) ---

# Define what a "Typical" market listing looks like
mask_rent = (df['rent_aed'] >= 10000) & (df['rent_aed'] <= 10000000)
mask_area = (df['area_sqm'] >= 15) & (df['area_sqm'] <= 5000)

# Apply the master flag
df['is_market_clean'] = mask_rent & mask_area

clean_count = df['is_market_clean'].sum()
print(f"\n[DONE] Step 7 Complete: {clean_count:,} typical listings flagged as 'Market Clean'.")
print(f"[INFO] Removed {len(df) - clean_count:,} outliers.")


# --- FINAL QA EXPORT ---

qa_sample_path = 'eda/rentals_qa_3000.xlsx'
# We'll take a random sample of 3,000 rows to see a good variety
df.sample(3000).to_excel(qa_sample_path, index=False)

print(f"\n[DONE] Final QA Sample created: {qa_sample_path}")
print("Please review this file. Look specifically at the 'community' and 'rent_aed' columns.")


# --- STEP 8: THE FINAL EXPORT ---

# 1. Establish the path to our existing database
db_path = 'data/processed/transactions.duckdb'

# 2. Connect and save as a new table called 'rentals'
with duckdb.connect(db_path) as con:
    # Overwrite if it already exists (to prevent duplicates)
    con.execute("DROP TABLE IF EXISTS rentals")
    con.execute("CREATE TABLE rentals AS SELECT * FROM df")
    
    # 3. Final Sign-off
    count = con.execute("SELECT COUNT(*) FROM rentals").fetchone()[0]
    print(f"\n[LAUNCH] MISSION ACCOMPLISHED!")
    print(f"Successfully exported {count:,} clean rental listings to {db_path}")
    print("Table 'rentals' is now available for the AI Agent to query.")

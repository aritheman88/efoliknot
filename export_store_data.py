"""
Export store price comparison data from PostgreSQL to CSV
Uses pre-exported average prices CSV file (no heavy database queries!)

IMPORTANT: Export popular_items_avg_prices view to CSV first:
  Location: C:/Users/ariel/MyPythonScripts/efoliknot/data/popular_items_avg_prices.csv
"""
import psycopg2
import pandas as pd
from pathlib import Path
from datetime import datetime
import warnings
from config import pg_config

# Suppress ALL warnings
warnings.filterwarnings('ignore')

def timestamp():
    """Return current timestamp string"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Constants
UPLOAD_DATE = '2025-11-02'
OUTPUT_DIR = Path(r'C:\Users\ariel\MyPythonScripts\efoliknot\data')

def get_average_prices_from_csv():
    """Load average prices from CSV file (no database query needed!)"""
    print(f"[{timestamp()}] Step 1: Loading average prices from CSV file...")

    start_time = datetime.now()

    # Read from the exported CSV file
    csv_path = OUTPUT_DIR / "popular_items_avg_prices.csv"

    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {csv_path}\n"
            f"Please export the popular_items_avg_prices view to this location first."
        )

    df = pd.read_csv(csv_path)

    # Keep only itemcode and average_price columns
    df = df[['itemcode', 'average_price']]

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"[{timestamp()}]   ✓ Loaded {len(df):,} average prices in {elapsed:.1f} seconds")

    return df

def get_all_stores(conn):
    """Get all store metadata"""
    print(f"[{timestamp()}] Step 2: Loading all store metadata...")

    start_time = datetime.now()
    query = """
    SELECT 
        store_code,
        chainname,
        subchainname,
        storename,
        storeid,
        address,
        city,
        zipcode,
        latitude,
        longitude
    FROM all_stores
    ORDER BY store_code
    """

    df = pd.read_sql_query(query, conn)
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"[{timestamp()}]   ✓ Loaded {len(df):,} stores in {elapsed:.1f} seconds")
    return df

def get_stores_with_prices(conn, upload_date):
    """Get list of stores that have prices on the given date"""
    print(f"[{timestamp()}] Step 3: Getting stores with prices on {upload_date}...")

    start_time = datetime.now()
    query = """
    SELECT DISTINCT store_code 
    FROM allprices 
    WHERE upload_date = %s
    """

    df = pd.read_sql_query(query, conn, params=(upload_date,))
    store_codes = df['store_code'].tolist()

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"[{timestamp()}]   ✓ Found {len(store_codes):,} stores with prices in {elapsed:.1f} seconds")
    return store_codes

def get_store_prices(conn, store_code, upload_date):
    """Get all prices for a single store - simple query, no joins"""
    query = """
    SELECT itemcode, itemprice
    FROM allprices
    WHERE upload_date = %s
      AND store_code = %s
      AND itemprice > 0
      AND itemprice IS NOT NULL
    """

    df = pd.read_sql_query(query, conn, params=(upload_date, store_code))
    return df

def calculate_store_rank(store_prices_df, avg_prices_df):
    """Calculate average price difference using pandas merge (in memory)"""

    # Merge store prices with average prices (pandas join - FAST!)
    merged_df = store_prices_df.merge(
        avg_prices_df,
        on='itemcode',
        how='inner'  # Only keep items that have average prices
    )

    if len(merged_df) == 0:
        return None, 0

    # Calculate price difference percentage
    merged_df['price_diff_percent'] = (
        (merged_df['itemprice'] - merged_df['average_price']) /
        merged_df['average_price'] * 100
    )

    # Get average and count
    avg_price_diff = merged_df['price_diff_percent'].mean()
    popular_item_count = len(merged_df)

    return avg_price_diff, popular_item_count

def export_store_comparisons():
    """Main function - simple and safe"""

    script_start = datetime.now()
    print("="*70)
    print(f"[{timestamp()}] Starting export for {UPLOAD_DATE}")
    print("="*70)
    print()

    try:
        # Connect to database
        print(f"[{timestamp()}] Connecting to PostgreSQL database...")
        conn = psycopg2.connect(**pg_config)
        print(f"[{timestamp()}]   ✓ Connected successfully!\n")

        # Step 1: Load average prices from CSV file (no database query!)
        avg_prices_df = get_average_prices_from_csv()

        # Step 2: Get all store metadata
        all_stores_df = get_all_stores(conn)

        # Step 3: Get stores that have prices on this date
        stores_with_prices = get_stores_with_prices(conn, UPLOAD_DATE)

        # Filter to only stores with prices
        stores_df = all_stores_df[all_stores_df['store_code'].isin(stores_with_prices)].copy()

        print()
        print(f"[{timestamp()}] Step 4: Processing {len(stores_df):,} stores...")
        print("-"*70)

        # Initialize columns for results
        stores_df['average_price_diff'] = None
        stores_df['popular_item_count'] = 0
        stores_df['total_items'] = 0

        # Process each store
        store_start_time = datetime.now()
        for idx, row in stores_df.iterrows():
            store_code = row['store_code']
            store_name = row['storename']

            # Get prices for this store (simple query!)
            store_prices_df = get_store_prices(conn, store_code, UPLOAD_DATE)
            total_items = len(store_prices_df)

            # Calculate rank in pandas (merge in memory - FAST!)
            avg_diff, matched_items = calculate_store_rank(store_prices_df, avg_prices_df)

            # Store results
            stores_df.at[idx, 'average_price_diff'] = avg_diff
            stores_df.at[idx, 'popular_item_count'] = matched_items
            stores_df.at[idx, 'total_items'] = total_items

            # Print progress with details
            if avg_diff is not None:
                print(f"[{timestamp()}]   {idx+1}/{len(stores_df):,} {store_code} ({store_name}): "
                      f"{matched_items:,}/{total_items:,} items matched | "
                      f"Price diff: {avg_diff:+.2f}%")
            else:
                print(f"[{timestamp()}]   {idx+1}/{len(stores_df):,} {store_code} ({store_name}): "
                      f"0/{total_items:,} items matched | No data")

            # Progress summary every 100 stores
            if (idx + 1) % 100 == 0:
                elapsed = (datetime.now() - store_start_time).total_seconds()
                avg_time_per_store = elapsed / (idx + 1)
                remaining_stores = len(stores_df) - (idx + 1)
                estimated_remaining = (remaining_stores * avg_time_per_store) / 60  # in minutes
                print(f"[{timestamp()}]     ⏱ Progress: {idx+1}/{len(stores_df):,} complete | "
                      f"Avg {avg_time_per_store:.1f}s/store | Est. {estimated_remaining:.1f} min remaining")
                print()

        # Close connection
        conn.close()

        total_processing_time = (datetime.now() - store_start_time).total_seconds()
        print()
        print(f"[{timestamp()}]   ✓ Completed all stores in {total_processing_time/60:.1f} minutes")

        # Remove stores with no popular items
        final_df = stores_df[stores_df['average_price_diff'].notna()].copy()

        # Create output filename with date
        output_filename = f"store_price_comp_{UPLOAD_DATE}.csv"
        output_path = OUTPUT_DIR / output_filename

        # Ensure output directory exists
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Export to CSV
        print(f"[{timestamp()}] Writing CSV file...")
        final_df.to_csv(output_path, index=False, encoding='utf-8-sig')

        script_elapsed = (datetime.now() - script_start).total_seconds()

        print()
        print("="*70)
        print(f"[{timestamp()}] ✓ Export completed successfully!")
        print("="*70)
        print(f"\nOutput file: {output_path}")
        print(f"\nSummary:")
        print(f"  - Total stores processed: {len(stores_df):,}")
        print(f"  - Stores with popular items: {len(final_df):,}")
        print(f"  - Unique chains: {final_df['chainname'].nunique()}")
        print(f"  - Popular items tracked: {len(avg_prices_df):,}")
        print(f"  - Average price diff range: {final_df['average_price_diff'].min():.2f}% to {final_df['average_price_diff'].max():.2f}%")
        print(f"\nTotal runtime: {script_elapsed/60:.1f} minutes")

    except Exception as e:
        print(f"\n[{timestamp()}] ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    export_store_comparisons()
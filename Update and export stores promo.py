#!/usr/bin/env python3
"""
Update Store Effective Price Comparisons and Export to CSV
==========================================================

Mirrors update_and_export_stores.py but uses effective prices (regular or promo,
whichever is lower) for the subchains map at efoliknot.net/subchains.

Only includes chains that have promo data:
    אושר עד, ויקטורי, טיב טעם, יוחננוף, מחסני השוק, קרפור, רמי לוי, שופרסל

Requires: popular_items_avg_effective_prices materialized view to exist.
Run update_popular_items_effective_view.py first.

Output:
    subchains/data/store_effective_comparisons_YYYY-MM-DD.csv  (dated archive)
    subchains/data/store_effective_comparisons.csv             (for map)

Usage:
    python update_and_export_stores_promo.py  (always prompts interactively)

Author: efoliknot team
Last Updated: 2026-05-05
"""

import psycopg2
import pandas as pd
from pathlib import Path
from datetime import datetime
import warnings
from config import pg_config

warnings.filterwarnings('ignore')

# Chains with promo data — only these are included
PROMO_CHAINS = ['אושר עד', 'ויקטורי', 'טיב טעם', 'יוחננוף', 'מחסני השוק', 'קרפור', 'רמי לוי', 'שופרסל']

# Subchains/cities to exclude (same as main map)
EXCLUDED_SUBCHAINS = ['Be', 'אונליין']
EXCLUDED_CITIES = ['unknown']

# Output directory — inside the subchains frontend folder
OUTPUT_DIR = Path(__file__).parent / 'subchains' / 'data'


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def validate_date(date_string):
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return date_string
    except ValueError:
        raise ValueError(f"Invalid date format: {date_string}. Please use YYYY-MM-DD format.")


def build_view_sql(upload_date):
    """
    Generate SQL to create/replace the store_effective_price_comparisons view.

    Effective price per item per store:
        LEAST(pr.itemprice, COALESCE(ap.discounted_price_per_unit, pr.itemprice))

    Compares each store's effective prices against the national effective average
    from popular_items_avg_effective_prices (the materialized view).

    Only chains in PROMO_CHAINS are included.
    """
    chains_in = ', '.join(f"'{c}'" for c in PROMO_CHAINS)
    subchains_in = ', '.join(f"'{c}'" for c in EXCLUDED_SUBCHAINS)
    cities_in = ', '.join(f"'{c}'" for c in EXCLUDED_CITIES)

    return f"""
    CREATE OR REPLACE VIEW public.store_effective_price_comparisons AS
    WITH effective_store_item_prices AS (
        SELECT
            s.store_code,
            s.storename            AS store_name,
            s.chainname,
            s.subchainname,
            s.storeid,
            s.address,
            s.city,
            s.zipcode,
            s.latitude,
            s.longitude,
            pr.itemcode,
            LEAST(
                pr.itemprice,
                COALESCE(ap.discounted_price_per_unit, pr.itemprice)
            )                      AS effective_price,
            pi.average_price       AS national_avg_effective_price,
            CASE
                WHEN pi.average_price > 0 THEN
                    (
                        LEAST(pr.itemprice, COALESCE(ap.discounted_price_per_unit, pr.itemprice))
                        - pi.average_price
                    ) / pi.average_price * 100
                ELSE NULL
            END                    AS price_diff_percent
        FROM all_stores s
        JOIN allprices pr
            ON pr.store_code  = s.store_code
        LEFT JOIN allpromos ap
            ON  ap.store_code  = pr.store_code
            AND ap.itemcode    = pr.itemcode
            AND ap.upload_date = pr.upload_date
            AND ap.promotion_end_date >= pr.upload_date
            AND ap.discounted_price_per_unit IS NOT NULL
        JOIN popular_items_avg_effective_prices pi
            ON pi.itemcode = pr.itemcode
        WHERE pr.upload_date = '{upload_date}'
            AND pr.itemprice > 0
            AND pr.itemprice IS NOT NULL
            AND s.chainname IN ({chains_in})
            AND s.subchainname NOT IN ({subchains_in})
            AND s.city NOT IN ({cities_in})
    )
    SELECT
        store_code,
        store_name,
        chainname,
        subchainname,
        storeid,
        address,
        city,
        zipcode,
        latitude,
        longitude,
        AVG(price_diff_percent)  AS average_price_diff,
        COUNT(itemcode)          AS popular_item_count
    FROM effective_store_item_prices
    WHERE price_diff_percent IS NOT NULL
    GROUP BY store_code, store_name, chainname, subchainname, storeid,
             address, city, zipcode, latitude, longitude;
    """


def update_view(conn, upload_date):
    """Create or replace the store_effective_price_comparisons view."""
    print(f"[{timestamp()}] Step 1: Updating store_effective_price_comparisons view...")
    print(f"[{timestamp()}]   Date:              {upload_date}")
    print(f"[{timestamp()}]   Chains included:   {', '.join(PROMO_CHAINS)}")

    start_time = datetime.now()
    view_sql = build_view_sql(upload_date)

    cursor = conn.cursor()
    cursor.execute(view_sql)
    conn.commit()

    # Verify view exists
    cursor.execute("""
        SELECT COUNT(*)
        FROM information_schema.views
        WHERE table_schema = 'public'
        AND table_name = 'store_effective_price_comparisons'
    """)
    if cursor.fetchone()[0] == 0:
        raise Exception("View creation failed - view does not exist after CREATE")

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"[{timestamp()}]   ✓ View updated successfully in {elapsed:.1f} seconds")
    cursor.close()


def export_to_csv(conn, upload_date, output_dir):
    """Export the store_effective_price_comparisons view to CSV."""
    print(f"\n[{timestamp()}] Step 2: Exporting view to CSV...")

    start_time = datetime.now()

    print(f"[{timestamp()}]   Loading data from view...")
    query = "SELECT * FROM public.store_effective_price_comparisons ORDER BY store_code"
    df = pd.read_sql_query(query, conn)

    load_elapsed = (datetime.now() - start_time).total_seconds()
    print(f"[{timestamp()}]   ✓ Loaded {len(df):,} stores in {load_elapsed:.1f} seconds")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Dated archive file
    dated_path = output_dir / f"store_effective_comparisons_{upload_date}.csv"
    df.to_csv(dated_path, index=False, encoding='utf-8-sig')

    # Standard file for the map
    map_path = output_dir / "store_effective_comparisons.csv"
    df.to_csv(map_path, index=False, encoding='utf-8-sig')

    export_elapsed = (datetime.now() - start_time).total_seconds()
    print(f"[{timestamp()}]   ✓ Export completed in {export_elapsed:.1f} seconds")

    return df, dated_path, map_path


def show_statistics(df, upload_date, dated_path, map_path, total_elapsed):
    """Display summary statistics."""
    print()
    print("=" * 70)
    print(f"[{timestamp()}] ✓ Export completed successfully!")
    print("=" * 70)

    print(f"\nOutput files:")
    print(f"  1. {dated_path}")
    print(f"  2. {map_path} (for map)")

    print(f"\nSummary:")
    print(f"  - Total stores:   {len(df):,}")
    print(f"  - Unique chains:  {df['chainname'].nunique()}")
    print(f"  - Date:           {upload_date}")

    print(f"\nEffective price difference statistics:")
    print(f"  - Cheapest store:       {df['average_price_diff'].min():.2f}%")
    print(f"  - Most expensive store: {df['average_price_diff'].max():.2f}%")
    print(f"  - Mean difference:      {df['average_price_diff'].mean():.2f}%")
    print(f"  - Median difference:    {df['average_price_diff'].median():.2f}%")

    print(f"\nPopular items per store:")
    print(f"  - Minimum: {int(df['popular_item_count'].min()):,}")
    print(f"  - Maximum: {int(df['popular_item_count'].max()):,}")
    print(f"  - Average: {df['popular_item_count'].mean():.0f}")

    print(f"\nTop 5 cheapest stores (effective prices):")
    for _, row in df.nsmallest(5, 'average_price_diff').iterrows():
        print(f"  {row['store_name']:30} ({row['chainname']:15}, {row['city']:15}): "
              f"{row['average_price_diff']:+6.2f}% | {int(row['popular_item_count']):,} items")

    print(f"\nTop 5 most expensive stores (effective prices):")
    for _, row in df.nlargest(5, 'average_price_diff').iterrows():
        print(f"  {row['store_name']:30} ({row['chainname']:15}, {row['city']:15}): "
              f"{row['average_price_diff']:+6.2f}% | {int(row['popular_item_count']):,} items")

    print(f"\nStores by chain:")
    for chain, count in df['chainname'].value_counts().items():
        avg_diff = df[df['chainname'] == chain]['average_price_diff'].mean()
        print(f"  {chain:20}: {count:3,} stores | avg {avg_diff:+6.2f}%")

    print(f"\nTotal runtime: {total_elapsed / 60:.1f} minutes")
    print("=" * 70)


def interactive_mode():
    """Prompt user for parameters."""
    print("\n" + "=" * 70)
    print("Update Store Effective Price Comparisons and Export")
    print("=" * 70 + "\n")

    while True:
        date_input = input("Enter upload date (YYYY-MM-DD): ").strip()
        try:
            upload_date = validate_date(date_input)
            break
        except ValueError as e:
            print(f"Error: {e}")

    skip_view = input("\nSkip view update? (y/n) [n]: ").strip().lower() in ['y', 'yes']

    return upload_date, skip_view


def main():
    upload_date, skip_view = interactive_mode()

    script_start = datetime.now()
    print()
    print("=" * 70)
    print(f"[{timestamp()}] Starting effective price export for {upload_date}")
    print("=" * 70)
    print()

    try:
        print(f"[{timestamp()}] Connecting to PostgreSQL database...")
        conn = psycopg2.connect(**pg_config)
        print(f"[{timestamp()}]   ✓ Connected successfully!")
        print()

        if not skip_view:
            update_view(conn, upload_date)
        else:
            print(f"[{timestamp()}] Step 1: Skipping view update (using existing view)")

        df, dated_path, map_path = export_to_csv(conn, upload_date, OUTPUT_DIR)
        conn.close()

        total_elapsed = (datetime.now() - script_start).total_seconds()
        show_statistics(df, upload_date, dated_path, map_path, total_elapsed)

    except Exception as e:
        print(f"\n[{timestamp()}] ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
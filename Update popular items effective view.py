#!/usr/bin/env python3
"""
Update Popular Items Effective Prices Materialized View Script
==============================================================

Creates/refreshes the popular_items_avg_effective_prices MATERIALIZED VIEW.

"Effective price" = LEAST(regular_price, promo_price_per_unit)
i.e. if an item is on promotion, use the promo price; otherwise use the regular price.

Only includes chains that have promo data:
    אושר עד, ויקטורי, טיב טעם, יוחננוף, מחסני השוק, קרפור, רמי לוי, שופרסל

Used as the baseline for the subchains map (efoliknot.net/subchains).

Usage:
    python update_popular_items_effective_view.py  (always prompts interactively)

Author: efoliknot team
Last Updated: 2026-05-05
"""

import psycopg2
import time
from datetime import datetime
from config import pg_config

# Chains that have promo data — only these are included in the baseline
PROMO_CHAINS = ['אושר עד', 'ויקטורי', 'טיב טעם', 'יוחננוף', 'מחסני השוק', 'קרפור', 'רמי לוי', 'שופרסל']

# Subchains/cities to exclude (same as main map)
EXCLUDED_SUBCHAINS = ['Be', 'אונליין']
EXCLUDED_CITIES = ['unknown']


def validate_date(date_string):
    """Validate YYYY-MM-DD format."""
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return date_string
    except ValueError:
        raise ValueError(f"Invalid date format: {date_string}. Please use YYYY-MM-DD format.")


def validate_min_stores(min_stores):
    """Validate positive integer."""
    try:
        value = int(min_stores)
        if value < 1:
            raise ValueError("Minimum stores must be at least 1")
        return value
    except (ValueError, TypeError):
        raise ValueError(f"Invalid minimum stores value: {min_stores}. Must be a positive integer.")


def build_matview_sql(upload_date, min_stores):
    """
    Build the CREATE MATERIALIZED VIEW SQL for effective prices.

    Effective price per item per store:
        LEAST(pr.itemprice, COALESCE(ap.discounted_price_per_unit, pr.itemprice))

    Only chains in PROMO_CHAINS are included, since the subchains map
    only shows stores from those chains.

    Parameters are baked in as literals (materialized views cannot be parameterized).
    """
    # Build IN clause for promo chains
    chains_in = ', '.join(f"'{c}'" for c in PROMO_CHAINS)
    subchains_in = ', '.join(f"'{c}'" for c in EXCLUDED_SUBCHAINS)

    return f"""
    CREATE MATERIALIZED VIEW public.popular_items_avg_effective_prices AS
    WITH effective_store_prices AS (
        -- For each store+item, compute the effective price (promo if available, else regular)
        SELECT
            pr.store_code,
            pr.itemcode,
            LEAST(
                pr.itemprice,
                COALESCE(ap.discounted_price_per_unit, pr.itemprice)
            ) AS effective_price
        FROM allprices pr
        LEFT JOIN allpromos ap
            ON  ap.store_code  = pr.store_code
            AND ap.itemcode    = pr.itemcode
            AND ap.upload_date = pr.upload_date
            AND ap.promotion_end_date >= pr.upload_date
            AND ap.discounted_price_per_unit IS NOT NULL
        JOIN all_stores s ON pr.store_code = s.store_code
        WHERE pr.upload_date = '{upload_date}'
            AND pr.itemprice > 0
            AND pr.itemprice IS NOT NULL
            AND s.chainname IN ({chains_in})
            AND s.subchainname NOT IN ({subchains_in})
            AND s.city != 'unknown'
    ),
    popular_items AS (
        -- Items that appear in at least min_stores stores
        SELECT itemcode
        FROM effective_store_prices
        GROUP BY itemcode
        HAVING COUNT(DISTINCT store_code) > {min_stores}
    )
    SELECT
        i.itemcode,
        i.itemname,
        i.supplier,
        i.brand,
        i.category,
        AVG(esp.effective_price)    AS average_price,
        '{upload_date}'::DATE       AS upload_date
    FROM popular_items pi
    JOIN effective_store_prices esp ON esp.itemcode   = pi.itemcode
    JOIN items i                    ON i.itemcode     = pi.itemcode
    GROUP BY i.itemcode, i.itemname, i.supplier, i.brand, i.category
    WITH DATA;
    """


def update_matview(upload_date, min_stores, dry_run=False):
    """
    Drop and recreate the popular_items_avg_effective_prices materialized view.

    Args:
        upload_date (str): Date in YYYY-MM-DD format
        min_stores (int): Minimum number of stores for a popular item
        dry_run (bool): If True, print SQL without executing

    Returns:
        bool: True if successful
    """
    print(f"\n{'=' * 60}")
    print(f"Updating popular_items_avg_effective_prices materialized view")
    print(f"{'=' * 60}")
    print(f"Date:                    {upload_date}")
    print(f"Minimum stores:          {min_stores}")
    print(f"Chains included:         {', '.join(PROMO_CHAINS)}")
    print(f"Dry run:                 {dry_run}")
    print(f"{'=' * 60}\n")

    drop_sql = "DROP MATERIALIZED VIEW IF EXISTS public.popular_items_avg_effective_prices CASCADE;"
    create_sql = build_matview_sql(upload_date, min_stores)

    if dry_run:
        print("DRY RUN - SQL that would be executed:")
        print("-" * 60)
        print(drop_sql)
        print()
        print(create_sql)
        print("-" * 60)
        return True

    conn = None
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(**pg_config)
        cursor = conn.cursor()

        print("Setting statement timeout to 10 minutes...")
        cursor.execute("SET statement_timeout = '600000';")

        print("Dropping existing materialized view (if exists)...")
        cursor.execute(drop_sql)
        conn.commit()

        print("Creating materialized view (this may take several minutes)...")
        start_time = time.time()
        cursor.execute(create_sql)
        conn.commit()
        elapsed = time.time() - start_time
        print(f"  ✓ Completed in {elapsed:.2f} seconds")

        # Verify
        print("Verifying data...")
        cursor.execute("SELECT COUNT(*) FROM public.popular_items_avg_effective_prices")
        item_count = cursor.fetchone()[0]

        cursor.execute("SELECT DISTINCT upload_date FROM public.popular_items_avg_effective_prices")
        result = cursor.fetchone()
        stored_date = result[0] if result else None

        if item_count > 0:
            print(f"\n✓ Materialized view successfully created!")
            print(f"✓ Number of popular items: {item_count:,}")
            print(f"✓ Data date:               {stored_date}")
            print(f"✓ Total time:              {elapsed:.2f} seconds")

            print("\nSample of popular items (first 5):")
            cursor.execute("""
                SELECT itemcode, itemname, average_price
                FROM public.popular_items_avg_effective_prices
                LIMIT 5
            """)
            for row in cursor.fetchall():
                print(f"  - {row[0]}: {row[1]} (avg effective: ₪{row[2]:.2f})")

            cursor.execute("""
                SELECT
                    MIN(average_price) AS min_price,
                    MAX(average_price) AS max_price,
                    AVG(average_price) AS avg_price
                FROM public.popular_items_avg_effective_prices
            """)
            stats = cursor.fetchone()
            print(f"\nEffective price statistics:")
            print(f"  Min:     ₪{stats[0]:.2f}")
            print(f"  Max:     ₪{stats[1]:.2f}")
            print(f"  Average: ₪{stats[2]:.2f}")
        else:
            print("\n✗ Materialized view creation failed - no items found")
            return False

        cursor.close()
        conn.close()

        print(f"\n{'=' * 60}")
        print("Update completed successfully!")
        print(f"{'=' * 60}\n")
        return True

    except psycopg2.Error as e:
        print(f"\n✗ Database error: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        if conn:
            conn.rollback()
        return False


def interactive_mode():
    """Prompt user for parameters."""
    print("\n" + "=" * 60)
    print("Popular Items Effective Prices Materialized View Update")
    print("=" * 60 + "\n")

    while True:
        date_input = input("Enter upload date (YYYY-MM-DD): ").strip()
        try:
            upload_date = validate_date(date_input)
            break
        except ValueError as e:
            print(f"Error: {e}")

    while True:
        stores_input = input("Enter minimum stores threshold [10]: ").strip()
        if not stores_input:
            stores_input = "10"
        try:
            min_stores = validate_min_stores(stores_input)
            break
        except ValueError as e:
            print(f"Error: {e}")

    dry_run_input = input("Dry run only? (y/n) [n]: ").strip().lower()
    dry_run = dry_run_input in ['y', 'yes']

    return upload_date, min_stores, dry_run


def main():
    upload_date, min_stores, dry_run = interactive_mode()

    if not dry_run:
        print(f"\nAbout to recreate materialized view with:")
        print(f"  Date:           {upload_date}")
        print(f"  Minimum stores: {min_stores}")
        confirm = input("\nProceed? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("Operation cancelled.")
            return

    success = update_matview(upload_date, min_stores, dry_run)
    if not success:
        exit(1)


if __name__ == "__main__":
    main()
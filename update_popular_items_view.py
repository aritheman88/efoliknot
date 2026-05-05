#!/usr/bin/env python3
"""
Update Popular Items Materialized View Script
=============================================

Creates/refreshes the popular_items_avg_prices MATERIALIZED VIEW with configurable:
- Date for price data
- Minimum number of stores threshold for "popular" items

Usage:
    python update_popular_items_view.py  (always prompts interactively)

Author: efoliknot team
Last Updated: 2026-05-01
"""

import psycopg2
import argparse
from datetime import datetime
import time
from config import pg_config


def validate_date(date_string):
    """
    Validate that the date string is in YYYY-MM-DD format.

    Args:
        date_string (str): Date in YYYY-MM-DD format

    Returns:
        str: Valid date string

    Raises:
        ValueError: If date format is invalid
    """
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return date_string
    except ValueError:
        raise ValueError(f"Invalid date format: {date_string}. Please use YYYY-MM-DD format.")


def validate_min_stores(min_stores):
    """
    Validate that minimum stores is a positive integer.

    Args:
        min_stores: Value to validate

    Returns:
        int: Valid minimum stores value

    Raises:
        ValueError: If value is not a positive integer
    """
    try:
        value = int(min_stores)
        if value < 1:
            raise ValueError("Minimum stores must be at least 1")
        return value
    except (ValueError, TypeError):
        raise ValueError(f"Invalid minimum stores value: {min_stores}. Must be a positive integer.")


def build_matview_sql(upload_date, min_stores):
    """
    Build the CREATE MATERIALIZED VIEW SQL with date and min_stores baked in as literals.

    Materialized views cannot accept parameters, so values are embedded directly
    into the SQL. The view is always dropped and recreated when parameters change.

    Args:
        upload_date (str): Date string in YYYY-MM-DD format
        min_stores (int): Minimum number of stores threshold

    Returns:
        str: Complete CREATE MATERIALIZED VIEW SQL statement
    """
    return f"""
    CREATE MATERIALIZED VIEW public.popular_items_avg_prices AS
    WITH popular_items AS (
        SELECT allprices.itemcode
        FROM allprices
        JOIN all_stores ON allprices.store_code = all_stores.store_code
        WHERE allprices.upload_date = '{upload_date}'
            AND allprices.itemprice > 0
            AND allprices.itemprice IS NOT NULL
            AND all_stores.chainname NOT IN ('סופר פארם', 'Yellow', 'דור אלון')
            AND all_stores.subchainname != 'Be'
            AND all_stores.subchainname != 'אונליין'
        GROUP BY allprices.itemcode
        HAVING COUNT(DISTINCT allprices.store_code) > {min_stores}
    )
    SELECT
        i.itemcode,
        i.itemname,
        i.supplier,
        i.brand,
        i.category,
        AVG(p.itemprice) AS average_price,
        '{upload_date}'::DATE AS upload_date
    FROM popular_items pi
    JOIN items i ON pi.itemcode = i.itemcode
    JOIN allprices p ON i.itemcode = p.itemcode
    JOIN all_stores s ON p.store_code = s.store_code
    WHERE p.upload_date = '{upload_date}'
        AND p.itemprice > 0
        AND p.itemprice IS NOT NULL
        AND s.chainname NOT IN ('סופר פארם', 'Yellow', 'דור אלון')
        AND s.subchainname != 'Be'
        AND s.subchainname != 'אונליין'
    GROUP BY i.itemcode, i.itemname, i.supplier, i.brand, i.category
    WITH DATA;
    """


def update_matview(upload_date, min_stores, dry_run=False):
    """
    Drop and recreate the popular_items_avg_prices materialized view.

    Because upload_date and min_stores are baked into the view definition as
    literals (materialized views cannot accept parameters), we always drop and
    recreate rather than using REFRESH MATERIALIZED VIEW.

    Args:
        upload_date (str): Date in YYYY-MM-DD format
        min_stores (int): Minimum number of stores
        dry_run (bool): If True, print SQL without executing

    Returns:
        bool: True if successful, False otherwise
    """
    print(f"\n{'=' * 60}")
    print(f"Updating popular_items_avg_prices materialized view")
    print(f"{'=' * 60}")
    print(f"Date: {upload_date}")
    print(f"Minimum stores threshold: {min_stores}")
    print(f"Dry run: {dry_run}")
    print(f"{'=' * 60}\n")

    drop_sql = "DROP MATERIALIZED VIEW IF EXISTS public.popular_items_avg_prices;"
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

        print("Creating materialized view (this may take a few minutes)...")
        start_time = time.time()
        cursor.execute(create_sql)
        conn.commit()
        elapsed = time.time() - start_time
        print(f"  ✓ Completed in {elapsed:.2f} seconds")

        # Verify the data
        print("Verifying data...")
        cursor.execute("SELECT COUNT(*) FROM public.popular_items_avg_prices")
        item_count = cursor.fetchone()[0]

        cursor.execute("SELECT DISTINCT upload_date FROM public.popular_items_avg_prices")
        result = cursor.fetchone()
        stored_date = result[0] if result else None

        if item_count > 0:
            print(f"\n✓ Materialized view successfully created!")
            print(f"✓ Number of popular items: {item_count:,}")
            print(f"✓ Data date: {stored_date}")
            print(f"✓ Total time: {elapsed:.2f} seconds")

            print("\nSample of popular items (first 5):")
            cursor.execute("""
                SELECT itemcode, itemname, average_price
                FROM public.popular_items_avg_prices
                LIMIT 5
            """)
            for row in cursor.fetchall():
                print(f"  - {row[0]}: {row[1]} (avg: ₪{row[2]:.2f})")

            cursor.execute("""
                SELECT
                    MIN(average_price) AS min_price,
                    MAX(average_price) AS max_price,
                    AVG(average_price) AS avg_price
                FROM public.popular_items_avg_prices
            """)
            stats = cursor.fetchone()
            print(f"\nPrice statistics:")
            print(f"  Min: ₪{stats[0]:.2f}")
            print(f"  Max: ₪{stats[1]:.2f}")
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
    """
    Prompt the user for upload_date, min_stores, and dry_run flag.

    Returns:
        tuple: (upload_date, min_stores, dry_run)
    """
    print("\n" + "=" * 60)
    print("Popular Items Materialized View Update")
    print("=" * 60 + "\n")

    # Get date
    while True:
        date_input = input("Enter upload date (YYYY-MM-DD): ").strip()
        try:
            upload_date = validate_date(date_input)
            break
        except ValueError as e:
            print(f"Error: {e}")

    # Get minimum stores
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
    """Main entry point — always runs in interactive mode."""
    upload_date, min_stores, dry_run = interactive_mode()

    if not dry_run:
        print("\nYou are about to recreate the materialized view with:")
        print(f"  Date: {upload_date}")
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
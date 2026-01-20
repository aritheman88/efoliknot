#!/usr/bin/env python3
"""
Update Popular Items Table Script
==================================

Creates/updates the popular_items_avg_prices TABLE with configurable:
- Date for price data
- Minimum number of stores threshold for "popular" items

This produces IDENTICAL results to the view version, but stored as a table.

Usage:
    python update_popular_items_view.py --date 2026-01-11 --min-stores 10
    python update_popular_items_view.py -d 2026-01-11 -m 10
    python update_popular_items_view.py  (interactive mode)

Author: efoliknot team
Last Updated: 2026-01-20
"""

import psycopg2
from psycopg2 import sql
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


def update_view(upload_date,min_stores,dry_run=False):
    """
    Update the popular_items_avg_prices table in the database.

    Args:
        upload_date (str): Date in YYYY-MM-DD format
        min_stores (int): Minimum number of stores
        dry_run (bool): If True, print SQL without executing

    Returns:
        bool: True if successful, False otherwise
    """
    print(f"\n{'=' * 60}")
    print(f"Updating popular_items_avg_prices table")
    print(f"{'=' * 60}")
    print(f"Date: {upload_date}")
    print(f"Minimum stores threshold: {min_stores}")
    print(f"Dry run: {dry_run}")
    print(f"{'=' * 60}\n")

    # SQL statements
    drop_table_sql = "DROP TABLE IF EXISTS public.popular_items_avg_prices;"

    create_table_sql = """
    CREATE TABLE public.popular_items_avg_prices (
        itemcode BIGINT,
        itemname TEXT,
        supplier TEXT,
        brand TEXT,
        category TEXT,
        average_price DOUBLE PRECISION,
        upload_date DATE,
        PRIMARY KEY (itemcode)
    );
    """

    # This is IDENTICAL to the view SQL, just wrapped in INSERT INTO
    # and with upload_date column added to SELECT
    insert_sql = """
    INSERT INTO public.popular_items_avg_prices
    WITH popular_items AS (
        SELECT allprices.itemcode
        FROM allprices
        JOIN all_stores ON allprices.store_code = all_stores.store_code
        WHERE allprices.upload_date = %s
            AND allprices.itemprice > 0
            AND allprices.itemprice IS NOT NULL
            AND all_stores.chainname NOT IN ('סופר פארם', 'Yellow', 'דור אלון')
            AND all_stores.subchainname != 'Be'
            AND all_stores.subchainname != 'אונליין'
        GROUP BY allprices.itemcode
        HAVING COUNT(DISTINCT allprices.store_code) > %s
    )
    SELECT 
        i.itemcode,
        i.itemname,
        i.supplier,
        i.brand,
        i.category,
        AVG(p.itemprice) AS average_price,
        %s::DATE AS upload_date
    FROM popular_items pi
    JOIN items i ON pi.itemcode = i.itemcode
    JOIN allprices p ON i.itemcode = p.itemcode
    JOIN all_stores s ON p.store_code = s.store_code
    WHERE p.upload_date = %s
        AND p.itemprice > 0
        AND p.itemprice IS NOT NULL
        AND s.chainname NOT IN ('סופר פארם', 'Yellow', 'דור אלון')
        AND s.subchainname != 'Be'
        AND s.subchainname != 'אונליין'
    GROUP BY i.itemcode, i.itemname, i.supplier, i.brand, i.category;
    """

    if dry_run:
        print("DRY RUN - SQL that would be executed:")
        print("-" * 60)
        print(drop_table_sql)
        print()
        print(create_table_sql)
        print()
        print(insert_sql)
        print("\nParameters:")
        print(f"  1. upload_date (CTE WHERE): {upload_date}")
        print(f"  2. min_stores (HAVING): {min_stores}")
        print(f"  3. upload_date (column): {upload_date}")
        print(f"  4. upload_date (main WHERE): {upload_date}")
        print("-" * 60)
        return True

    try:
        # Connect to database
        print("Connecting to database...")
        conn = psycopg2.connect(**pg_config)
        cursor = conn.cursor()

        # Set longer timeout for this session
        print("Setting statement timeout to 10 minutes...")
        cursor.execute("SET statement_timeout = '600000';")  # 10 minutes

        # Drop existing table if it exists
        print("Dropping old table (if exists)...")
        cursor.execute(drop_table_sql)
        conn.commit()

        # Create table with correct structure
        print("Creating table with new structure...")
        start_time = time.time()
        cursor.execute(create_table_sql)
        conn.commit()
        create_time = time.time() - start_time
        print(f"  ✓ Completed in {create_time:.2f} seconds")

        # Insert new data - SAME parameters as original view script
        print("Populating table with new data (this may take a few minutes)...")
        start_time = time.time()
        cursor.execute(insert_sql,(upload_date,min_stores,upload_date,upload_date))
        insert_time = time.time() - start_time
        print(f"  ✓ Completed in {insert_time:.2f} seconds")

        # Commit the transaction
        conn.commit()

        # Verify the data
        print("Verifying data...")
        cursor.execute("SELECT COUNT(*) FROM public.popular_items_avg_prices")
        item_count = cursor.fetchone()[0]

        # Verify the date
        cursor.execute("SELECT DISTINCT upload_date FROM public.popular_items_avg_prices")
        result = cursor.fetchone()
        stored_date = result[0] if result else None

        if item_count > 0:
            print(f"\n✓ Table successfully updated!")
            print(f"✓ Number of popular items: {item_count}")
            print(f"✓ Data date: {stored_date}")
            print(f"✓ Total time: {create_time + insert_time:.2f} seconds")

            # Show sample of results
            print("\nSample of popular items (first 5):")
            cursor.execute("""
                SELECT itemcode, itemname, average_price 
                FROM public.popular_items_avg_prices 
                LIMIT 5
            """)
            for row in cursor.fetchall():
                print(f"  - {row[0]}: {row[1]} (avg: ₪{row[2]:.2f})")

            # Show some statistics
            cursor.execute("""
                SELECT 
                    MIN(average_price) as min_price,
                    MAX(average_price) as max_price,
                    AVG(average_price) as avg_price
                FROM public.popular_items_avg_prices
            """)
            stats = cursor.fetchone()
            print(f"\nPrice statistics:")
            print(f"  Min: ₪{stats[0]:.2f}")
            print(f"  Max: ₪{stats[1]:.2f}")
            print(f"  Average: ₪{stats[2]:.2f}")
        else:
            print("\n✗ Table update failed - no items inserted")
            return False

        cursor.close()
        conn.close()

        print(f"\n{'=' * 60}")
        print("Update completed successfully!")
        print("Note: Table contains same data as view, stored physically for fast querying.")
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
    Run the script in interactive mode, prompting user for inputs.

    Returns:
        tuple: (upload_date, min_stores, dry_run)
    """
    print("\n" + "=" * 60)
    print("Popular Items Table Update - Interactive Mode")
    print("=" * 60 + "\n")

    # Get date
    while True:
        date_input = input("Enter upload date (YYYY-MM-DD) [2026-01-11]: ").strip()
        if not date_input:
            date_input = "2026-01-11"

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

    # Ask about dry run
    dry_run_input = input("Dry run only? (y/n) [n]: ").strip().lower()
    dry_run = dry_run_input in ['y', 'yes']

    return upload_date, min_stores, dry_run


def main():
    """Main function to parse arguments and update the table."""
    parser = argparse.ArgumentParser(
        description='Update the popular_items_avg_prices PostgreSQL table (same logic as view)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --date 2026-01-11 --min-stores 10
  %(prog)s -d 2026-01-11 -m 15
  %(prog)s --dry-run -d 2026-01-11 -m 10
  %(prog)s  (interactive mode)

Note: This produces IDENTICAL results to the view version, stored as a table.
        """
    )

    parser.add_argument(
        '-d', '--date',
        type=str,
        help='Upload date in YYYY-MM-DD format (e.g., 2026-01-11)'
    )

    parser.add_argument(
        '-m', '--min-stores',
        type=int,
        help='Minimum number of stores for item to be considered popular (e.g., 10)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print SQL without executing (for testing)'
    )

    args = parser.parse_args()

    # If no arguments provided, run in interactive mode
    if args.date is None and args.min_stores is None:
        upload_date, min_stores, dry_run = interactive_mode()
    else:
        # Validate required arguments
        if args.date is None or args.min_stores is None:
            parser.error("Both --date and --min-stores are required (or run without arguments for interactive mode)")

        try:
            upload_date = validate_date(args.date)
            min_stores = validate_min_stores(args.min_stores)
            dry_run = args.dry_run
        except ValueError as e:
            parser.error(str(e))

    # Confirm before execution (unless dry run)
    if not dry_run:
        print("\nYou are about to update the database table with the following settings:")
        print(f"  Date: {upload_date}")
        print(f"  Minimum stores: {min_stores}")
        confirm = input("\nProceed? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("Operation cancelled.")
            return

    # Execute the update
    success = update_view(upload_date, min_stores, dry_run)

    if not success:
        exit(1)


if __name__ == "__main__":
    main()
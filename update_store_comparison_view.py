#!/usr/bin/env python3
"""
Update Store Price Comparisons View Script
==========================================

Updates the store_price_comparisons PostgreSQL view with configurable:
- Date for price data
- Chains to exclude
- Subchains to exclude
- Cities to exclude

This view calculates each store's average price difference compared to
the national average, based on popular items.

Usage:
    python update_store_comparisons_view.py --date 2025-11-02
    python update_store_comparisons_view.py -d 2025-11-02 --exclude-chains "Yellow,דור אלון"
    python update_store_comparisons_view.py  (interactive mode)

Author: efoliknot team
Last Updated: 2025-11-13
"""

import psycopg2
from psycopg2 import sql
import argparse
from datetime import datetime
from config import pg_config

# Default filters
DEFAULT_EXCLUDED_CHAINS = ['סופר פארם','Yellow','דור אלון']
DEFAULT_EXCLUDED_SUBCHAINS = ['Be','אונליין', 'מרכז לוגיסטי', 'מרכז מכירה וחלוקה', 'רמי לוי לעסקים']
DEFAULT_EXCLUDED_CITIES = ['unknown']


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
        datetime.strptime(date_string,'%Y-%m-%d')
        return date_string
    except ValueError:
        raise ValueError(f"Invalid date format: {date_string}. Please use YYYY-MM-DD format.")


def parse_list_input(input_string):
    """
    Parse a comma-separated string into a list.

    Args:
        input_string (str): Comma-separated values

    Returns:
        list: List of stripped values
    """
    if not input_string or input_string.strip() == '':
        return []
    return [item.strip() for item in input_string.split(',') if item.strip()]


def create_view_sql(upload_date,excluded_chains,excluded_subchains,excluded_cities):
    """
    Generate the SQL statement to create/replace the store_price_comparisons view.

    Args:
        upload_date (str): Date in YYYY-MM-DD format
        excluded_chains (list): List of chain names to exclude
        excluded_subchains (list): List of subchain names to exclude
        excluded_cities (list): List of cities to exclude

    Returns:
        tuple: (sql_template, parameters) for parameterized query
    """
    # Build the WHERE clause conditions
    where_conditions = []
    params = []

    # Date condition (appears twice in the query)
    params.append(upload_date)

    # Price conditions
    where_conditions.append("p.itemprice > 0")
    where_conditions.append("p.itemprice IS NOT NULL")

    # Chain exclusions
    if excluded_chains:
        # We need to add each chain as a separate parameter
        chain_placeholders = []
        for chain in excluded_chains:
            params.append(chain)
            chain_placeholders.append('%s')
        where_conditions.append(f"s.chainname NOT IN ({','.join(chain_placeholders)})")

    # Subchain exclusions
    if excluded_subchains:
        subchain_placeholders = []
        for subchain in excluded_subchains:
            params.append(subchain)
            subchain_placeholders.append('%s')
        where_conditions.append(f"s.subchainname NOT IN ({','.join(subchain_placeholders)})")

    # City exclusions
    if excluded_cities:
        city_placeholders = []
        for city in excluded_cities:
            params.append(city)
            city_placeholders.append('%s')
        where_conditions.append(f"s.city NOT IN ({','.join(city_placeholders)})")

    where_clause = " AND ".join(where_conditions)

    sql_template = f"""
    CREATE OR REPLACE VIEW public.store_price_comparisons AS
    WITH store_item_price_diffs AS (
        SELECT 
            s.store_code,
            s.storename AS store_name,
            s.chainname,
            s.subchainname,
            s.storeid,
            s.address,
            s.city,
            s.zipcode,
            s.latitude,
            s.longitude,
            p.itemcode,
            p.itemprice,
            pi.average_price,
            CASE
                WHEN pi.average_price > 0 THEN 
                    ((p.itemprice - pi.average_price) / pi.average_price) * 100
                ELSE NULL
            END AS price_diff_percent
        FROM all_stores s
        JOIN allprices p ON s.store_code = p.store_code
        JOIN popular_items_avg_prices pi ON p.itemcode = pi.itemcode
        WHERE p.upload_date = %s
            AND {where_clause}
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
        AVG(price_diff_percent) AS average_price_diff,
        COUNT(itemcode) AS popular_item_count
    FROM store_item_price_diffs
    WHERE price_diff_percent IS NOT NULL
    GROUP BY store_code, store_name, chainname, subchainname, storeid, address, city, zipcode, latitude, longitude;
    """

    return sql_template,params


def update_view(upload_date,excluded_chains,excluded_subchains,excluded_cities,dry_run=False):
    """
    Update the store_price_comparisons view in the database.

    Args:
        upload_date (str): Date in YYYY-MM-DD format
        excluded_chains (list): List of chain names to exclude
        excluded_subchains (list): List of subchain names to exclude
        excluded_cities (list): List of cities to exclude
        dry_run (bool): If True, print SQL without executing

    Returns:
        bool: True if successful, False otherwise
    """
    print(f"\n{'=' * 70}")
    print(f"Updating store_price_comparisons view")
    print(f"{'=' * 70}")
    print(f"Date: {upload_date}")
    print(f"Excluded chains: {excluded_chains if excluded_chains else '(none)'}")
    print(f"Excluded subchains: {excluded_subchains if excluded_subchains else '(none)'}")
    print(f"Excluded cities: {excluded_cities if excluded_cities else '(none)'}")
    print(f"Dry run: {dry_run}")
    print(f"{'=' * 70}\n")

    # Generate SQL
    view_sql,params = create_view_sql(upload_date,excluded_chains,excluded_subchains,excluded_cities)

    if dry_run:
        print("DRY RUN - SQL that would be executed:")
        print("-" * 70)
        print(view_sql)
        print("\nParameters:")
        for i,param in enumerate(params,1):
            print(f"  {i}. {param}")
        print("-" * 70)
        return True

    try:
        # Connect to database
        print("Connecting to database...")
        conn = psycopg2.connect(**pg_config)
        cursor = conn.cursor()

        # Execute the view creation with parameterized values
        print("Executing view update...")
        cursor.execute(view_sql,params)

        # Commit the transaction
        conn.commit()

        # Verify the view was created
        print("Verifying view creation...")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.views 
            WHERE table_schema = 'public' 
            AND table_name = 'store_price_comparisons'
        """)
        view_exists = cursor.fetchone()[0] > 0

        if view_exists:
            # Get count of stores in the view
            cursor.execute("SELECT COUNT(*) FROM public.store_price_comparisons")
            store_count = cursor.fetchone()[0]

            print(f"\n✓ View successfully updated!")
            print(f"✓ Number of stores: {store_count}")

            # Show statistics
            cursor.execute("""
                SELECT 
                    MIN(average_price_diff) as min_diff,
                    MAX(average_price_diff) as max_diff,
                    AVG(average_price_diff) as avg_diff,
                    MIN(popular_item_count) as min_items,
                    MAX(popular_item_count) as max_items,
                    AVG(popular_item_count) as avg_items
                FROM public.store_price_comparisons
            """)
            stats = cursor.fetchone()

            print(f"\nPrice difference statistics:")
            print(f"  - Cheapest store: {stats[0]:.2f}% below average")
            print(f"  - Most expensive store: {stats[1]:.2f}% above average")
            print(f"  - Mean store difference: {stats[2]:.2f}%")

            print(f"\nPopular items per store:")
            print(f"  - Minimum: {int(stats[3])} items")
            print(f"  - Maximum: {int(stats[4])} items")
            print(f"  - Average: {stats[5]:.0f} items")

            # Show sample stores
            print("\nSample stores (5 cheapest):")
            cursor.execute("""
                SELECT store_name, chainname, city, average_price_diff, popular_item_count
                FROM public.store_price_comparisons 
                ORDER BY average_price_diff ASC
                LIMIT 5
            """)
            for row in cursor.fetchall():
                print(f"  - {row[0]} ({row[1]}, {row[2]}): {row[3]:.2f}% | {row[4]} items")

            print("\nSample stores (5 most expensive):")
            cursor.execute("""
                SELECT store_name, chainname, city, average_price_diff, popular_item_count
                FROM public.store_price_comparisons 
                ORDER BY average_price_diff DESC
                LIMIT 5
            """)
            for row in cursor.fetchall():
                print(f"  - {row[0]} ({row[1]}, {row[2]}): {row[3]:+.2f}% | {row[4]} items")
        else:
            print("\n✗ View creation failed - view does not exist")
            return False

        cursor.close()
        conn.close()

        print(f"\n{'=' * 70}")
        print("Update completed successfully!")
        print(f"{'=' * 70}\n")

        return True

    except psycopg2.Error as e:
        print(f"\n✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False


def interactive_mode():
    """
    Run the script in interactive mode, prompting user for inputs.

    Returns:
        tuple: (upload_date, excluded_chains, excluded_subchains, excluded_cities, dry_run)
    """
    print("\n" + "=" * 70)
    print("Store Price Comparisons View Update - Interactive Mode")
    print("=" * 70 + "\n")

    # Get date
    while True:
        date_input = input("Enter upload date (YYYY-MM-DD) [2025-11-02]: ").strip()
        if not date_input:
            date_input = "2025-11-02"

        try:
            upload_date = validate_date(date_input)
            break
        except ValueError as e:
            print(f"Error: {e}")

    # Get excluded chains
    print(f"\nDefault excluded chains: {', '.join(DEFAULT_EXCLUDED_CHAINS)}")
    chains_input = input("Enter excluded chains (comma-separated) or press Enter for defaults: ").strip()
    if chains_input:
        excluded_chains = parse_list_input(chains_input)
    else:
        excluded_chains = DEFAULT_EXCLUDED_CHAINS

    # Get excluded subchains
    print(f"\nDefault excluded subchains: {', '.join(DEFAULT_EXCLUDED_SUBCHAINS)}")
    subchains_input = input("Enter excluded subchains (comma-separated) or press Enter for defaults: ").strip()
    if subchains_input:
        excluded_subchains = parse_list_input(subchains_input)
    else:
        excluded_subchains = DEFAULT_EXCLUDED_SUBCHAINS

    # Get excluded cities
    print(f"\nDefault excluded cities: {', '.join(DEFAULT_EXCLUDED_CITIES)}")
    cities_input = input("Enter excluded cities (comma-separated) or press Enter for defaults: ").strip()
    if cities_input:
        excluded_cities = parse_list_input(cities_input)
    else:
        excluded_cities = DEFAULT_EXCLUDED_CITIES

    # Ask about dry run
    dry_run_input = input("\nDry run only? (y/n) [n]: ").strip().lower()
    dry_run = dry_run_input in ['y','yes']

    return upload_date,excluded_chains,excluded_subchains,excluded_cities,dry_run


def main():
    """Main function to parse arguments and update the view."""
    parser = argparse.ArgumentParser(
        description='Update the store_price_comparisons PostgreSQL view',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --date 2025-11-02
  %(prog)s -d 2025-11-02 --exclude-chains "Yellow,דור אלון"
  %(prog)s -d 2025-11-02 --exclude-subchains "Be,אונליין"
  %(prog)s --dry-run -d 2025-11-02
  %(prog)s  (interactive mode)

Default exclusions:
  Chains: סופר פארם, Yellow, דור אלון
  Subchains: Be, אונליין
  Cities: unknown
        """
    )

    parser.add_argument(
        '-d','--date',
        type=str,
        help='Upload date in YYYY-MM-DD format (e.g., 2025-11-02)'
    )

    parser.add_argument(
        '--exclude-chains',
        type=str,
        help='Comma-separated list of chain names to exclude (overrides defaults)'
    )

    parser.add_argument(
        '--exclude-subchains',
        type=str,
        help='Comma-separated list of subchain names to exclude (overrides defaults)'
    )

    parser.add_argument(
        '--exclude-cities',
        type=str,
        help='Comma-separated list of cities to exclude (overrides defaults)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print SQL without executing (for testing)'
    )

    args = parser.parse_args()

    # If no date provided, run in interactive mode
    if args.date is None:
        upload_date,excluded_chains,excluded_subchains,excluded_cities,dry_run = interactive_mode()
    else:
        try:
            upload_date = validate_date(args.date)
        except ValueError as e:
            parser.error(str(e))

        # Use provided exclusions or defaults
        if args.exclude_chains is not None:
            excluded_chains = parse_list_input(args.exclude_chains)
        else:
            excluded_chains = DEFAULT_EXCLUDED_CHAINS

        if args.exclude_subchains is not None:
            excluded_subchains = parse_list_input(args.exclude_subchains)
        else:
            excluded_subchains = DEFAULT_EXCLUDED_SUBCHAINS

        if args.exclude_cities is not None:
            excluded_cities = parse_list_input(args.exclude_cities)
        else:
            excluded_cities = DEFAULT_EXCLUDED_CITIES

        dry_run = args.dry_run

    # Confirm before execution (unless dry run)
    if not dry_run:
        print("\nYou are about to update the database view with the following settings:")
        print(f"  Date: {upload_date}")
        print(f"  Excluded chains: {excluded_chains if excluded_chains else '(none)'}")
        print(f"  Excluded subchains: {excluded_subchains if excluded_subchains else '(none)'}")
        print(f"  Excluded cities: {excluded_cities if excluded_cities else '(none)'}")
        confirm = input("\nProceed? (y/n): ").strip().lower()
        if confirm not in ['y','yes']:
            print("Operation cancelled.")
            return

    # Execute the update
    success = update_view(upload_date,excluded_chains,excluded_subchains,excluded_cities,dry_run)

    if not success:
        exit(1)


if __name__ == "__main__":
    main()
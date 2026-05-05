#!/usr/bin/env python3
"""
Update Store Price Comparisons View and Export to CSV
=====================================================

This script does TWO things:
1. Updates the store_price_comparisons database view with configurable parameters
2. Exports the view results to a CSV file with detailed progress tracking

Usage:
    python update_and_export_stores.py --date 2025-11-02
    python update_and_export_stores.py -d 2025-11-02 --skip-view-update
    python update_and_export_stores.py  (interactive mode)

Author: efoliknot team
Last Updated: 2025-11-13
"""

import psycopg2
import pandas as pd
from pathlib import Path
import argparse
from datetime import datetime
import warnings
from config import pg_config

# Suppress pandas warnings
warnings.filterwarnings('ignore')

# Default filters
DEFAULT_EXCLUDED_CHAINS = ['סופר פארם','Yellow','דור אלון']
DEFAULT_EXCLUDED_SUBCHAINS = ['Be','אונליין']
DEFAULT_EXCLUDED_CITIES = ['unknown']

# Output directory
OUTPUT_DIR = Path(__file__).parent / 'data'


def timestamp():
    """Return current timestamp string"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def validate_date(date_string):
    """Validate date format"""
    try:
        datetime.strptime(date_string,'%Y-%m-%d')
        return date_string
    except ValueError:
        raise ValueError(f"Invalid date format: {date_string}. Please use YYYY-MM-DD format.")


def parse_list_input(input_string):
    """Parse comma-separated string into list"""
    if not input_string or input_string.strip() == '':
        return []
    return [item.strip() for item in input_string.split(',') if item.strip()]


def create_view_sql(upload_date,excluded_chains,excluded_subchains,excluded_cities):
    """Generate SQL to create/replace the store_price_comparisons view
        Note: This view joins with the popular_items_avg_prices TABLE
    (not a view anymore), which makes it much faster.
"""
    where_conditions = []
    params = []

    params.append(upload_date)
    where_conditions.append("p.itemprice > 0")
    where_conditions.append("p.itemprice IS NOT NULL")

    if excluded_chains:
        chain_placeholders = []
        for chain in excluded_chains:
            params.append(chain)
            chain_placeholders.append('%s')
        where_conditions.append(f"s.chainname NOT IN ({','.join(chain_placeholders)})")

    if excluded_subchains:
        subchain_placeholders = []
        for subchain in excluded_subchains:
            params.append(subchain)
            subchain_placeholders.append('%s')
        where_conditions.append(f"s.subchainname NOT IN ({','.join(subchain_placeholders)})")

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


def update_view(conn,upload_date,excluded_chains,excluded_subchains,excluded_cities):
    """Update the store_price_comparisons view"""
    print(f"[{timestamp()}] Step 1: Updating store_price_comparisons view...")
    print(f"[{timestamp()}]   Date: {upload_date}")
    print(f"[{timestamp()}]   Excluded chains: {excluded_chains if excluded_chains else '(none)'}")
    print(f"[{timestamp()}]   Excluded subchains: {excluded_subchains if excluded_subchains else '(none)'}")
    print(f"[{timestamp()}]   Excluded cities: {excluded_cities if excluded_cities else '(none)'}")

    start_time = datetime.now()

    view_sql,params = create_view_sql(upload_date,excluded_chains,excluded_subchains,excluded_cities)

    cursor = conn.cursor()
    cursor.execute(view_sql,params)
    conn.commit()

    # Verify view exists
    cursor.execute("""
        SELECT COUNT(*) 
        FROM information_schema.views 
        WHERE table_schema = 'public' 
        AND table_name = 'store_price_comparisons'
    """)
    view_exists = cursor.fetchone()[0] > 0

    if not view_exists:
        raise Exception("View creation failed - view does not exist")

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"[{timestamp()}]   ✓ View updated successfully in {elapsed:.1f} seconds")

    cursor.close()
    return True


def export_to_csv(conn,upload_date,output_dir):
    """Export the store_price_comparisons view to CSV"""
    print(f"\n[{timestamp()}] Step 2: Exporting view to CSV...")

    start_time = datetime.now()

    # Read the entire view into pandas
    print(f"[{timestamp()}]   Loading data from view...")
    query = "SELECT * FROM public.store_price_comparisons ORDER BY store_code"
    df = pd.read_sql_query(query,conn)

    load_elapsed = (datetime.now() - start_time).total_seconds()
    print(f"[{timestamp()}]   ✓ Loaded {len(df):,} stores in {load_elapsed:.1f} seconds")

    # Create output filename with date
    output_filename = f"store_price_comparisons_{upload_date}.csv"
    output_path = output_dir / output_filename

    # Ensure output directory exists
    output_dir.mkdir(parents=True,exist_ok=True)

    # Export to CSV
    print(f"[{timestamp()}]   Writing to {output_filename}...")
    df.to_csv(output_path,index=False,encoding='utf-8-sig')

    # Also save to the standard location for the map
    map_csv_path = output_dir / "store_price_comparisons.csv"
    df.to_csv(map_csv_path,index=False,encoding='utf-8-sig')

    export_elapsed = (datetime.now() - start_time).total_seconds()
    print(f"[{timestamp()}]   ✓ Export completed in {export_elapsed:.1f} seconds")

    return df,output_path,map_csv_path


def show_statistics(df,upload_date,output_path,map_csv_path,total_elapsed):
    """Display detailed statistics about the export"""
    print()
    print("=" * 70)
    print(f"[{timestamp()}] ✓ Export completed successfully!")
    print("=" * 70)
    print(f"\nOutput files:")
    print(f"  1. {output_path}")
    print(f"  2. {map_csv_path} (for map)")

    print(f"\nSummary:")
    print(f"  - Total stores: {len(df):,}")
    print(f"  - Unique chains: {df['chainname'].nunique()}")
    print(f"  - Date: {upload_date}")

    # Price statistics
    print(f"\nPrice difference statistics:")
    print(f"  - Cheapest store: {df['average_price_diff'].min():.2f}% below average")
    print(f"  - Most expensive store: {df['average_price_diff'].max():.2f}% above average")
    print(f"  - Mean difference: {df['average_price_diff'].mean():.2f}%")
    print(f"  - Median difference: {df['average_price_diff'].median():.2f}%")

    # Item count statistics
    print(f"\nPopular items per store:")
    print(f"  - Minimum: {int(df['popular_item_count'].min())} items")
    print(f"  - Maximum: {int(df['popular_item_count'].max())} items")
    print(f"  - Average: {df['popular_item_count'].mean():.0f} items")
    print(f"  - Median: {df['popular_item_count'].median():.0f} items")

    # Top 5 cheapest stores
    print(f"\nTop 5 cheapest stores:")
    cheapest = df.nsmallest(5,'average_price_diff')
    for idx,row in cheapest.iterrows():
        print(f"  {row['store_name']:30} ({row['chainname']:15}, {row['city']:15}): "
              f"{row['average_price_diff']:+6.2f}% | {int(row['popular_item_count']):,} items")

    # Top 5 most expensive stores
    print(f"\nTop 5 most expensive stores:")
    expensive = df.nlargest(5,'average_price_diff')
    for idx,row in expensive.iterrows():
        print(f"  {row['store_name']:30} ({row['chainname']:15}, {row['city']:15}): "
              f"{row['average_price_diff']:+6.2f}% | {int(row['popular_item_count']):,} items")

    # Chain statistics
    print(f"\nStores by chain:")
    chain_counts = df['chainname'].value_counts()
    for chain,count in chain_counts.head(10).items():
        avg_diff = df[df['chainname'] == chain]['average_price_diff'].mean()
        print(f"  {chain:20}: {count:3,} stores | avg {avg_diff:+6.2f}%")

    print(f"\nTotal runtime: {total_elapsed / 60:.1f} minutes")
    print("=" * 70)


def interactive_mode():
    """Run in interactive mode"""
    print("\n" + "=" * 70)
    print("Update Store Comparisons and Export - Interactive Mode")
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

    # Ask about view update
    skip_view = input("\nSkip view update? (y/n) [n]: ").strip().lower() in ['y','yes']

    if not skip_view:
        # Get exclusions
        print(f"\nDefault excluded chains: {', '.join(DEFAULT_EXCLUDED_CHAINS)}")
        chains_input = input("Enter excluded chains (comma-separated) or press Enter for defaults: ").strip()
        excluded_chains = parse_list_input(chains_input) if chains_input else DEFAULT_EXCLUDED_CHAINS

        print(f"\nDefault excluded subchains: {', '.join(DEFAULT_EXCLUDED_SUBCHAINS)}")
        subchains_input = input("Enter excluded subchains (comma-separated) or press Enter for defaults: ").strip()
        excluded_subchains = parse_list_input(subchains_input) if subchains_input else DEFAULT_EXCLUDED_SUBCHAINS

        print(f"\nDefault excluded cities: {', '.join(DEFAULT_EXCLUDED_CITIES)}")
        cities_input = input("Enter excluded cities (comma-separated) or press Enter for defaults: ").strip()
        excluded_cities = parse_list_input(cities_input) if cities_input else DEFAULT_EXCLUDED_CITIES
    else:
        excluded_chains = []
        excluded_subchains = []
        excluded_cities = []

    return upload_date,excluded_chains,excluded_subchains,excluded_cities,skip_view


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Update store_price_comparisons view and export to CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --date 2025-11-02
  %(prog)s -d 2025-11-02 --exclude-chains "Yellow,דור אלון"
  %(prog)s -d 2025-11-02 --skip-view-update
  %(prog)s  (interactive mode)
        """
    )

    parser.add_argument('-d','--date',type=str,help='Upload date (YYYY-MM-DD)')
    parser.add_argument('--exclude-chains',type=str,help='Chains to exclude (comma-separated)')
    parser.add_argument('--exclude-subchains',type=str,help='Subchains to exclude (comma-separated)')
    parser.add_argument('--exclude-cities',type=str,help='Cities to exclude (comma-separated)')
    parser.add_argument('--skip-view-update',action='store_true',help='Skip view update, only export')
    parser.add_argument('--output-dir',type=str,help='Output directory for CSV')

    args = parser.parse_args()

    # Interactive mode if no date provided
    if args.date is None:
        upload_date,excluded_chains,excluded_subchains,excluded_cities,skip_view = interactive_mode()
    else:
        try:
            upload_date = validate_date(args.date)
        except ValueError as e:
            parser.error(str(e))

        excluded_chains = parse_list_input(args.exclude_chains) if args.exclude_chains else DEFAULT_EXCLUDED_CHAINS
        excluded_subchains = parse_list_input(
            args.exclude_subchains) if args.exclude_subchains else DEFAULT_EXCLUDED_SUBCHAINS
        excluded_cities = parse_list_input(args.exclude_cities) if args.exclude_cities else DEFAULT_EXCLUDED_CITIES
        skip_view = args.skip_view_update

    # Set output directory
    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR

    script_start = datetime.now()
    print("=" * 70)
    print(f"[{timestamp()}] Starting process for {upload_date}")
    print("=" * 70)
    print()

    try:
        # Connect to database
        print(f"[{timestamp()}] Connecting to PostgreSQL database...")
        conn = psycopg2.connect(**pg_config)
        print(f"[{timestamp()}]   ✓ Connected successfully!")
        print()

        # Step 1: Update view (unless skipped)
        if not skip_view:
            update_view(conn,upload_date,excluded_chains,excluded_subchains,excluded_cities)
        else:
            print(f"[{timestamp()}] Step 1: Skipping view update (using existing view)")

        # Step 2: Export to CSV
        df,output_path,map_csv_path = export_to_csv(conn,upload_date,output_dir)

        # Close connection
        conn.close()

        # Show statistics
        total_elapsed = (datetime.now() - script_start).total_seconds()
        show_statistics(df,upload_date,output_path,map_csv_path,total_elapsed)

    except Exception as e:
        print(f"\n[{timestamp()}] ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
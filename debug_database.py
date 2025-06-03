import psycopg2
from psycopg2.extras import RealDictCursor
import config


def debug_database():
    """
    Debug the database to understand why store_price_comparisons view returns no results
    """

    try:
        # Connect to PostgreSQL using config
        print("Connecting to PostgreSQL database...")
        pg_conn = psycopg2.connect(**config.pg_config)

        with pg_conn.cursor(cursor_factory=RealDictCursor) as pg_cursor:

            print("\n" + "=" * 60)
            print("1. Checking available upload dates in allprices table")
            print("=" * 60)

            pg_cursor.execute("""
                SELECT upload_date, COUNT(*) as record_count 
                FROM allprices 
                GROUP BY upload_date 
                ORDER BY upload_date DESC 
                LIMIT 10;
            """)

            dates = pg_cursor.fetchall()
            if dates:
                print("Available upload dates:")
                for date_row in dates:
                    print(f"  {date_row['upload_date']}: {date_row['record_count']:,} records")

                latest_date = dates[0]['upload_date']
                print(f"\nLatest date with data: {latest_date}")
            else:
                print("No data found in allprices table!")
                return

            print("\n" + "=" * 60)
            print("2. Checking all_stores table")
            print("=" * 60)

            pg_cursor.execute("SELECT COUNT(*) as store_count FROM all_stores;")
            store_count = pg_cursor.fetchone()['store_count']
            print(f"Total stores in all_stores: {store_count:,}")

            pg_cursor.execute("""
                SELECT chainname, COUNT(*) as store_count 
                FROM all_stores 
                GROUP BY chainname 
                ORDER BY store_count DESC 
                LIMIT 10;
            """)

            chains = pg_cursor.fetchall()
            print("\nTop chains by store count:")
            for chain in chains:
                print(f"  {chain['chainname']}: {chain['store_count']:,} stores")

            print("\n" + "=" * 60)
            print("3. Checking items_new table")
            print("=" * 60)

            pg_cursor.execute("SELECT COUNT(*) as item_count FROM items_new;")
            item_count = pg_cursor.fetchone()['item_count']
            print(f"Total items in items_new: {item_count:,}")

            print("\n" + "=" * 60)
            print(f"4. Testing with latest date: {latest_date}")
            print("=" * 60)

            # Test the popular_items CTE with latest date
            pg_cursor.execute(f"""
                WITH popular_items AS (
                    SELECT allprices.itemcode
                    FROM allprices
                    JOIN all_stores ON allprices.store_code = all_stores.store_code
                    WHERE allprices.upload_date = '{latest_date}' 
                        AND allprices.itemprice > 0 
                        AND allprices.itemprice IS NOT NULL 
                        AND (all_stores.chainname <> ALL (ARRAY['סופר פארם', 'Yellow', 'דור אלון'])) 
                        AND all_stores.subchainname <> 'Be' 
                        AND all_stores.subchainname <> 'אונליין'
                    GROUP BY allprices.itemcode
                    HAVING count(DISTINCT allprices.store_code) > 10
                )
                SELECT COUNT(*) as popular_item_count FROM popular_items;
            """)

            popular_count = pg_cursor.fetchone()['popular_item_count']
            print(f"Popular items (>10 stores) with latest date: {popular_count:,}")

            if popular_count == 0:
                print("\n⚠️  No popular items found! Let's check with lower threshold...")

                # Test with lower threshold
                pg_cursor.execute(f"""
                    WITH popular_items AS (
                        SELECT allprices.itemcode, count(DISTINCT allprices.store_code) as store_count
                        FROM allprices
                        JOIN all_stores ON allprices.store_code = all_stores.store_code
                        WHERE allprices.upload_date = '{latest_date}' 
                            AND allprices.itemprice > 0 
                            AND allprices.itemprice IS NOT NULL 
                            AND (all_stores.chainname <> ALL (ARRAY['סופר פארם', 'Yellow', 'דור אלון'])) 
                            AND all_stores.subchainname <> 'Be' 
                            AND all_stores.subchainname <> 'אונליין'
                        GROUP BY allprices.itemcode
                    )
                    SELECT 
                        COUNT(*) as total_items,
                        COUNT(CASE WHEN store_count >= 5 THEN 1 END) as items_5_plus_stores,
                        COUNT(CASE WHEN store_count >= 3 THEN 1 END) as items_3_plus_stores,
                        MAX(store_count) as max_stores_per_item
                    FROM popular_items;
                """)

                threshold_stats = pg_cursor.fetchone()
                print(f"Items with 5+ stores: {threshold_stats['items_5_plus_stores']:,}")
                print(f"Items with 3+ stores: {threshold_stats['items_3_plus_stores']:,}")
                print(f"Max stores per item: {threshold_stats['max_stores_per_item']}")

            print("\n" + "=" * 60)
            print("5. Testing store_price_comparisons view with latest date")
            print("=" * 60)

            # Update the view to use the latest date temporarily for testing
            test_query = f"""
                WITH store_item_price_diffs AS (
                    SELECT s.store_code,
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
                            WHEN pi.average_price > 0 THEN (p.itemprice - pi.average_price) / pi.average_price * 100
                            ELSE NULL
                        END AS price_diff_percent
                    FROM all_stores s
                    JOIN allprices p ON s.store_code = p.store_code
                    JOIN (
                        WITH popular_items AS (
                            SELECT allprices.itemcode
                            FROM allprices
                            JOIN all_stores ON allprices.store_code = all_stores.store_code
                            WHERE allprices.upload_date = '{latest_date}' 
                                AND allprices.itemprice > 0 
                                AND allprices.itemprice IS NOT NULL 
                                AND (all_stores.chainname <> ALL (ARRAY['סופר פארם', 'Yellow', 'דור אלון'])) 
                                AND all_stores.subchainname <> 'Be' 
                                AND all_stores.subchainname <> 'אונליין'
                            GROUP BY allprices.itemcode
                            HAVING count(DISTINCT allprices.store_code) > 5  -- Lower threshold for testing
                        )
                        SELECT i.itemcode, avg(p.itemprice) AS average_price
                        FROM popular_items pi
                        JOIN items_new i ON pi.itemcode = i.itemcode
                        JOIN allprices p ON i.itemcode = p.itemcode
                        JOIN all_stores s ON p.store_code = s.store_code
                        WHERE p.upload_date = '{latest_date}' 
                            AND p.itemprice > 0 
                            AND p.itemprice IS NOT NULL 
                            AND (s.chainname <> ALL (ARRAY['סופר פארם', 'Yellow', 'דור אלון'])) 
                            AND s.subchainname <> 'Be' 
                            AND s.subchainname <> 'אונליין'
                        GROUP BY i.itemcode
                    ) pi ON p.itemcode = pi.itemcode
                    WHERE p.upload_date = '{latest_date}' 
                        AND p.itemprice > 0 
                        AND p.itemprice IS NOT NULL 
                        AND (s.chainname <> ALL (ARRAY['סופר פארם', 'Yellow', 'דור אלון'])) 
                        AND s.subchainname <> 'Be' 
                        AND s.subchainname <> 'אונליין'
                )
                SELECT COUNT(*) as total_store_items 
                FROM store_item_price_diffs 
                WHERE price_diff_percent IS NOT NULL;
            """

            pg_cursor.execute(test_query)
            test_count = pg_cursor.fetchone()['total_store_items']
            print(f"Store-item combinations with valid price differences: {test_count:,}")

            if test_count > 0:
                print(f"\n✅ Success! Data found with date {latest_date} and lower threshold (5+ stores)")
                print(f"\nSuggested fix: Update your views to use '{latest_date}' instead of '2025-06-01'")
                print("And consider lowering the popular items threshold from 10 to 5 stores")
            else:
                print("\n❌ Still no data found. There might be other issues...")

        pg_conn.close()

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    debug_database()
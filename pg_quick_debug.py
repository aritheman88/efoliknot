import psycopg2
from psycopg2.extras import RealDictCursor
import config


def quick_debug():
    """
    Quick debug to find the specific issue with the views
    """

    try:
        print("Connecting to PostgreSQL database...")
        pg_conn = psycopg2.connect(**config.pg_config)

        with pg_conn.cursor(cursor_factory=RealDictCursor) as pg_cursor:

            print("\n1. Testing popular_items_avg_prices view directly...")
            pg_cursor.execute("SELECT COUNT(*) as count FROM popular_items_avg_prices LIMIT 1;")
            popular_view_count = pg_cursor.fetchone()['count']
            print(f"   popular_items_avg_prices has {popular_view_count:,} records")

            if popular_view_count == 0:
                print("\n❌ Problem: popular_items_avg_prices view is empty!")

                print("\n2. Testing the popular_items CTE separately...")
                pg_cursor.execute("""
                    WITH popular_items AS (
                        SELECT allprices.itemcode
                        FROM allprices
                        JOIN all_stores ON allprices.store_code = all_stores.store_code
                        WHERE allprices.upload_date = '2025-06-01'
                            AND allprices.itemprice > 0
                            AND allprices.itemprice IS NOT NULL
                            AND (all_stores.chainname <> ALL (ARRAY['סופר פארם', 'Yellow', 'דור אלון']))
                            AND all_stores.subchainname <> 'Be'
                            AND all_stores.subchainname <> 'אונליין'
                        GROUP BY allprices.itemcode
                        HAVING count(DISTINCT allprices.store_code) > 10
                    )
                    SELECT COUNT(*) as popular_count FROM popular_items;
                """)
                popular_cte_count = pg_cursor.fetchone()['popular_count']
                print(f"   Popular items CTE: {popular_cte_count:,} items")

                if popular_cte_count > 0:
                    print("\n3. Testing the JOIN with items_new...")
                    pg_cursor.execute("""
                        WITH popular_items AS (
                            SELECT allprices.itemcode
                            FROM allprices
                            JOIN all_stores ON allprices.store_code = all_stores.store_code
                            WHERE allprices.upload_date = '2025-06-01'
                                AND allprices.itemprice > 0
                                AND allprices.itemprice IS NOT NULL
                                AND (all_stores.chainname <> ALL (ARRAY['סופר פארם', 'Yellow', 'דור אלון']))
                                AND all_stores.subchainname <> 'Be'
                                AND all_stores.subchainname <> 'אונליין'
                            GROUP BY allprices.itemcode
                            HAVING count(DISTINCT allprices.store_code) > 10
                        )
                        SELECT COUNT(*) as join_count 
                        FROM popular_items pi
                        JOIN items_new i ON pi.itemcode = i.itemcode;
                    """)
                    join_count = pg_cursor.fetchone()['join_count']
                    print(f"   After JOIN with items_new: {join_count:,} items")
            else:
                print("✅ popular_items_avg_prices view is working!")

                print("\n2. Testing store_price_comparisons view...")
                try:
                    # Set a timeout for this query
                    pg_cursor.execute("SET statement_timeout = '30s';")
                    pg_cursor.execute("SELECT COUNT(*) as count FROM store_price_comparisons LIMIT 1;")
                    store_view_count = pg_cursor.fetchone()['count']
                    print(f"   store_price_comparisons has {store_view_count:,} records")

                    if store_view_count > 0:
                        print("✅ Both views are working!")

                        print("\n3. Testing a sample query...")
                        pg_cursor.execute("""
                            SELECT store_code, store_name, chainname, city, 
                                   average_price_diff, popular_item_count,
                                   latitude, longitude
                            FROM store_price_comparisons 
                            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                            LIMIT 5;
                        """)
                        sample_data = pg_cursor.fetchall()

                        print("Sample data:")
                        for row in sample_data:
                            print(f"   {row['store_name']} ({row['chainname']}) - {row['city']}")
                            print(
                                f"     Price diff: {row['average_price_diff']:.2f}%, Items: {row['popular_item_count']}")
                            print(f"     Coords: {row['latitude']}, {row['longitude']}")
                    else:
                        print("❌ store_price_comparisons view is empty!")

                except psycopg2.errors.QueryCanceled:
                    print("❌ store_price_comparisons view query timed out (>30s)")
                    print("   This suggests a performance issue in the view")
                except Exception as e:
                    print(f"❌ Error testing store_price_comparisons: {e}")

        pg_conn.close()

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    quick_debug()
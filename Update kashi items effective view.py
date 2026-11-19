#!/usr/bin/env python3
"""
Update Kashi Items Effective Prices Materialized View
=====================================================

Creates the kashi_items_avg_effective_prices MATERIALIZED VIEW: the national
average effective price of each Kashi (קאשי) item. It is the baseline of the
Kashi map (efoliknot.net/kashi).

Before this script, the view existed only in the database. This script reproduces
its definition (as of 2026-06-01, read from pg_matviews) with the item list moved
to kashi/kashi_items.csv. Edit that CSV to change the basket.

"Effective price" = LEAST(regular_price, promo_price_per_unit), only for the 8
chains that publish promos, and only for items sold in more than MIN_STORES stores.

Usage:
    python "Update kashi items effective view.py" 2026-11-15
    python "Update kashi items effective view.py" 2026-11-15 --dry-run   # print SQL only

Then run "Update and export stores kashi.py" (DROP ... CASCADE also drops the
store_kashi_price_comparisons view, which that script recreates) and
"Csv to geojson kashi.py".

Takes about 4 minutes.
"""

import sys
import time
from datetime import datetime
from pathlib import Path

import psycopg2

from config import pg_config

ITEMS_CSV = Path(__file__).parent / 'kashi' / 'kashi_items.csv'
PROMO_CHAINS = ['אושר עד', 'ויקטורי', 'טיב טעם', 'יוחננוף', 'מחסני השוק', 'קרפור', 'רמי לוי', 'שופרסל']
EXCLUDED_SUBCHAINS = ['Be', 'אונליין']
MIN_STORES = 10   # HAVING COUNT(DISTINCT store_code) > MIN_STORES


def load_items():
    lines = ITEMS_CSV.read_text(encoding='utf-8').split()
    if not lines or lines[0] != 'itemcode':
        raise SystemExit(f'{ITEMS_CSV} must have a single "itemcode" column')
    codes = list(dict.fromkeys(int(x) for x in lines[1:]))
    return codes


def build_matview_sql(upload_date, codes):
    codes_sql = ', '.join(str(c) for c in codes)
    chains_in = ', '.join(f"'{c}'" for c in PROMO_CHAINS)
    subchains_in = ', '.join(f"'{c}'" for c in EXCLUDED_SUBCHAINS)
    return f"""
    CREATE MATERIALIZED VIEW public.kashi_items_avg_effective_prices AS
    WITH target_items AS (
        SELECT unnest(ARRAY[{codes_sql}]::bigint[]) AS itemcode
    ),
    effective_store_prices AS (
        SELECT
            pr.store_code,
            pr.itemcode,
            LEAST(pr.itemprice, COALESCE(ap.discounted_price_per_unit::real, pr.itemprice)) AS effective_price
        FROM allprices pr
        JOIN target_items t ON t.itemcode = pr.itemcode
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
            AND s.city <> 'unknown'
    ),
    popular_items AS (
        SELECT itemcode
        FROM effective_store_prices
        GROUP BY itemcode
        HAVING COUNT(DISTINCT store_code) > {MIN_STORES}
    )
    SELECT
        i.itemcode,
        i.itemname,
        i.supplier,
        i.brand,
        i.category,
        AVG(esp.effective_price) AS average_price,
        '{upload_date}'::date    AS upload_date
    FROM popular_items pi
    JOIN effective_store_prices esp ON esp.itemcode = pi.itemcode
    JOIN items i                    ON i.itemcode   = pi.itemcode
    GROUP BY i.itemcode, i.itemname, i.supplier, i.brand, i.category
    WITH DATA;
    """


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry_run = '--dry-run' in sys.argv
    if len(args) != 1:
        raise SystemExit(__doc__)
    upload_date = args[0]
    datetime.strptime(upload_date, '%Y-%m-%d')

    codes = load_items()
    print(f'Kashi items in {ITEMS_CSV.name}: {len(codes):,}')
    drop_sql = 'DROP MATERIALIZED VIEW IF EXISTS public.kashi_items_avg_effective_prices CASCADE;'
    create_sql = build_matview_sql(upload_date, codes)
    if dry_run:
        print(drop_sql)
        print(create_sql)
        return

    conn = psycopg2.connect(**pg_config)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '900000';")
    t = time.time()
    cur.execute(drop_sql)
    cur.execute(create_sql)
    conn.commit()
    cur.execute('SELECT COUNT(*), MIN(upload_date) FROM public.kashi_items_avg_effective_prices')
    n, d = cur.fetchone()
    conn.close()
    print(f'kashi_items_avg_effective_prices: {n:,} items for {d} ({time.time() - t:.0f}s)')
    print('Next: "Update and export stores kashi.py", then "Csv to geojson kashi.py"')


if __name__ == '__main__':
    main()

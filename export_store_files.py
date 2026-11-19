"""
Export the per-store price tables behind "הצג טבלת מחירים" on the main map.

Usage:
    python export_store_files.py 2026-11-15

Run after update_popular_items_view.py and update_and_export_stores.py for the
same date: it reads the popular_items_avg_prices materialized view and the store
list in data/store_price_comparisons.csv.

Output (data/store_files/):
  _items.json        one shared dictionary of the popular items:
                     {"date", "fields", "items": {itemcode: [name, manufacturer, brand, category, avg]}}
  <store_code>.json  per store: metadata + "items": [[itemcode, price], ...]
                     (popular items only, i.e. the items the store grade is based on)

js/map.js joins the two into the table rows. Files of the old format (one big
"prices" list per store, May 2025) are removed.
"""
import json
import math
import sys
import time
from pathlib import Path

import pandas as pd
import psycopg2

from config import pg_config

OUT_DIR = Path(__file__).parent / 'data' / 'store_files'
STORES_CSV = Path(__file__).parent / 'data' / 'store_price_comparisons.csv'


def clean(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return v


def main(upload_date):
    t0 = time.time()
    conn = psycopg2.connect(**pg_config)
    cur = conn.cursor()

    cur.execute("select itemcode, itemname, supplier, brand, category, average_price, upload_date "
                "from popular_items_avg_prices")
    items = pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])
    view_date = str(items.upload_date.iloc[0])
    if view_date != upload_date:
        sys.exit(f'popular_items_avg_prices is for {view_date}, not {upload_date}: run update_popular_items_view.py first')
    print(f'{len(items):,} popular items')

    stores = pd.read_csv(STORES_CSV, encoding='utf-8-sig')
    stores = stores[stores.latitude.notna() & stores.longitude.notna()]
    print(f'{len(stores):,} stores on the map')

    # one pass over the date's prices, restricted to popular items
    cur.execute("""
        select p.store_code, p.itemcode, min(p.itemprice)
        from allprices p
        join popular_items_avg_prices pi on pi.itemcode = p.itemcode
        where p.upload_date = %s and p.itemprice > 0
        group by 1, 2""", (upload_date,))
    prices = pd.DataFrame(cur.fetchall(), columns=['store_code', 'itemcode', 'price'])
    conn.close()
    prices = prices[prices.store_code.isin(stores.store_code)]
    print(f'{len(prices):,} store-item prices ({time.time() - t0:.0f}s)')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    old = {p.name for p in OUT_DIR.glob('*.json')}

    used = set(prices.itemcode.unique())
    it = items[items.itemcode.isin(used)]
    shared = {
        'date': upload_date,
        'fields': ['itemname', 'manufacturer', 'brand', 'category', 'average_price'],
        'items': {str(int(r.itemcode)): [clean(r.itemname), clean(r.supplier), clean(r.brand), clean(r.category),
                                         round(float(r.average_price), 2)]
                  for r in it.itertuples()},
    }
    (OUT_DIR / '_items.json').write_text(json.dumps(shared, ensure_ascii=False, separators=(',', ':')),
                                         encoding='utf-8')

    written = {'_items.json'}
    by_store = dict(tuple(prices.groupby('store_code')))
    for s in stores.itertuples():
        g = by_store.get(s.store_code)
        if g is None:
            continue
        doc = {
            'store_code': s.store_code,
            'store_name': clean(s.store_name),
            'chainname': clean(s.chainname),
            'subchainname': clean(s.subchainname),
            'city': clean(s.city),
            'latitude': clean(s.latitude),
            'longitude': clean(s.longitude),
            'average_price_diff': round(float(s.average_price_diff), 2),
            'item_count': len(g),
            'date': upload_date,
            'items': [[int(c), round(float(p), 2)] for c, p in zip(g.itemcode, g.price)],
        }
        name = f'{s.store_code}.json'
        (OUT_DIR / name).write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        written.add(name)

    for name in old - written:
        (OUT_DIR / name).unlink()
    size = sum(p.stat().st_size for p in OUT_DIR.glob('*.json')) / 1e6
    print(f'Wrote {len(written) - 1:,} store files + _items.json ({size:.0f} MB), '
          f'removed {len(old - written)} old files, {time.time() - t0:.0f}s')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])

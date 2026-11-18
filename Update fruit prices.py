#!/usr/bin/env python3
"""
Update fruit prices (efoliknot.net/fruit)
==========================================

Builds fruit/data/fruit_prices.json + fruit/data/fruit_prices.csv: the effective
price per kg of five seasonal fruits in every store of the 8 chains with promo data.

Fruit choice (2026-11-15): fruits whose store coverage rose most from August to
November and that are carried by most stores: persimmon, clementine, pomegranate,
pomelit, grapefruit. Edit FRUITS to change the list.

Method
------
* Item names come from each chain's own PriceFull XML (raw download folder), NOT
  from the items table: produce uses short internal codes that collide across
  chains, and items keeps one name per code (e.g. Yohananof 608 = persimmon).
* Only weighed items (bIsWeighted=1), so itemprice is per kg. Organic, packed,
  dried, peeled and juice items are excluded.
* Effective price = min(regular, cheapest open general promo): club_id=0, not a
  coupon, start <= date <= end, discounted_price / min_qty, >= 30% of regular.
* A store's price for a fruit = its cheapest matching item.
* Excluded: Be, online stores, Eilat (VAT-free), stores without coordinates.
  Regular prices outside [1/3, 3] x the fruit median are dropped.

Usage:
    python "Update fruit prices.py" 2026-11-15
"""

import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import psycopg2

from config import pg_config

RAW_DIR = r"C:\Users\Ariel\OneDrive - Lobby 99\Desktop\Kimonaim"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fruit', 'data')

CHAIN_FOLDERS = {
    'yohananof': 'יוחננוף', 'osherAd': 'אושר עד', 'ramilevi': 'רמי לוי', 'shufersal': 'שופרסל',
    'victory': 'ויקטורי', 'carrefour': 'קרפור', 'tivTaam': 'טיב טעם', 'mahsaneiHashuk': 'מחסני השוק',
}
FRUITS = {  # key: (Hebrew label, emoji, include regex on the chain's own name, exclude regex)
    'persimmon':   ('אפרסמון',  '🟠', r'^אפרסמון',            r'אורגני|ארוז|מיובש|יבש|סלט'),
    'clementine':  ('קלמנטינה', '🍊', r'^(?:קלמנטינ|מנדרינ)', r'אורגני|ארוז|מיובש|מיץ|סחוט'),
    'pomegranate': ('רימון',    '🔴', r'^רימון',              r'אורגני|ארוז|מקולף|גרעיני|פרוס|מיץ'),
    'pomelit':     ('פומלית',   '🟢', r'^פומלית',             r'אורגני|ארוז'),
    'grapefruit':  ('אשכולית',  '🟡', r'^אשכולית',            r'אורגני|ארוז|מיץ'),
}
EXCLUDED_SUBCHAINS = ['Be', 'אונליין']
FILES_PER_CHAIN = 25   # spread sample of store files; produce codes are chain-wide


def chain_names(date):
    """itemcode -> name per chain, for weighed fruit items, from raw PriceFull XML."""
    pat = re.compile('|'.join(f[2] for f in FRUITS.values()))
    rows = []
    for folder, chain in CHAIN_FOLDERS.items():
        files = sorted(glob.glob(os.path.join(RAW_DIR, folder, date, 'PriceFull*.xml')))
        if not files:
            print(f'  !! no PriceFull files for {folder} on {date}')
        for f in files[::max(1, len(files) // FILES_PER_CHAIN)]:
            try:
                for _, el in ET.iterparse(f):
                    kids = {c.tag.lower(): (c.text or '').strip() for c in el}
                    if 'itemcode' in kids and ('itemname' in kids or 'itemnm' in kids):
                        name = re.sub(r'\s+', ' ', kids.get('itemname') or kids.get('itemnm') or '').strip()
                        code = re.sub(r'\D', '', kids['itemcode'])
                        if code and kids.get('bisweighted') == '1' and pat.search(name):
                            rows.append((chain, int(code), name))
                        el.clear()
            except ET.ParseError as e:
                print(f'  parse error {os.path.basename(f)}: {e}')
    df = pd.DataFrame(rows, columns=['chainname', 'itemcode', 'itemname']).drop_duplicates(['chainname', 'itemcode'])
    df['fruit'] = None
    for key, (_, _, inc, exc) in FRUITS.items():
        m = df.itemname.str.contains(inc) & ~df.itemname.str.contains(exc) & df.fruit.isna()
        df.loc[m, 'fruit'] = key
    return df[df.fruit.notna()]


def fetch(cur, sql):
    cur.execute(sql)
    return pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])


def build(date):
    names = chain_names(date)
    print(f'Matched {len(names)} chain items:', names.groupby('chainname').size().to_dict())
    codes = ','.join(str(c) for c in sorted(names.itemcode.unique()))
    chains = ','.join(f"'{c}'" for c in CHAIN_FOLDERS.values())

    conn = psycopg2.connect(**pg_config)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '900000'")
    stores = fetch(cur, f"""select store_code, chainname, subchainname, storename, address, city, latitude, longitude
                            from all_stores where chainname in ({chains})""")
    # literal date, no join: fast path on the allpromos / allprices pkeys
    prices = fetch(cur, f"""select store_code, itemcode, itemprice from allprices
                            where upload_date = '{date}' and itemcode in ({codes}) and itemprice > 0""")
    promos = fetch(cur, f"""select store_code, itemcode, discounted_price, min_qty from allpromos
                            where upload_date = '{date}' and itemcode in ({codes})
                              and club_id = 0 and not coalesce(is_coupon, false)
                              and promotion_start_date <= '{date}' and promotion_end_date >= '{date}'
                              and discounted_price is not null""")
    conn.close()

    stores = stores[~stores.subchainname.isin(EXCLUDED_SUBCHAINS) & (stores.city != 'unknown')
                    & ~stores.city.fillna('').str.contains('אילת') & stores.latitude.notna()]
    p = prices.merge(stores).merge(names, on=['chainname', 'itemcode'])
    p['itemprice'] = p.itemprice.astype(float).round(2)

    promos['pp'] = promos.discounted_price.astype(float) / promos.min_qty.astype(float).clip(lower=1)
    promos = promos.sort_values('pp').drop_duplicates(['store_code', 'itemcode'])
    p = p.merge(promos, how='left', on=['store_code', 'itemcode'])
    ok = p.pp.notna() & (p.pp < p.itemprice) & (p.pp >= 0.3 * p.itemprice)
    p['eff'] = np.where(ok, p.pp, p.itemprice).round(2)
    p['promo'] = ''
    p.loc[ok, 'promo'] = [
        f'{q:g} ק"ג ב-{d:.2f} ₪' if q > 1 else f'מבצע: {d:.2f} ₪ לק"ג'
        for q, d in zip(p.loc[ok, 'min_qty'].astype(float), p.loc[ok, 'discounted_price'].astype(float))]

    med = p.groupby('fruit').itemprice.transform('median')
    out = ~(p.itemprice / med).between(1 / 3, 3)
    print(f'Dropped {out.sum()} outlier rows of {len(p)}')
    p = p[~out]

    best = p.sort_values(['eff', 'itemprice']).drop_duplicates(['store_code', 'fruit'])
    return best, stores


def write(best, date):
    os.makedirs(OUT_DIR, exist_ok=True)
    summary = {}
    for fruit, g in best.groupby('fruit'):
        rows = []
        for chain, c in g.groupby('chainname'):
            cheapest = c.sort_values(['eff', 'itemprice']).iloc[0]
            n_min = int((c.eff == cheapest.eff).sum())
            rows.append({
                'chain': chain, 'stores': int(c.store_code.nunique()),
                'min': float(cheapest.eff), 'median': round(float(c.eff.median()), 2),
                'regMedian': round(float(c.itemprice.median()), 2),
                'promoShare': round(float((c.promo != '').mean()), 3),
                'minStore': cheapest.storename, 'minCity': cheapest.city, 'minItem': cheapest.itemname,
                'minPromo': cheapest.promo, 'minStoresCount': n_min,
            })
        summary[fruit] = sorted(rows, key=lambda r: (r['min'], r['median']))

    st = best.drop_duplicates('store_code').set_index('store_code')
    stores_out = []
    for code, g in best.groupby('store_code'):
        s = st.loc[code]
        stores_out.append({
            'id': code, 'name': s.storename, 'chain': s.chainname, 'sub': s.subchainname,
            'city': s.city, 'addr': s.address, 'lat': round(float(s.latitude), 6), 'lon': round(float(s.longitude), 6),
            'p': {r.fruit: [float(r.eff), float(r.itemprice), r.itemname, r.promo] for r in g.itertuples()},
        })
    data = {
        'date': date,
        'fruits': [{'key': k, 'label': v[0], 'icon': v[1]} for k, v in FRUITS.items()],
        'chains': list(CHAIN_FOLDERS.values()),
        'summary': summary,
        'stores': stores_out,
    }
    with open(os.path.join(OUT_DIR, 'fruit_prices.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    labels = {k: v[0] for k, v in FRUITS.items()}
    csv = best.assign(fruit_he=best.fruit.map(labels))[
        ['fruit_he', 'chainname', 'subchainname', 'storename', 'city', 'address', 'itemcode', 'itemname',
         'itemprice', 'eff', 'promo']]
    csv.columns = ['פרי', 'רשת', 'תת-רשת', 'סניף', 'עיר', 'כתובת', 'קוד פריט', 'שם פריט',
                   'מחיר רגיל לק"ג', 'מחיר אפקטיבי לק"ג', 'מבצע']
    csv.sort_values(['פרי', 'מחיר אפקטיבי לק"ג']).to_csv(
        os.path.join(OUT_DIR, 'fruit_prices.csv'), index=False, encoding='utf-8-sig')
    print(f'Wrote {len(stores_out)} stores to {OUT_DIR}')
    for fruit, rows in summary.items():
        print(f'  {labels[fruit]}: ' + ', '.join(f"{r['chain']} {r['min']:.2f}/{r['median']:.2f}" for r in rows))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('usage: python "Update fruit prices.py" YYYY-MM-DD')
    d = sys.argv[1]
    best, _ = build(d)
    write(best, d)

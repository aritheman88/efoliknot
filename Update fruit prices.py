#!/usr/bin/env python3
"""
Update fruit prices (efoliknot.net/fruit)
==========================================

Builds fruit/data/fruit_prices.json + fruit/data/fruit_prices.csv: the effective
price per kg of 11 fruits in every store of the 8 chains with promo data.

Fruit choice (2026-11-18):
* requested: strawberries, grapes, watermelon, kiwi, banana, avocado;
* seasonal: the fruits whose store coverage rose most from August to November and
  that most stores carry: persimmon, clementine, pomegranate, pomelit, grapefruit.
Edit FRUITS to change the list.

Method
------
* Item names come from each chain's own PriceFull XML (raw download folder), NOT
  from the items table: produce uses short internal codes that collide across
  chains, and items keeps one name per code (e.g. Yohananof 608 = persimmon).
* Weighed items (bIsWeighted=1, itemprice is per kg), plus packs whose weight is
  written in the chain's item name ("תות שדה 500 גרם"): price / weight. Strawberries
  are mostly sold in packs. Organic, frozen, dried, peeled, juice and non-food
  items are excluded. A barcode counts as frozen if any chain's name or the items
  category says so (some chains drop "קפוא" from the name).
* Effective price = min(regular, cheapest open general promo): club_id=0, not a
  coupon, start <= date <= end, discounted_price / min_qty, >= 30% of regular.
* A store's price for a fruit = its cheapest matching item.
* Excluded: Be, online stores, Eilat (VAT-free), stores without coordinates.
  Regular prices outside [1/3, 3] x both the store-row median and the median of item medians are dropped.

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
PACK_WEIGHTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fruit', 'pack_weights.csv')

CHAIN_FOLDERS = {
    'yohananof': 'יוחננוף', 'osherAd': 'אושר עד', 'ramilevi': 'רמי לוי', 'shufersal': 'שופרסל',
    'victory': 'ויקטורי', 'carrefour': 'קרפור', 'tivTaam': 'טיב טעם', 'mahsaneiHashuk': 'מחסני השוק',
}
FRUITS = {  # key: (Hebrew label, group, include regex on the chain's own name, exclude regex)
    'strawberry':  ('תותים',    'req', r'^(?:תות שדה|תותים|תות(?= |$))',
                    r'שוקולד|מצופ|מיובש|מסוכר|אפגני|חמוץ|סגול|קריץ|מוברק|פרוטי|אייס|עץ|מ"?ל\b|%|Muller|דנונה|קריסטל|ליטר|אורגני'),
    'grapes':      ('ענבים',    'req', r'^ענב(?:ים)?(?=[ .]|$)',     r'שוקולד|אורגני|מיץ|(?:^| )קר(?= |$)|עלי'),
    'watermelon':  ('אבטיח',    'req', r'^אבטיח',                    r'מסוכר|מוברק|קריץ|חמוץ|מ"?ל\b|קרחונים|מיץ|חתוך|קוביות'),
    'kiwi':        ('קיווי',    'req', r'^קיווי',                    r'נעל|משח|נוזל|ספוג|מיובש|מסוכר|Muller|אורגני|קופסא|ניקוי|בישום|הגנת'),
    'banana':      ('בננה',     'req', r'^בננ(?:ה|ות)(?=[ .]|$)',    r'צ.?יפס|ציפס|מסוכר|מיובש|שוקולד|מצופ|ליטר|מ"ל|פקק|אורגני'),
    'avocado':     ('אבוקדו',   'req', r'^אבוקדו',                   r'ממרח|מחית|גוואק|אורגני|סלט'),
    'persimmon':   ('אפרסמון',  'season', r'^אפרסמון',               r'אורגני|מיובש|יבש|סלט'),
    'clementine':  ('קלמנטינה', 'season', r'^(?:קלמנטינ|מנדרינ)',    r'אורגני|מיובש|מיץ|סחוט'),
    'pomegranate': ('רימון',    'season', r'^רימון',                 r'אורגני|מקולף|גרעיני|פרוס|מיץ'),
    'pomelit':     ('פומלית',   'season', r'^פומלית',                r'אורגני'),
    'grapefruit':  ('אשכולית',  'season', r'^אשכולית',               r'אורגני|מיץ'),
}
FROZEN = 'קפוא|מוקפא'
# frozen products whose name in some chains drops the word (checked in the online catalogue)
FROZEN_CODES = {7290013424976}   # Alpha Frost "תות שדה שלם" 500 g (Mahsanei Hashuk)
WEIGHT_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(ק"?ג|קילו|גרם|גר|ג(?=[\s\'`-]|$))')
EXCLUDED_SUBCHAINS = ['Be', 'אונליין']
FILES_PER_CHAIN = 25   # spread sample of store files; produce codes are chain-wide


def pack_kg(name):
    """Pack weight in kg from the item name, or None."""
    m = WEIGHT_RE.search(name)
    if not m:
        return None
    v = float(m.group(1))
    kg = v if m.group(2).startswith('ק') else v / 1000
    return kg if 0.1 <= kg <= 5 else None


def chain_names(date):
    """itemcode -> name per chain for fruit items (weighed, or with a pack weight), from raw PriceFull XML."""
    pat = re.compile('|'.join(f[2] for f in FRUITS.values()))
    frozen_codes = set(FROZEN_CODES)
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
                        if code and pat.search(name):
                            if re.search(FROZEN, name):
                                frozen_codes.add(int(code))
                            rows.append((chain, int(code), name, kids.get('bisweighted') == '1'))
                        el.clear()
            except ET.ParseError as e:
                print(f'  parse error {os.path.basename(f)}: {e}')
    df = pd.DataFrame(rows, columns=['chainname', 'itemcode', 'itemname', 'weighed']).drop_duplicates(['chainname', 'itemcode'])
    # a barcode named frozen in any chain is frozen everywhere (long barcodes only: short codes collide)
    df = df[~(df.itemcode.isin(frozen_codes) & (df.itemcode >= 10**8)) & ~df.itemname.str.contains(FROZEN)]
    df['kg'] = pd.Series([1.0 if w else pack_kg(n) for w, n in zip(df.weighed, df.itemname)], index=df.index, dtype=object)
    # packs with no weight in the name: weights looked up online (fruit/pack_weights.csv, with sources)
    pw = pd.read_csv(PACK_WEIGHTS, dtype={'chainname': str}).fillna({'chainname': ''})
    by_chain = {(r.chainname, int(r.itemcode)): r.grams / 1000 for r in pw.itertuples() if r.chainname}
    by_code = {int(r.itemcode): r.grams / 1000 for r in pw.itertuples() if not r.chainname}
    miss = df.kg.isna()
    df.loc[miss, 'kg'] = [by_chain.get((c, i), by_code.get(i)) for c, i in zip(df.chainname[miss], df.itemcode[miss])]
    df['kg'] = pd.to_numeric(df.kg)
    df = df[df.kg.notna()]
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
    frozen = fetch(cur, f"""select itemcode from items where itemcode in ({codes}) and itemcode >= 100000000
                            and (category ~ '{FROZEN}' or department ~ '{FROZEN}')""")
    # full barcodes the catalog files outside produce (e.g. a chain naming caviar spread "תות שדה")
    other = fetch(cur, f"""select itemcode from items where itemcode in ({codes}) and itemcode >= 100000000
                           and department is not null and department <> 'ירקות ופירות'""")
    names = names[~names.itemcode.isin(frozen.itemcode) & ~names.itemcode.isin(other.itemcode)]
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
    p['packprice'] = p.itemprice.astype(float).round(2)
    p['itemprice'] = (p.packprice / p.kg).round(2)          # per kg

    promos['pp'] = promos.discounted_price.astype(float) / promos.min_qty.astype(float).clip(lower=1)
    promos = promos.sort_values('pp').drop_duplicates(['store_code', 'itemcode'])
    p = p.merge(promos, how='left', on=['store_code', 'itemcode'])
    p['pp'] = p.pp / p.kg
    ok = p.pp.notna() & (p.pp < p.itemprice) & (p.pp >= 0.3 * p.itemprice)
    p['eff'] = np.where(ok, p.pp, p.itemprice).round(2)
    p['promo'] = ''
    p.loc[ok, 'promo'] = [
        (f'{q:g} ק"ג ב-{d:.2f} ₪' if q > 1 else f'מבצע: {d:.2f} ₪ לק"ג') if w else
        (f'{q:g} מארזים ב-{d:.2f} ₪' if q > 1 else f'מבצע: {d:.2f} ₪ למארז')
        for q, d, w in zip(p.loc[ok, 'min_qty'].astype(float), p.loc[ok, 'discounted_price'].astype(float),
                           p.loc[ok, 'weighed'])]
    p['label'] = [n if w else f'{n} (מארז ב-{pp:.2f} ₪)' for n, w, pp in zip(p.itemname, p.weighed, p.packprice)]

    # A price is kept if it is within [1/3, 3] of the store-row median OR of the median of item medians.
    # The second reference stops one item sold in many stores (Shufersal's 250 g strawberry box,
    # ₪160/kg in 134 stores) from pushing out genuine loose prices (₪35/kg); the first stops many
    # box items from pushing out cheap loose fruit (avocado).
    item_med = p.groupby(['fruit', 'chainname', 'itemcode']).itemprice.median()
    row_med = p.groupby('fruit').itemprice.transform('median')
    itm_med = p.fruit.map(item_med.groupby('fruit').median())
    out = ~((p.itemprice / row_med).between(1 / 3, 3) | (p.itemprice / itm_med).between(1 / 3, 3))
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
                'minStore': cheapest.storename, 'minCity': cheapest.city, 'minItem': cheapest.label,
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
            'p': {r.fruit: [float(r.eff), float(r.itemprice), r.label, r.promo] for r in g.itertuples()},
        })
    data = {
        'date': date,
        'fruits': [{'key': k, 'label': v[0], 'group': v[1]} for k, v in FRUITS.items()],
        'chains': list(CHAIN_FOLDERS.values()),
        'summary': summary,
        'stores': stores_out,
    }
    with open(os.path.join(OUT_DIR, 'fruit_prices.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    labels = {k: v[0] for k, v in FRUITS.items()}
    csv = best.assign(fruit_he=best.fruit.map(labels))[
        ['fruit_he', 'chainname', 'subchainname', 'storename', 'city', 'address', 'itemcode', 'label',
         'itemprice', 'eff', 'promo']]
    csv.columns = ['פרי', 'רשת', 'תת-רשת', 'סניף', 'עיר', 'כתובת', 'קוד פריט', 'שם פריט',
                   'מחיר רגיל לק"ג', 'מחיר אפקטיבי לק"ג', 'מבצע']
    csv.sort_values(['פרי', 'מחיר אפקטיבי לק"ג']).to_csv(
        os.path.join(OUT_DIR, 'fruit_prices.csv'), index=False, encoding='utf-8-sig')
    print(f'Wrote {len(stores_out)} stores to {OUT_DIR}')
    for fruit in FRUITS:
        rows = summary.get(fruit, [])
        print(f'  {labels[fruit]}: ' + ', '.join(f"{r['chain']} {r['min']:.2f}/{r['median']:.2f}" for r in rows))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('usage: python "Update fruit prices.py" YYYY-MM-DD')
    d = sys.argv[1]
    best, _ = build(d)
    write(best, d)

#!/usr/bin/env python3
"""
Israel Grocery Store Fetcher
=============================

Fetches grocery/supermarket locations across Israel from:
1. OpenStreetMap Overpass API (primary - free, comprehensive)
2. Nominatim reverse geocoding for missing addresses (free, rate-limited)

Output: israel_grocery_stores.csv with columns:
    source, osm_id, store_name, chainname, address, city,
    latitude, longitude, store_type, phone, website

Usage:
    python fetch_grocery_stores.py

Requirements:
    pip install requests pandas

Author: efoliknot team
Last Updated: 2026-05-05
"""

import requests
import pandas as pd
import json
import time
import re
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent / 'israel_grocery_stores.csv'
CHECKPOINT_FILE = Path(__file__).parent / 'grocery_stores_checkpoint.json'

PRIMARY_URL = "https://overpass-api.de/api/interpreter"
MIRROR_URL = "https://overpass.kumi.systems/api/interpreter"

# Israel bounding box (south, west, north, east)
ISRAEL_BBOX = (29.4, 34.2, 33.4, 35.9)

# OSM shop types to fetch
SHOP_TYPES = [
    'supermarket',
    'convenience',
    'grocery',
    'general',
    'food',
    'mini_market',
]

# Known chain name mappings from OSM name variants → clean Hebrew name
CHAIN_MAP = {
    'shufersal': 'שופרסל',
    'שופרסל': 'שופרסל',
    'rami levy': 'רמי לוי',
    'רמי לוי': 'רמי לוי',
    'victory': 'ויקטורי',
    'ויקטורי': 'ויקטורי',
    'yohananof': 'יוחננוף',
    'יוחננוף': 'יוחננוף',
    'carrefour': 'קרפור',
    'קרפור': 'קרפור',
    'tiv taam': 'טיב טעם',
    'טיב טעם': 'טיב טעם',
    'osher ad': 'אושר עד',
    'אושר עד': 'אושר עד',
    'mahsanei hashuk': 'מחסני השוק',
    'מחסני השוק': 'מחסני השוק',
    'yeinot bitan': 'יינות ביתן',
    'יינות ביתן': 'יינות ביתן',
    'hazi hinam': 'חצי חינם',
    'חצי חינם': 'חצי חינם',
    'stop market': 'סטופ מרקט',
    'am:pm': 'ampm',
    'am-pm': 'ampm',
    'ampm': 'ampm',
    'zol vbgadol': 'זול ובגדול',
    'זול ובגדול': 'זול ובגדול',
    'maayan 2000': 'מעיין 2000',
    'מעיין 2000': 'מעיין 2000',
    'nativ hahesed': 'נתיב החסד',
    'נתיב החסד': 'נתיב החסד',
}


def overpass_query(shop_type):
    """Build Overpass QL query for a given shop type within Israel."""
    south, west, north, east = ISRAEL_BBOX
    bbox = f"{south},{west},{north},{east}"
    return f"""
    [out:json][timeout:180];
    (
      node["shop"="{shop_type}"]({bbox});
      way["shop"="{shop_type}"]({bbox});
      relation["shop"="{shop_type}"]({bbox});
    );
    out center tags;
    """


def fetch_overpass(shop_type, retries=10):
    """Fetch OSM data for a shop type via Overpass API with exponential backoff and mirror fallback.

    Returns a list of elements on success (may be empty), or None if all retries fail.
    Switches from PRIMARY_URL to MIRROR_URL after 2 consecutive primary failures.
    """
    query = overpass_query(shop_type)
    consecutive_primary_failures = 0

    for attempt in range(retries):
        use_mirror = consecutive_primary_failures >= 2
        url = MIRROR_URL if use_mirror else PRIMARY_URL
        endpoint_label = "mirror" if use_mirror else "primary"

        try:
            print(f"  Fetching '{shop_type}' (attempt {attempt + 1}/{retries}, {endpoint_label})...")
            response = requests.post(
                url,
                data={'data': query},
                timeout=180,
                headers={'User-Agent': 'efoliknot-store-fetcher/1.0 (lobby99.org.il)'}
            )
            response.raise_for_status()
            data = response.json()
            elements = data.get('elements', [])
            print(f"  → {len(elements):,} elements found")
            return elements
        except requests.exceptions.RequestException as e:
            if not use_mirror:
                consecutive_primary_failures += 1
            wait = min(10 * (2 ** attempt), 120)
            print(f"  {type(e).__name__} on attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                print(f"  Waiting {wait}s before retry...")
                time.sleep(wait)

    print(f"  Failed to fetch '{shop_type}' after {retries} attempts")
    return None


def load_checkpoint():
    """Load previously saved per-shop-type elements from checkpoint file."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_checkpoint(checkpoint):
    """Persist checkpoint data so a crashed run can resume."""
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump(checkpoint, f, ensure_ascii=False)


def extract_coords(element):
    """Extract lat/lon from a node, way, or relation element."""
    if element['type'] == 'node':
        return element.get('lat'), element.get('lon')
    elif 'center' in element:
        return element['center'].get('lat'), element['center'].get('lon')
    return None, None


def extract_address(tags):
    """
    Build a clean address string and city from OSM tags.
    OSM uses addr:street, addr:housenumber, addr:city.
    """
    street = tags.get('addr:street', '')
    housenumber = tags.get('addr:housenumber', '')
    city = tags.get('addr:city', '') or tags.get('addr:suburb', '') or tags.get('is_in:city', '')

    address_parts = []
    if street:
        address_parts.append(street)
    if housenumber:
        address_parts.append(housenumber)

    address = ' '.join(address_parts).strip()
    return address, city


def guess_chain(name):
    """Try to match a store name to a known chain."""
    if not name:
        return ''
    name_lower = name.lower().strip()
    for key, chain in CHAIN_MAP.items():
        if key in name_lower:
            return chain
    return ''


def parse_element(element, shop_type):
    """Parse a single OSM element into a store dict."""
    tags = element.get('tags', {})
    lat, lon = extract_coords(element)

    if lat is None or lon is None:
        return None

    name = (
        tags.get('name') or
        tags.get('name:he') or
        tags.get('brand') or
        tags.get('operator') or
        ''
    )

    address, city = extract_address(tags)

    # Try brand tag first for chain detection, then name
    brand = tags.get('brand', '') or tags.get('operator', '')
    chainname = guess_chain(brand) or guess_chain(name)

    return {
        'source': 'OpenStreetMap',
        'osm_id': f"{element['type'][0]}{element['id']}",
        'store_name': name,
        'chainname': chainname,
        'address': address,
        'city': city,
        'latitude': lat,
        'longitude': lon,
        'store_type': shop_type,
        'phone': tags.get('phone', '') or tags.get('contact:phone', ''),
        'website': tags.get('website', '') or tags.get('contact:website', ''),
    }


def deduplicate(df):
    """
    Remove duplicate stores.
    Priority: prefer rows with more complete data (name + address + city).
    """
    print(f"\nDeduplicating {len(df):,} records...")

    # Score completeness
    df['_score'] = (
        (df['store_name'] != '').astype(int) +
        (df['address'] != '').astype(int) +
        (df['city'] != '').astype(int)
    )

    # Drop exact OSM ID duplicates (same element fetched under multiple shop types)
    df = df.sort_values('_score', ascending=False).drop_duplicates(subset=['osm_id'])

    # Drop near-duplicates by coordinates (within ~10m)
    df['lat_r'] = df['latitude'].round(4)
    df['lon_r'] = df['longitude'].round(4)
    df = df.drop_duplicates(subset=['lat_r', 'lon_r', 'store_name'])

    df = df.drop(columns=['_score', 'lat_r', 'lon_r'])
    print(f"After deduplication: {len(df):,} records")
    return df


def main():
    print("=" * 60)
    print("Israel Grocery Store Fetcher")
    print("=" * 60)
    print(f"Bounding box: {ISRAEL_BBOX}")
    print(f"Shop types: {', '.join(SHOP_TYPES)}")
    print()

    checkpoint = load_checkpoint()
    if checkpoint:
        print(f"Resuming from checkpoint — already fetched: {', '.join(checkpoint.keys())}")
    print()

    all_elements = []
    seen_ids = set()

    for shop_type in SHOP_TYPES:
        if shop_type in checkpoint:
            print(f"  Skipping '{shop_type}' (checkpoint: {len(checkpoint[shop_type]):,} elements)")
            elements = checkpoint[shop_type]
        else:
            elements = fetch_overpass(shop_type)
            if elements is None:
                print(f"  Warning: '{shop_type}' could not be fetched — skipping")
                elements = []
            else:
                checkpoint[shop_type] = elements
                save_checkpoint(checkpoint)
                print(f"  Checkpoint saved ({shop_type} complete)")
            # Be polite to the Overpass API
            time.sleep(3)

        for el in elements:
            uid = f"{el['type'][0]}{el['id']}"
            if uid not in seen_ids:
                seen_ids.add(uid)
                all_elements.append((el, shop_type))

    print(f"\nTotal unique OSM elements: {len(all_elements):,}")
    print("Parsing elements...")

    rows = []
    for element, shop_type in all_elements:
        row = parse_element(element, shop_type)
        if row:
            rows.append(row)

    print(f"Parsed: {len(rows):,} stores with valid coordinates")

    df = pd.DataFrame(rows)
    df = deduplicate(df)

    # Sort by city then store name
    df = df.sort_values(['city', 'store_name'], na_position='last')

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Final store count: {len(df):,}")
    print(f"\nBy store type:")
    for stype, count in df['store_type'].value_counts().items():
        print(f"  {stype:20}: {count:,}")
    print(f"\nBy identified chain (top 15):")
    chain_counts = df[df['chainname'] != '']['chainname'].value_counts()
    for chain, count in chain_counts.head(15).items():
        print(f"  {chain:20}: {count:,}")
    print(f"\nStores with name:    {(df['store_name'] != '').sum():,}")
    print(f"Stores with address: {(df['address'] != '').sum():,}")
    print(f"Stores with city:    {(df['city'] != '').sum():,}")

    # Save
    df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    print(f"\n✓ Saved to {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == '__main__':
    main()

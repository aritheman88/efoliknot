#!/usr/bin/env python3
"""
CSV to GeoJSON Converter - Effective Prices (Subchains Map)
============================================================

Converts store_effective_comparisons.csv to stores.geojson for the
subchains map at efoliknot.net/subchains.

Reads from:  subchains/data/store_effective_comparisons.csv
Writes to:   subchains/data/stores.geojson

Usage:
    python csv_to_geojson_promo.py

Author: efoliknot team
Last Updated: 2026-05-05
"""

import csv
import json
import math
import os
from pathlib import Path

# Paths relative to this script's location (efoliknot/)
SCRIPT_DIR = Path(__file__).parent
INPUT_CSV  = SCRIPT_DIR / 'subchains' / 'data' / 'store_effective_comparisons.csv'
OUTPUT_GEOJSON = SCRIPT_DIR / 'subchains' / 'data' / 'stores.geojson'


def is_numeric_string(s):
    """Check if a string represents a plain number (not an address with dots)."""
    if not isinstance(s, str):
        return False
    s = s.strip()
    if not s:
        return False
    has_decimal = False
    for i, c in enumerate(s):
        if c == '-':
            if i != 0:
                return False
        elif c == '.':
            if has_decimal:
                return False
            has_decimal = True
        elif not c.isdigit():
            return False
    return True


def csv_to_geojson(csv_file, output_file):
    """
    Convert the effective price comparisons CSV to GeoJSON.

    Skips rows with missing or invalid coordinates.
    Converts numeric strings to int/float; keeps everything else as string.
    """
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }

    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        row_num = 0

        for row in reader:
            row_num += 1

            if not row['latitude'] or not row['longitude']:
                print(f"Skipping row {row_num} with missing coordinates: {row['store_code']}")
                continue

            try:
                lat = float(row['latitude'])
                lng = float(row['longitude'])

                if math.isnan(lat) or math.isnan(lng) or math.isinf(lat) or math.isinf(lng):
                    print(f"Skipping row {row_num} with invalid coordinates: lat={lat}, lng={lng}")
                    continue

                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lng, lat]
                    },
                    "properties": {}
                }

                for key, value in row.items():
                    if key in ('latitude', 'longitude'):
                        continue
                    if not value or str(value).upper() in ('NULL', 'NAN'):
                        feature["properties"][key] = None
                    elif is_numeric_string(value):
                        try:
                            if '.' in value:
                                num = float(value)
                                feature["properties"][key] = None if (math.isnan(num) or math.isinf(num)) else num
                            else:
                                feature["properties"][key] = int(value)
                        except ValueError:
                            feature["properties"][key] = value
                    else:
                        feature["properties"][key] = value

                # Final safety check
                for key, value in feature["properties"].items():
                    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                        print(f"Invalid numeric value in row {row_num}, key {key}: {value}")
                        feature["properties"][key] = None

                geojson["features"].append(feature)

            except (ValueError, KeyError) as e:
                print(f"Skipping row {row_num} due to error: {e} (store_code={row.get('store_code', '?')})")

    # Validate before writing
    try:
        json.dumps(geojson)
        print(f"GeoJSON validation successful")
    except (TypeError, ValueError) as e:
        print(f"WARNING: GeoJSON validation failed: {e} — attempting to clean...")
        valid_features = []
        for i, feature in enumerate(geojson["features"]):
            try:
                json.dumps(feature)
                valid_features.append(feature)
            except (TypeError, ValueError):
                print(f"  Dropping invalid feature {i} (store_code={feature.get('properties', {}).get('store_code', '?')})")
        geojson["features"] = valid_features

    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"Converted {len(geojson['features'])} features to GeoJSON")
    print(f"Output saved to {output_file}")


if __name__ == "__main__":
    if not INPUT_CSV.exists():
        print(f"ERROR: Input file not found: {INPUT_CSV}")
        print("Run update_and_export_stores_promo.py first.")
        exit(1)

    print(f"Reading from: {INPUT_CSV}")
    print(f"Writing to:   {OUTPUT_GEOJSON}")
    print()
    csv_to_geojson(INPUT_CSV, OUTPUT_GEOJSON)
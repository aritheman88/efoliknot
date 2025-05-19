import csv
import json
import os
import math


def is_valid_number(value):
    """Check if a value is a valid number (not NaN or Infinity)"""
    if isinstance(value,(int,float)):
        return not math.isnan(value) and not math.isinf(value)
    return True


def csv_to_geojson(csv_file,output_file):
    """
    Convert a CSV file with latitude and longitude columns to GeoJSON format.
    Properly handles NULL, NaN, and invalid values.

    Parameters:
    csv_file (str): Path to the CSV file
    output_file (str): Path to write the GeoJSON output
    """

    # Create a GeoJSON structure
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }

    # Read the CSV file
    with open(csv_file,'r',encoding='utf-8-sig') as f:  # Note the utf-8-sig encoding
        reader = csv.DictReader(f)
        row_num = 0

        for row in reader:
            row_num += 1
            # Skip if latitude or longitude are missing or invalid
            if not row['latitude'] or not row['longitude']:
                print(f"Skipping row {row_num} with missing coordinates: {row}")
                continue

            try:
                # Convert latitude and longitude to float, ensuring they're valid numbers
                lat = float(row['latitude'])
                lng = float(row['longitude'])

                # Check if coordinates are valid numbers (not NaN or Infinity)
                if math.isnan(lat) or math.isnan(lng) or math.isinf(lat) or math.isinf(lng):
                    print(f"Skipping row {row_num} with invalid coordinates: lat={lat}, lng={lng}")
                    continue

                # Create a GeoJSON feature
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lng,lat]
                    },
                    "properties": {}
                }

                # Add all properties from the CSV, properly handling NULL, NaN and invalid values
                for key,value in row.items():
                    if key != 'latitude' and key != 'longitude':
                        # Handle empty values, "NULL", "NaN" and similar
                        if not value or str(value).upper() == "NULL" or str(value).upper() == "NAN":
                            feature["properties"][key] = None
                        else:
                            # Try to convert numeric values
                            try:
                                if isinstance(value,str) and '.' in value:
                                    num_value = float(value)
                                    # Check if it's a valid number
                                    if math.isnan(num_value) or math.isinf(num_value):
                                        print(f"Invalid numeric value in row {row_num}, key {key}: {value}")
                                        feature["properties"][key] = None
                                    else:
                                        feature["properties"][key] = num_value
                                elif isinstance(value,str) and value.lstrip('-').isdigit():
                                    feature["properties"][key] = int(value)
                                else:
                                    feature["properties"][key] = value
                            except (ValueError,TypeError) as e:
                                print(f"Error converting value in row {row_num}, key {key}: {value}, Error: {e}")
                                feature["properties"][key] = value

                # Validate the feature to ensure all values are valid for JSON
                for key,value in feature["properties"].items():
                    if isinstance(value,(int,float)) and (math.isnan(value) or math.isinf(value)):
                        print(f"Invalid numeric value in properties, row {row_num}, key {key}: {value}")
                        feature["properties"][key] = None

                # Add the feature to the collection
                geojson["features"].append(feature)

            except (ValueError,KeyError) as e:
                print(f"Skipping row {row_num} due to error: {e}")
                print(f"Problematic row: {row}")

    # Validate the entire GeoJSON before writing
    try:
        # This will fail if there are any NaN or invalid values
        test_json = json.dumps(geojson)
        print(f"GeoJSON validation successful")
    except (TypeError,ValueError) as e:
        print(f"ERROR: Invalid GeoJSON: {e}")
        # Try to find the problematic feature
        for i,feature in enumerate(geojson["features"]):
            try:
                json.dumps(feature)
            except (TypeError,ValueError) as e:
                print(f"Problem in feature {i}: {e}")
                print(f"Feature: {feature}")

                # Try to find the problematic property
                if "properties" in feature:
                    for prop_key,prop_value in feature["properties"].items():
                        try:
                            json.dumps({prop_key: prop_value})
                        except (TypeError,ValueError) as e:
                            print(f"Problem in property {prop_key}: {prop_value}")
                            # Fix the value
                            feature["properties"][prop_key] = None

    # Write the GeoJSON file
    try:
        with open(output_file,'w',encoding='utf-8') as f:
            json.dump(geojson,f,ensure_ascii=False,indent=2)
        print(f"Converted {len(geojson['features'])} features to GeoJSON")
        print(f"Output saved to {output_file}")
    except (TypeError,ValueError) as e:
        print(f"ERROR: Failed to write GeoJSON: {e}")
        # Write a safe version with filtered features
        valid_features = []
        for feature in geojson["features"]:
            try:
                json.dumps(feature)
                valid_features.append(feature)
            except:
                print(f"Skipping invalid feature")

        geojson["features"] = valid_features
        with open(output_file,'w',encoding='utf-8') as f:
            json.dump(geojson,f,ensure_ascii=False,indent=2)
        print(f"Saved {len(valid_features)} valid features to {output_file}")


if __name__ == "__main__":
    # Create data directory if it doesn't exist
    os.makedirs("data",exist_ok=True)

    # Path to your CSV file - update this to your actual path
    csv_file = "data/store_price_comparisons.csv"

    # Path to write the GeoJSON output
    output_file = "data/stores.geojson"

    csv_to_geojson(csv_file,output_file)

## Test
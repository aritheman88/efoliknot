import json
import os
import math
import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import config


def is_valid_number(value):
    """Check if a value is a valid number (not NaN or Infinity)"""
    if isinstance(value,(int,float)):
        return not math.isnan(value) and not math.isinf(value)
    return True


def postgres_to_geojson(output_file,query=None):
    """
    Connect to PostgreSQL database using config.py and convert query results to GeoJSON format.
    Properly handles NULL, NaN, and invalid values.

    Parameters:
    output_file (str): Path to write the GeoJSON output
    query (str): SQL query to execute (optional, defaults to selecting from store_price_comparisons view)
    """

    # Default query to select from the view
    if query is None:
        query = """
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
            average_price_diff,
            popular_item_count
        FROM public.store_price_comparisons
        ORDER BY store_code;
        """

    # Create a GeoJSON structure
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }

    try:
        # Connect to PostgreSQL using config
        print("Connecting to PostgreSQL database...")
        pg_conn = psycopg2.connect(**config.pg_config)

        # Use RealDictCursor to get results as dictionaries
        with pg_conn.cursor(cursor_factory=RealDictCursor) as pg_cursor:
            print("Executing query...")
            pg_cursor.execute(query)

            row_num = 0
            while True:
                # Fetch rows in batches to handle large datasets efficiently
                rows = pg_cursor.fetchmany(1000)
                if not rows:
                    break

                for row in rows:
                    row_num += 1

                    # Convert row to regular dict for easier handling
                    row_dict = dict(row)

                    # Skip if latitude or longitude are missing or invalid
                    if not row_dict.get('latitude') or not row_dict.get('longitude'):
                        print(
                            f"Skipping row {row_num} with missing coordinates: store_code={row_dict.get('store_code')}")
                        continue

                    try:
                        # Convert latitude and longitude to float, ensuring they're valid numbers
                        lat = float(row_dict['latitude'])
                        lng = float(row_dict['longitude'])

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

                        # Add all properties from the row, properly handling NULL, NaN and invalid values
                        for key,value in row_dict.items():
                            if key not in ['latitude','longitude']:
                                # Handle None/NULL values
                                if value is None:
                                    feature["properties"][key] = None
                                elif isinstance(value,(int,float)):
                                    # Check if it's a valid number
                                    if math.isnan(value) or math.isinf(value):
                                        print(f"Invalid numeric value in row {row_num}, key {key}: {value}")
                                        feature["properties"][key] = None
                                    else:
                                        feature["properties"][key] = value
                                else:
                                    # String or other types
                                    feature["properties"][key] = str(value) if value is not None else None

                        # Final validation of the feature properties
                        for key,value in feature["properties"].items():
                            if isinstance(value,(int,float)) and (math.isnan(value) or math.isinf(value)):
                                print(f"Invalid numeric value in properties, row {row_num}, key {key}: {value}")
                                feature["properties"][key] = None

                        # Add the feature to the collection
                        geojson["features"].append(feature)

                    except (ValueError,KeyError,TypeError) as e:
                        print(f"Skipping row {row_num} due to error: {e}")
                        print(f"Problematic row: store_code={row_dict.get('store_code')}")

        pg_conn.close()
        print(f"Database connection closed")

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

    # Validate the entire GeoJSON before writing
    try:
        # This will fail if there are any NaN or invalid values
        test_json = json.dumps(geojson)
        print(f"GeoJSON validation successful")
    except (TypeError,ValueError) as e:
        print(f"ERROR: Invalid GeoJSON: {e}")
        # Try to find and fix problematic features
        valid_features = []
        for i,feature in enumerate(geojson["features"]):
            try:
                json.dumps(feature)
                valid_features.append(feature)
            except (TypeError,ValueError) as e:
                print(f"Problem in feature {i}: {e}")
                # Try to fix the feature by cleaning properties
                if "properties" in feature:
                    cleaned_properties = {}
                    for prop_key,prop_value in feature["properties"].items():
                        try:
                            json.dumps({prop_key: prop_value})
                            cleaned_properties[prop_key] = prop_value
                        except (TypeError,ValueError):
                            print(f"Cleaning problematic property {prop_key}: {prop_value}")
                            cleaned_properties[prop_key] = None
                    feature["properties"] = cleaned_properties
                    valid_features.append(feature)

        geojson["features"] = valid_features

    # Write the GeoJSON file
    try:
        with open(output_file,'w',encoding='utf-8') as f:
            json.dump(geojson,f,ensure_ascii=False,indent=2)
        print(f"Converted {len(geojson['features'])} features to GeoJSON")
        print(f"Output saved to {output_file}")
    except (TypeError,ValueError) as e:
        print(f"ERROR: Failed to write GeoJSON: {e}")
        sys.exit(1)


def get_connection_params_from_env():
    """
    DEPRECATED: Connection parameters are now handled by config.py
    """
    pass


def get_connection_params_interactive():
    """
    DEPRECATED: Connection parameters are now handled by config.py
    """
    pass


if __name__ == "__main__":
    # Create data directory if it doesn't exist
    os.makedirs("data",exist_ok=True)

    # Path to write the GeoJSON output
    output_file = "data/stores.geojson"

    try:
        # Verify config is properly loaded
        if not hasattr(config,'pg_config'):
            print("ERROR: config.py does not contain 'pg_config' dictionary")
            sys.exit(1)

        print(f"Using database connection from config.py")

        # Convert PostgreSQL data to GeoJSON
        postgres_to_geojson(output_file)

    except ImportError:
        print("ERROR: Could not import config.py. Make sure the file exists and contains pg_config dictionary.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
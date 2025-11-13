# Israel Supermarket Price Map

An interactive web map for visualizing and comparing supermarket prices across Israel.
- **Live map**: https://efoliknot.net/
- **Source code**: https://github.com/aritheman88/efoliknot/

---

## 📋 Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
- [Scripts Guide](#scripts-guide)
  - [Update Popular Items View](#1-update_popular_items_viewpy)
  - [Update Store Comparisons & Export](#2-update_and_export_storespy-recommended)
  - [Update Store Comparisons Only](#3-update_store_comparisons_viewpy)
- [Complete Workflow](#complete-workflow)
- [Database Structure](#database-structure)
- [Map Features](#map-features)
- [Troubleshooting](#troubleshooting)
- [Security & Best Practices](#security--best-practices)

---

## Overview

This project combines a **Python data processing backend** with an **interactive web frontend** to visualize supermarket price comparisons across Israel. The backend connects to a PostgreSQL database (AWS RDS) to process and export price data, while the frontend uses Leaflet.js to display stores on an interactive map with color-coded markers indicating price competitiveness.

### Tech Stack
- **Backend**: Python 3.x with psycopg2, pandas
- **Database**: PostgreSQL (AWS RDS)
- **Frontend**: HTML5, CSS3, JavaScript (Leaflet.js)
- **Data Format**: GeoJSON, CSV, JSON

### How It Works

```
PostgreSQL Database (Price Data)
    ↓
1. Define "Popular Items" → popular_items_avg_prices view
    ↓
2. Calculate Store Grades → store_price_comparisons view
    ↓
3. Export to CSV → store_price_comparisons.csv
    ↓
4. Convert to GeoJSON → stores.geojson
    ↓
Interactive Map Visualization
```

---

## Project Structure

```
efoliknot/
│
├── leaflet/                           # Frontend web application
│   ├── css/
│   │   └── styles.css                 # Map and UI styles
│   ├── data/
│   │   ├── store_price_comparisons.csv # Main CSV data source
│   │   ├── stores.geojson             # Generated GeoJSON from CSV
│   │   └── store_files/               # Individual store price JSON files
│   ├── img/                           # Chain logos (19 logos)
│   ├── js/
│   │   └── map.js                     # Main JavaScript for interactive map
│   └── index.html                     # Main HTML page
│
├── Python Backend Scripts:
├── config.py                          # Database configuration (loads from .env)
│
├── View Update Scripts (NEW):
├── update_popular_items_view.py       # Updates popular items view ⭐
├── update_and_export_stores.py        # Updates view + exports CSV ⭐⭐⭐ RECOMMENDED
├── update_store_comparisons_view.py   # Updates store comparisons view only ⭐
│
├── Data Processing Scripts:
├── export_store_data.py               # Legacy export script (slower)
├── csv_to_geojson.py                  # CSV → GeoJSON converter
├── pg_to_geojson.py                   # PostgreSQL → GeoJSON converter
│
├── Debugging Tools:
├── debug_database.py                  # Database diagnostic tool
├── pg_quick_debug.py                  # Quick database view tester
│
├── Configuration Files:
├── .env                               # Environment variables (NOT in git)
├── .env.example                       # Environment template
├── .gitignore                         # Git ignore rules
├── requirements.txt                   # Python dependencies
└── README.md                          # This file
```

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/aritheman88/efoliknot.git
cd efoliknot
```

### 2. Set Up Python Environment

```bash
# Using conda (recommended)
conda activate basic  # or your preferred environment

# Install dependencies
pip install -r requirements.txt
```

**Dependencies installed**:
- `psycopg2-binary` - PostgreSQL database adapter
- `pandas` - Data processing library
- `python-dotenv` - Environment variable management

### 3. Configure Database Credentials

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your credentials
```

Your `.env` file should contain:
```
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=your_database_host
DB_PORT=5432
```

**⚠️ IMPORTANT**: Never commit `.env` to git! It's already in `.gitignore`.

### 4. Verify Setup

Test your database connection:
```bash
python debug_database.py
```

---

## Scripts Guide

### 1. `update_popular_items_view.py`

**Purpose**: Updates the `popular_items_avg_prices` database view  
**When to use**: First step when updating with new price data  
**Run time**: ~15 seconds

This script defines which items are "popular" (appear in many stores) and calculates their national average prices. An item is "popular" if it appears in a minimum number of stores (e.g., 10+ stores).

#### Basic Usage

**Interactive mode** (recommended for beginners):
```bash
python update_popular_items_view.py
```

**Command-line mode** (faster for regular use):
```bash
python update_popular_items_view.py --date 2025-11-10 --min-stores 10
# Or short form:
python update_popular_items_view.py -d 2025-11-10 -m 10
```

**Test mode** (preview SQL without executing):
```bash
python update_popular_items_view.py --dry-run -d 2025-11-10 -m 10
```

#### Parameters

- **`--date`** / **`-d`**: Upload date (YYYY-MM-DD format)
  - Example: `2025-11-10`
  - Must match the date in your `allprices` table

- **`--min-stores`** / **`-m`**: Minimum number of stores for an item to be "popular"
  - `10` = Standard (recommended)
  - `15` = Stricter (fewer items, more widely available)
  - `5` = More inclusive (more items, less common)

#### Example Output

```
============================================================
Updating popular_items_avg_prices view
============================================================
Date: 2025-11-10
Minimum stores threshold: 10
============================================================

Connecting to database...
Executing view update...
Verifying view creation...

✓ View successfully updated!
✓ Number of popular items: 847

Sample of popular items (first 5):
  - 7290000066684: חלב 3% 1 ליטר (avg: ₪6.45)
  - 7290006587213: לחם פרוס שיפון 750 גרם (avg: ₪5.90)
  - 7290000004013: ביצים M 12 יח' (avg: ₪13.20)
  ...
```

---

### 2. `update_and_export_stores.py` ⭐⭐⭐ **RECOMMENDED**

**Purpose**: Updates the `store_price_comparisons` view AND exports to CSV  
**When to use**: Your primary script for regular updates  
**Run time**: ~30 seconds  
**Why it's the best**: Combines view update + CSV export in one fast script

This is the **ultimate solution** that combines the best features:
- ✅ Fast database view updates with configurable parameters
- ✅ Detailed progress tracking and statistics
- ✅ Creates both dated and standard CSV files
- ✅ 30-60x faster than the legacy export script

#### Basic Usage

**Standard update** (most common):
```bash
python update_and_export_stores.py --date 2025-11-10
# Or short form:
python update_and_export_stores.py -d 2025-11-10
```

**Interactive mode**:
```bash
python update_and_export_stores.py
```

**Re-export without updating view** (if view is already current):
```bash
python update_and_export_stores.py -d 2025-11-10 --skip-view-update
```

**Custom exclusions**:
```bash
python update_and_export_stores.py -d 2025-11-10 \
  --exclude-chains "Yellow,דור אלון" \
  --exclude-subchains "Be,אונליין"
```

#### Parameters

- **`--date`** / **`-d`**: Upload date (YYYY-MM-DD format)
- **`--exclude-chains`**: Comma-separated list of chains to exclude
  - Default: `סופר פארם, Yellow, דור אלון`
- **`--exclude-subchains`**: Comma-separated list of subchains to exclude
  - Default: `Be, אונליין`
- **`--exclude-cities`**: Comma-separated list of cities to exclude
  - Default: `unknown`
- **`--skip-view-update`**: Skip view update, only export CSV
- **`--output-dir`**: Custom output directory

#### Output Files

The script creates **TWO CSV files**:

1. **Dated file**: `store_price_comparisons_2025-11-10.csv`
   - For archiving and version history
   - Includes date in filename

2. **Standard file**: `store_price_comparisons.csv`
   - For the map to use (always latest data)
   - No date in filename

**Default location**: `C:\Users\ariel\MyPythonScripts\efoliknot\data\`

#### Example Output

```
======================================================================
[2025-11-13 10:30:15] Starting process for 2025-11-10
======================================================================

[2025-11-13 10:30:15] Connecting to PostgreSQL database...
[2025-11-13 10:30:15]   ✓ Connected successfully!

[2025-11-13 10:30:15] Step 1: Updating store_price_comparisons view...
[2025-11-13 10:30:18]   ✓ View updated successfully in 3.2 seconds

[2025-11-13 10:30:18] Step 2: Exporting view to CSV...
[2025-11-13 10:30:21]   ✓ Loaded 847 stores in 2.8 seconds
[2025-11-13 10:30:22]   ✓ Export completed in 3.5 seconds

======================================================================
✓ Export completed successfully!
======================================================================

Output files:
  1. store_price_comparisons_2025-11-10.csv
  2. store_price_comparisons.csv (for map)

Summary:
  - Total stores: 847
  - Unique chains: 12
  - Date: 2025-11-10

Price difference statistics:
  - Cheapest store: -12.45% below average
  - Most expensive store: +15.32% above average
  - Mean difference: +0.02%
  - Median difference: -0.15%

Popular items per store:
  - Minimum: 125 items
  - Maximum: 892 items
  - Average: 547 items

Top 5 cheapest stores:
  רמי לוי דרך בגין      (רמי לוי, תל אביב): -8.23% | 678 items
  ...

Top 5 most expensive stores:
  מחסני השוק גאולה      (מחסני השוק, ירושלים): +9.87% | 423 items
  ...

Stores by chain:
  שופרסל: 256 stores | avg +1.23%
  רמי לוי: 178 stores | avg -3.45%
  ...

Total runtime: 0.6 minutes
======================================================================
```

---

### 3. `update_store_comparisons_view.py`

**Purpose**: Updates the `store_price_comparisons` view only (no CSV export)  
**When to use**: When you only want to update the database view  
**Run time**: ~5 seconds

Use this script when:
- You only want to update the database view
- Other tools will read from the view directly
- You need to test with dry-run mode

#### Basic Usage

```bash
# Standard update
python update_store_comparisons_view.py -d 2025-11-10

# Test with dry-run
python update_store_comparisons_view.py --dry-run -d 2025-11-10

# Interactive mode
python update_store_comparisons_view.py
```

---

## Complete Workflow

### Standard Weekly Update (Recommended)

When you receive new price data:

```bash
# Step 1: Update popular items view (defines "popular")
python update_popular_items_view.py -d 2025-11-10 -m 10

# Step 2: Update store comparisons AND export CSV
python update_and_export_stores.py -d 2025-11-10

# Step 3: Convert to GeoJSON for map
python csv_to_geojson.py

# Step 4: Test locally
cd leaflet
python -m http.server
# Visit http://localhost:8000
```

**Total time**: ~1 minute

### Quick One-Liner

```bash
python update_popular_items_view.py -d 2025-11-10 -m 10 && \
python update_and_export_stores.py -d 2025-11-10 && \
python csv_to_geojson.py
```

### Batch Script (Windows)

Create `update_map.bat`:
```batch
@echo off
set DATE=%1
if "%DATE%"=="" (
    echo Usage: update_map.bat YYYY-MM-DD
    exit /b 1
)
python update_popular_items_view.py -d %DATE% -m 10 || exit /b 1
python update_and_export_stores.py -d %DATE% || exit /b 1
python csv_to_geojson.py || exit /b 1
echo Complete! Test at: http://localhost:8000
```

Usage: `update_map.bat 2025-11-10`

### Shell Script (Linux/Mac)

Create `update_map.sh`:
```bash
#!/bin/bash
DATE=$1
[ -z "$DATE" ] && { echo "Usage: update_map.sh YYYY-MM-DD"; exit 1; }
python update_popular_items_view.py -d $DATE -m 10 || exit 1
python update_and_export_stores.py -d $DATE || exit 1
python csv_to_geojson.py || exit 1
echo "Complete! Test at: http://localhost:8000"
```

Usage: `chmod +x update_map.sh && ./update_map.sh 2025-11-10`

---

## Database Structure

### Tables

**`allprices`**
- Stores price data for all items across all stores
- Key columns: `store_code`, `itemcode`, `itemprice`, `upload_date`
- Updated regularly with new price data

**`all_stores`**
- Master table of all supermarket locations
- Key columns: `store_code`, `storename`, `chainname`, `subchainname`, `latitude`, `longitude`, `address`, `city`, `zipcode`

**`items`** (or `items_new`)
- Product catalog with item details
- Key columns: `itemcode`, `itemname`, `supplier`, `brand`, `category`

### Views

**`popular_items_avg_prices`**
- Calculates average prices for popular items
- Filters out: Super-Pharm, Yellow, Dor Alon chains
- Filters out: Be, Online subchains
- Updated by: `update_popular_items_view.py`

**`store_price_comparisons`**
- Main view comparing each store's prices to national average
- Calculates: `average_price_diff` (percentage), `popular_item_count`
- Powers the interactive map
- Updated by: `update_and_export_stores.py` or `update_store_comparisons_view.py`

### View Logic

The `store_price_comparisons` view:
1. Finds all popular items in each store
2. Compares each item's price to the national average
3. Calculates percentage difference for each item
4. Averages all differences to grade the store

Example: Store with `-8.23%` is 8.23% cheaper than the national average.

---

## Map Features

### Interactive Map
- **Clustering**: Markers cluster when zoomed out for better performance
- **Click markers**: View detailed store information
- **Color-coded**: Easy visual identification of price levels

### Price Color System

Consistent across all map components:
- **Dark Green** (#006400): Below -8% (much cheaper)
- **Light Green** (#32CD32): -8% to -3% (cheaper)
- **Yellow** (#FFFF00): -3% to +3% (average)
- **Orange** (#FF8C00): +3% to +8% (more expensive)
- **Red** (#FF0000): Above +8% (much more expensive)

### Price Filtering
- **Hebrew interface**: "אילו סופרמרקטים להראות?"
- **Range slider**: From "רק הזולים" (only cheap) to "כולל יקרים" (including expensive)
- **Mobile-optimized**: Proper RTL handling

### Other Features
- **Chain logos**: Automatically displays supermarket chain logos
- **Collapsible legend**: Save screen space
- **Price comparison table**: View individual product prices
- **RTL support**: Full Hebrew interface with proper text handling
- **Responsive design**: Works on desktop and mobile

---

## Troubleshooting

### Common Issues

#### "Invalid date format"
**Solution**: Use YYYY-MM-DD format
- ✅ Correct: `2025-11-10`
- ❌ Wrong: `11/10/2025` or `10-11-2025`

#### "View doesn't exist" or "popular_items_avg_prices not found"
**Solution**: Run the popular items update first:
```bash
python update_popular_items_view.py -d 2025-11-10 -m 10
```

#### Very few stores in output
**Check**:
1. Does the date exist in your `allprices` table?
2. Did you use the same date for both scripts?
3. Are your exclusions too strict?

**Debug**:
```bash
python debug_database.py
```

#### Map shows old data
**Solution**: Make sure you ran all steps:
```bash
python update_popular_items_view.py -d 2025-11-10 -m 10
python update_and_export_stores.py -d 2025-11-10
python csv_to_geojson.py
# Hard refresh browser: Ctrl+Shift+R
```

#### Database connection failed
**Check**:
- `.env` file exists and has correct credentials
- Database server is accessible
- Your IP is allowed by AWS security groups

#### Store grades seem wrong
**Check**:
- Did you use the same date for both view updates?
- Is the minimum stores threshold reasonable? (try 10)
- Verify exclusions are correct

**Test**:
```bash
python update_popular_items_view.py --dry-run -d 2025-11-10 -m 10
python update_and_export_stores.py --dry-run -d 2025-11-10
```

### Diagnostic Commands

```bash
# Comprehensive database diagnostics
python debug_database.py

# Quick view testing
python pg_quick_debug.py

# Get help for any script
python SCRIPT_NAME.py --help
```

---

## Security & Best Practices

### Recent Security Improvements

**Critical vulnerabilities fixed (2025-11-05)**:

1. ✅ **Hardcoded credentials removed** - All credentials now in `.env` file
2. ✅ **SQL injection fixed** - All queries use parameterized statements
3. ✅ **Git security improved** - Comprehensive `.gitignore` file

### Security Checklist

- [ ] Never commit `.env` file to git
- [ ] Use strong, unique passwords for database access
- [ ] Restrict AWS RDS security groups to known IPs
- [ ] Keep dependencies updated (`pip list --outdated`)
- [ ] Review git history for accidentally committed secrets
- [ ] Test new SQL queries with dry-run mode first

### Best Practices

#### Always Use Same Date
```bash
# ✅ CORRECT
DATE="2025-11-10"
python update_popular_items_view.py -d $DATE -m 10
python update_and_export_stores.py -d $DATE

# ❌ WRONG - Different dates
python update_popular_items_view.py -d 2025-11-10 -m 10
python update_and_export_stores.py -d 2025-11-02  # Different date!
```

#### Update Popular Items First
```bash
# ✅ CORRECT ORDER
python update_popular_items_view.py -d 2025-11-10 -m 10
python update_and_export_stores.py -d 2025-11-10

# ❌ WRONG - Skip popular items update
python update_and_export_stores.py -d 2025-11-10  # Uses old averages!
```

#### Test Before Deploying
```bash
# Test with dry-run
python update_popular_items_view.py --dry-run -d 2025-11-10 -m 10

# Test locally before deploying
cd leaflet && python -m http.server
```

#### Keep Defaults
Use default exclusions unless you have a specific reason to change them:
- Chains: `סופר פארם, Yellow, דור אלון`
- Subchains: `Be, אונליין`
- Cities: `unknown`

---

## Script Comparison

### Performance

| Script | Purpose | Speed | Flexibility |
|--------|---------|-------|-------------|
| `export_store_data.py` (legacy) | Export CSV | ⭐⭐ Slow (5-10 min) | ⭐ Limited |
| `update_store_comparisons_view.py` | Update view | ⭐⭐⭐ Fast (5 sec) | ⭐⭐⭐ High |
| `update_and_export_stores.py` | Both | ⭐⭐⭐ Fast (30 sec) | ⭐⭐⭐ High |

### When to Use Each Script

**Use `update_and_export_stores.py` for**:
- ✅ Standard weekly updates (99% of use cases)
- ✅ When you need CSV output
- ✅ Maximum speed and convenience

**Use `update_store_comparisons_view.py` for**:
- ✅ View-only updates (no CSV needed)
- ✅ When other tools read from view
- ✅ Testing with dry-run mode

**Use `export_store_data.py` for**:
- ⚠️ Legacy compatibility only
- ⚠️ Generally not recommended anymore

---

## Quick Reference

### Most Common Commands

```bash
# Standard weekly update
python update_popular_items_view.py -d 2025-11-10 -m 10
python update_and_export_stores.py -d 2025-11-10
python csv_to_geojson.py

# Re-export without view update
python update_and_export_stores.py -d 2025-11-10 --skip-view-update

# Interactive mode (beginner-friendly)
python update_and_export_stores.py

# Test with dry-run
python update_popular_items_view.py --dry-run -d 2025-11-10 -m 10

# Get help
python update_and_export_stores.py --help
```

### Parameter Quick Reference

**Popular Items**:
- `--date`, `-d`: Date (YYYY-MM-DD)
- `--min-stores`, `-m`: Minimum stores threshold (10 recommended)
- `--dry-run`: Preview SQL without executing

**Store Comparisons & Export**:
- `--date`, `-d`: Date (YYYY-MM-DD)
- `--exclude-chains`: Chains to exclude (comma-separated)
- `--exclude-subchains`: Subchains to exclude (comma-separated)
- `--exclude-cities`: Cities to exclude (comma-separated)
- `--skip-view-update`: Skip view update, only export
- `--output-dir`: Custom output directory

---

## CSV Format

The exported CSV includes:

- `store_code`: Unique identifier
- `store_name`: Store name
- `chainname`: Supermarket chain
- `subchainname`: Sub-chain name
- `storeid`: Numeric ID
- `address`: Store address
- `city`: City name
- `zipcode`: Postal code
- `latitude`: Geographic latitude
- `longitude`: Geographic longitude
- `average_price_diff`: Average price difference percentage vs. national average
- `popular_item_count`: Number of popular items in store

---

## Dependencies

### Frontend
- [Leaflet](https://leafletjs.com/) - Interactive maps
- [Leaflet.markercluster](https://github.com/Leaflet/Leaflet.markercluster) - Marker clustering
- [Font Awesome](https://fontawesome.com/) - Icons

### Backend (Python)
- **psycopg2-binary** (2.9.9) - PostgreSQL adapter
- **pandas** (2.1.4) - Data manipulation
- **python-dotenv** (1.0.0) - Environment variables

---

## Future Enhancements

Potential improvements:
- Search function for specific stores
- Data layers for different time periods
- Heatmap view based on price differences
- Route planning to nearest cheaper store
- User accounts for saving favorites
- Direct store comparison feature
- Mobile app for offline use
- Automated tests for Python scripts
- Type hints throughout codebase
- CI/CD pipeline for deployments

---

## License

All rights reserved. Based on publicly available price data from supermarket chains.

---

## Support

For issues or questions:
- Run diagnostics: `python debug_database.py`
- Check this README's Troubleshooting section
- Review error messages carefully
- Test with `--dry-run` mode first

---

**Last Updated**: 2025-11-13  
**Version**: 3.0.0 (Consolidated documentation + new scripts)
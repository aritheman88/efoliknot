# Israel Supermarket Price Map

An interactive web map for visualizing and comparing supermarket prices across Israel.
The map is available at https://efoliknot.net/, and the source code is hosted on GitHub:
https://github.com/aritheman88/efoliknot/

## Overview

This project combines a **Python data processing backend** with an **interactive web frontend** to visualize supermarket price comparisons across Israel. The backend connects to a PostgreSQL database (AWS RDS) to process and export price data, while the frontend uses Leaflet.js to display stores on an interactive map with color-coded markers indicating price competitiveness.

### Tech Stack
- **Backend**: Python 3.x with psycopg2, pandas
- **Database**: PostgreSQL (AWS RDS)
- **Frontend**: HTML5, CSS3, JavaScript (Leaflet.js)
- **Data Format**: GeoJSON, CSV, JSON

## Project Structure

```
efoliknot/
│
├── leaflet/                           # Frontend web application
│   ├── css/
│   │   └── styles.css                 # Styles for the map and UI
│   ├── data/
│   │   ├── stores_map_sample.csv      # Sample CSV data
│   │   ├── store_price_comparisons.csv # Main CSV data source
│   │   ├── stores.geojson             # Generated GeoJSON from CSV
│   │   └── store_files/               # Individual store price JSON files (256 stores)
│   ├── img/                           # Image assets directory (19 chain logos)
│   │   ├── lobby99 water.png          # Organization logo
│   │   ├── ramiLevi.png               # Supermarket chain logos
│   │   ├── shufersal.png
│   │   ├── victory.png
│   │   └── ...
│   ├── js/
│   │   └── map.js                     # Main JavaScript for interactive map (658 lines)
│   └── index.html                     # Main HTML page (349 lines)
│
├── Python Backend Scripts:
├── config.py                          # Database configuration (loads from .env)
├── pg_to_geojson.py                   # PostgreSQL → GeoJSON converter (220 lines)
├── csv_to_geojson.py                  # CSV → GeoJSON converter (188 lines)
├── export_store_data.py               # Export store price data to CSV (250 lines)
├── update_popular_items_view.py       # Update popular items view with custom parameters ⭐ NEW
├── debug_database.py                  # Database diagnostic tool (209 lines)
├── pg_quick_debug.py                  # Quick database view tester (114 lines)
│
├── Configuration Files:
├── .env                               # Environment variables (NOT in git)
├── .env.example                       # Environment template (safe to commit)
├── .gitignore                         # Git ignore rules
├── requirements.txt                   # Python dependencies
└── README.md                          # This documentation file
```

## Setup Instructions

### Initial Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/aritheman88/efoliknot.git
   cd efoliknot
   ```

2. **Set up Python environment** (recommended: use conda):
   ```bash
   conda activate basic  # or your preferred environment
   pip install -r requirements.txt
   ```

   This installs:
   - `psycopg2-binary` - PostgreSQL database adapter
   - `pandas` - Data processing library
   - `python-dotenv` - Environment variable management

3. **Configure database credentials**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your database credentials:
   ```
   DB_NAME=your_database_name
   DB_USER=your_database_user
   DB_PASSWORD=your_database_password
   DB_HOST=your_database_host
   DB_PORT=5432
   ```

   **IMPORTANT**: Never commit `.env` to git. It's already in `.gitignore`.

4. **Prepare your data**:
   - Place your CSV file in the `data` directory
   - Make sure it has the required columns (latitude, longitude, etc.)
   - Add supermarket chain logos to the `img` directory (PNG format recommended)

### Running the Application

1. **Update the popular items view** (recommended first step):
   ```bash
   # Interactive mode (recommended for first-time users)
   python update_popular_items_view.py
   
   # Command-line mode with specific parameters
   python update_popular_items_view.py --date 2025-11-02 --min-stores 10
   
   # Dry run to preview SQL without executing
   python update_popular_items_view.py --dry-run -d 2025-11-02 -m 10
   ```
   
   This updates the database view that determines which items are "popular" based on:
   - **Date**: Which day's price data to use
   - **Min stores**: Minimum number of stores an item must appear in (e.g., 10 means item must be in 10+ stores)

2. **Export data from PostgreSQL to CSV**:
   ```bash
   python export_store_data.py
   ```
   This creates `data/store_price_comparisons.csv` with price comparison data.

3. **Convert data to GeoJSON**:

   From PostgreSQL:
   ```bash
   python pg_to_geojson.py
   ```

   Or from CSV:
   ```bash
   python csv_to_geojson.py
   ```

   This creates `data/stores.geojson` that the map will use.

4. **Start a local web server**:
   ```bash
   cd leaflet
   python -m http.server
   ```
   Then open `http://localhost:8000` in your browser.

### Debugging

If you encounter issues with the database views:

```bash
python debug_database.py      # Comprehensive diagnostics
python pg_quick_debug.py      # Quick view testing
```

## Features

- **Interactive Map**: View all supermarkets across Israel with custom markers
- **Clustering**: Markers are clustered for better performance and readability
- **Detailed Information**: Click on markers to view detailed store information
- **Chain Logos**: Displays supermarket chain logos in store details and popups
- **Simplified Filtering**: Single price range filter to control which stores to display
  - Hebrew interface: "אילו סופרמרקטים להראות?" (Which supermarkets to show?)
  - Range from "רק הזולים" (only cheap ones) to "כולל יקרים" (including expensive ones)
  - Mobile-optimized with swapped label positions for proper functionality
- **Responsive Design**: Works on desktop and mobile devices
- **Consistent Color-Coded System**: Easily identify stores with higher/lower prices using a consistent color system:
  - Dark Green: Prices below -8% of average (much cheaper)
  - Light Green: Prices between -8% and -3% of average (cheaper)
  - Yellow: Prices between -3% and +3% of average (average)
  - Orange: Prices between +3% and +8% of average (more expensive)
  - Red: Prices above +8% of average (much more expensive)
- **Collapsible Legend**: Interactive legend with toggle functionality to save screen space
- **Price Comparison Table**: View and compare individual product prices within each store
- **Multilingual Support**: Full Hebrew interface with proper RTL (right-to-left) text handling
- **Custom Color Scheme**: Blue (#002d7f) and orange (#ff463c) branded color scheme

## Chain Logo System

The application automatically maps supermarket chain names to their corresponding logo images:

```javascript
const chainLogos = {
    'רמי לוי': 'ramiLevi.png',
    'שופרסל': 'shufersal.png',
    'ויקטורי': 'victory.png',
    // Additional chains...
};
```

To add support for a new supermarket chain:
1. Add the chain's logo to the `img` directory (PNG format with transparent background recommended)
2. Add a mapping in the `chainLogos` object in `map.js`

The system also supports partial matching for chain names, so "רמי לוי שיווק" would match "רמי לוי" and display the correct logo.

## Color-Coding System

The map uses a consistent color-coding system across all components:

- **Map Markers**: Individual store markers on the map
- **Marker Clusters**: Groups of stores when zoomed out
- **Price Indicators**: In store popups and detail panels
- **Price Comparison Table**: When viewing individual product prices

The color thresholds are:
- **Dark Green** (#006400): Below -8% (much cheaper than average)
- **Light Green** (#32CD32): Between -8% and -3% (cheaper than average)
- **Yellow** (#FFFF00): Between -3% and +3% (around average)
- **Orange** (#FF8C00): Between +3% and +8% (more expensive than average)
- **Red** (#FF0000): Above +8% (much more expensive than average)

To modify these thresholds, edit the color determination logic in the following functions in `map.js`:
- `createMarker` function (for individual store markers)
- `iconCreateFunction` in the marker cluster configuration (for clustered markers)
- Price indicator class determination in popup content and store details
- Price cell color determination in the `createPriceTable` function

## RTL Number Display

The application properly handles the display of negative numbers in RTL (right-to-left) context using special CSS:

```css
.number-wrapper {
    direction: ltr;  /* Force left-to-right direction for numbers */
    display: inline-block;
    unicode-bidi: embed; /* Preserves the bidirectional algorithm's behavior */
}
```

This ensures that negative signs always appear on the left side of numbers rather than the right, making price differences more intuitive to read.

## Collapsible Legend

The map includes a collapsible legend that can be toggled to save screen space:

- The legend is fully customizable and shows the color-coding system
- User preferences for the legend state (expanded/collapsed) are saved in localStorage
- The legend is positioned to avoid interference with map controls

## Known Issues and Troubleshooting

- **JSON Parsing Errors**: If you encounter "Unexpected token 'N'" errors or other JSON parsing issues, check your GeoJSON file for NaN, NULL, or other invalid JSON values. Use the enhanced `csv_to_geojson.py` script provided to handle these cases.

- **Hebrew Text with Periods**: The CSV parser may have issues with Hebrew text containing periods (e.g., "ד.מ.", "ק.אתא"). These will generate warnings but should still create a valid GeoJSON file.

- **Missing Logos**: If a chain logo doesn't appear, check the console log for a list of unique chain names in your data and ensure they're all mapped in the `chainLogos` object in `map.js`.

- **Missing Markers**: If markers aren't appearing, check browser console logs (F12) for errors. You can also try creating a test GeoJSON file with a few points to verify the basic functionality.

- **CORS Issues**: If accessing via a local file rather than a server, you might encounter Cross-Origin Resource Sharing (CORS) restrictions. Use the provided Python HTTP server to avoid these issues.

- **Browser Cache**: If you don't see your changes after updating files, try a hard refresh (Ctrl+Shift+R) or clear your browser cache. For development, you can add version numbers to your resource URLs (e.g., `styles.css?v=1.1`).

## CSV Format Requirements

The CSV file should include the following columns:

- `store_code`: Unique identifier for each store
- `store_name`: Name of the store
- `chainname`: Name of the supermarket chain
- `subchainname`: Sub-chain name (if applicable)
- `storeid`: Numeric ID for the store
- `address`: Store address
- `city`: City name
- `zipcode`: Postal code
- `latitude`: Geographic latitude (decimal)
- `longitude`: Geographic longitude (decimal)
- `average_price_diff`: Average price difference percentage compared to market average
- `popular_item_count`: Number of popular items available in the store

## Database Structure

The project uses a PostgreSQL database with the following key tables and views:

### Tables

**`allprices`**
- Stores price data for all items across all stores
- Key columns: `store_code`, `itemcode`, `itemprice`, `upload_date`
- Updated regularly with new price data

**`all_stores`**
- Master table of all supermarket locations
- Key columns: `store_code`, `storename`, `chainname`, `subchainname`, `latitude`, `longitude`, `address`, `city`, `zipcode`
- Includes geographic coordinates for mapping

**`items_new`** (or `items`)
- Product catalog with item details
- Key columns: `itemcode`, `itemname`, `supplier`, `brand`, `category`

### Views

**`popular_items_avg_prices`**
- Calculates average prices for popular items (items sold in a configurable number of stores)
- Excludes specific chains: Super-Pharm, Yellow, Dor Alon
- Excludes subchains: Be, Online stores
- Used as baseline for price comparisons
- **Can be updated using `update_popular_items_view.py`** ⭐

**`store_price_comparisons`**
- Main view that compares each store's prices to market averages
- Calculates `average_price_diff` (percentage deviation from average)
- Counts `popular_item_count` (number of popular items in stock)
- Output columns match CSV format requirements above
- Powers the interactive map visualization

### Data Flow

```
PostgreSQL Database
     ↓
[update_popular_items_view.py] → Update popular items view (optional but recommended)
     ↓
[export_store_data.py] → CSV export
     ↓
[csv_to_geojson.py] → GeoJSON conversion
     ↓
Leaflet Map (index.html + map.js)
```

Or directly:

```
PostgreSQL Database
     ↓
[update_popular_items_view.py] → Update popular items view (optional but recommended)
     ↓
[pg_to_geojson.py] → GeoJSON conversion
     ↓
Leaflet Map (index.html + map.js)
```

## Customization

- **Styles**: Modify the CSS in `css/styles.css` to change the appearance
- **Map Settings**: Adjust the map configuration in `js/map.js`
- **Adding Data**: Convert additional data using the Python script
- **Adding Layers**: Modify the JavaScript to include additional map layers
- **Chain Logos**: Add more supermarket chain logos to the `img` directory and update the `chainLogos` mapping in `map.js`
- **Price Difference Thresholds**: Modify the color thresholds in the relevant functions in `map.js`
- **Legend**: Customize the legend in `index.html` and its toggle behavior in the accompanying JavaScript
- **Popular Items Definition**: Use `update_popular_items_view.py` to adjust what constitutes a "popular" item

## CSS Organization

The stylesheet is organized into logical sections:

1. **Global/Reset Styles**: Basic styles that apply to the entire application
2. **Layout/Structure**: Styles for the container, header, content areas
3. **Component-Specific Styles**: Styles for filters, map elements, popups, etc.
4. **Utility Classes**: Reusable styles for common patterns
5. **Media Queries**: Responsive design adjustments for different screen sizes

When modifying the CSS, maintain this organization to keep the code clean and maintainable.

## Performance Optimizations

The application includes several mobile performance optimizations:
- Debounced slider input to reduce frequent map updates
- Minimized console logging for faster mobile rendering
- Optimized marker clustering calculations
- Mobile-specific UI adaptations for Hebrew RTL layout

## Python Backend Scripts

### Database Management Scripts

**`update_popular_items_view.py`** ⭐ **NEW**
- Updates the `popular_items_avg_prices` view with custom parameters
- Configurable upload date and minimum store threshold
- Interactive mode or command-line arguments
- Includes dry-run option for testing
- Validates inputs and provides detailed feedback
- Usage examples:
  ```bash
  # Interactive mode
  python update_popular_items_view.py
  
  # Command-line mode
  python update_popular_items_view.py --date 2025-11-02 --min-stores 10
  
  # Short form
  python update_popular_items_view.py -d 2025-11-02 -m 15
  
  # Dry run (preview only)
  python update_popular_items_view.py --dry-run -d 2025-11-02 -m 10
  ```

### Data Processing Scripts

**`pg_to_geojson.py`** (220 lines)
- Connects to PostgreSQL database
- Fetches data from `store_price_comparisons` view
- Validates coordinates and handles invalid data
- Processes data in batches of 1000 rows
- Outputs GeoJSON for map visualization

**`csv_to_geojson.py`** (188 lines)
- Converts CSV files to GeoJSON format
- Smart numeric string detection
- Handles Hebrew text with UTF-8-sig encoding
- Comprehensive data validation

**`export_store_data.py`** (250 lines)
- Exports store price comparisons from PostgreSQL to CSV
- Optimized using pre-loaded average prices
- Provides detailed progress reporting with timestamps
- Calculates store rankings based on price differences

### Debugging Tools

**`debug_database.py`** (209 lines)
- Comprehensive database diagnostics
- Tests data availability by date
- Analyzes popular items thresholds
- Tests database views with different parameters

**`pg_quick_debug.py`** (114 lines)
- Quick diagnostic tool for database views
- Tests `popular_items_avg_prices` view
- Tests `store_price_comparisons` view
- Query timeout protection (30 seconds)

### Configuration

**`config.py`**
- Loads database credentials from `.env` file using `python-dotenv`
- Validates all required environment variables
- Provides `pg_config` dictionary for psycopg2 connections

## Typical Workflow

Here's a recommended workflow when updating the map with new price data:

1. **Update the popular items view** with the new date:
   ```bash
   python update_popular_items_view.py -d 2025-11-10 -m 10
   ```

2. **Export the store data** to CSV:
   ```bash
   python export_store_data.py
   ```

3. **Convert to GeoJSON**:
   ```bash
   python csv_to_geojson.py
   ```

4. **Test locally**:
   ```bash
   cd leaflet
   python -m http.server
   ```

5. **Deploy** the updated files to your production server

## Security & Best Practices

### Recent Security Improvements (2025-11-05)

**Critical vulnerabilities fixed:**

1. **Hardcoded Credentials Removed**
   - Previously: Database password stored in plaintext in `config.py`
   - Now: All credentials loaded from `.env` file (excluded from git)
   - Impact: Prevents credential exposure in version control

2. **SQL Injection Vulnerabilities Fixed**
   - Previously: F-string date interpolation in SQL queries
   - Now: Parameterized queries using psycopg2 placeholders (`%s`)
   - Files fixed: `debug_database.py`, `pg_quick_debug.py`, `update_popular_items_view.py`
   - Impact: Prevents SQL injection attacks

3. **Git Security Improved**
   - Added comprehensive `.gitignore` file
   - Excludes: `__pycache__/`, `.env`, `config.py`, sensitive data files
   - Created `.env.example` as template for developers

### Code Quality Assessment

**Strengths:**
- Excellent data validation with multiple layers
- Smart performance optimizations (batch processing, clustering)
- Proper Hebrew language support (UTF-8, RTL)
- Rich user experience with interactive features
- Good documentation and progress logging
- Parameterized SQL queries throughout

**Areas for Improvement:**
- ❌ No type hints (planned enhancement)
- ❌ No unit tests (0% test coverage)
- ⚠️ Some broad exception handling
- ⚠️ Code duplication between CSV and PostgreSQL converters
- ⚠️ Hardcoded file paths in some scripts

**Overall Code Quality: 6.0/10** (improved from 5.5/10)
- Functionality: 9/10
- Security: 9/10 (improved from 8/10)
- Maintainability: 6/10
- Testing: 0/10
- Documentation: 8/10 (improved from 7/10)

### Security Checklist

When deploying or contributing to this project:

- [ ] Never commit `.env` file to git
- [ ] Rotate database passwords if they were ever exposed
- [ ] Use strong, unique passwords for database access
- [ ] Restrict AWS RDS security groups to known IPs
- [ ] Keep dependencies updated (`pip list --outdated`)
- [ ] Use parameterized queries for all SQL operations ✓
- [ ] Review git history for accidentally committed secrets
- [ ] Test new SQL queries with dry-run mode first

## Future Enhancements

Potential improvements to consider:
- Implementing a search function for specific stores
- Adding data layers for different time periods
- Creating a heatmap view based on price differences
- Adding route planning to the nearest cheaper store
- Implementing user accounts for saving favorite stores
- Adding a comparison feature to directly compare prices between two stores
- Developing a mobile app version for offline use
- Adding automated tests for Python backend scripts
- Implementing type hints throughout the codebase
- Creating a CI/CD pipeline for automated deployments

## Hosting

To make this map publicly available through your organization's website:

1. Upload all files to your web server
2. Ensure the server allows access to the data files
3. Update any relative paths if necessary

## Dependencies

### Frontend
- [Leaflet](https://leafletjs.com/): Open-source JavaScript library for interactive maps
- [Leaflet.markercluster](https://github.com/Leaflet/Leaflet.markercluster): Plugin for clustering markers
- [Font Awesome](https://fontawesome.com/): Icon library for user interface elements

### Backend (Python)
- **psycopg2-binary** (2.9.9): PostgreSQL database adapter
- **pandas** (2.1.4): Data manipulation and analysis
- **python-dotenv** (1.0.0): Environment variable management

## License

All rights reserved. Based on publicly available price data from supermarket chains.

---

**Last Updated**: 2025-11-13  
**Version**: 2.1.0 (Added `update_popular_items_view.py`)
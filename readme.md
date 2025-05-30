# Israel Supermarket Price Map

An interactive web map for visualizing and comparing supermarket prices across Israel.
The map is available at https://efoliknot.net/, and the source code is hosted on GitHub: 
https://github.com/aritheman88/efoliknot/

## Project Structure

```
leaflet/
│
├── css/
│   └── styles.css        # Styles for the map and UI
│
├── data/
│   ├── stores_map_sample.csv         # Sample CSV data
│   ├── store_price_comparisons.csv   # Main CSV data source
│   ├── stores.geojson                # Generated GeoJSON from CSV
│   └── store_files/                  # Directory for individual store price JSON files
│
├── img/                 # Image assets directory
│   ├── lobby99 water.png             # Organization logo
│   ├── ramiLevi.png                  # Supermarket chain logos
│   ├── shufersal.png
│   ├── victory.png
│   └── ...                           # Other chain logos
│
├── js/
│   └── map.js           # Main JavaScript for the interactive map
│
├── index.html           # Main HTML page (in the root directory)
├── csv_to_geojson.py    # Python script to convert CSV to GeoJSON
└── README.md            # This documentation file
```

## Setup Instructions

1. **Prepare your data**:
   - Place your CSV file in the `data` directory
   - Make sure it has the required columns (latitude, longitude, etc.)
   - Add supermarket chain logos to the `img` directory (PNG format recommended)

2. **Convert CSV data to GeoJSON**:
   Run the Python script from the leaflet directory:
   ```
   python csv_to_geojson.py
   ```
   This will create `data/stores.geojson` that the map will use.

3. **Start a local server**:
   You need a local web server to properly load the GeoJSON data. You can use Python's built-in HTTP server:
   ```
   python -m http.server
   ```
   Then open `http://localhost:8000` in your browser.

## Features

- **Interactive Map**: View all supermarkets across Israel with custom markers
- **Clustering**: Markers are clustered for better performance and readability
- **Detailed Information**: Click on markers to view detailed store information
- **Chain Logos**: Displays supermarket chain logos in store details and popups
- **Advanced Filtering**:
  - Filter by supermarket chain
  - Filter by city
  - Filter by maximum price difference percentage (filter out expensive stores)
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

## Customization

- **Styles**: Modify the CSS in `css/styles.css` to change the appearance
- **Map Settings**: Adjust the map configuration in `js/map.js`
- **Adding Data**: Convert additional data using the Python script
- **Adding Layers**: Modify the JavaScript to include additional map layers
- **Chain Logos**: Add more supermarket chain logos to the `img` directory and update the `chainLogos` mapping in `map.js`
- **Price Difference Thresholds**: Modify the color thresholds in the relevant functions in `map.js`
- **Legend**: Customize the legend in `index.html` and its toggle behavior in the accompanying JavaScript

## CSS Organization

The stylesheet is organized into logical sections:

1. **Global/Reset Styles**: Basic styles that apply to the entire application
2. **Layout/Structure**: Styles for the container, header, content areas
3. **Component-Specific Styles**: Styles for filters, map elements, popups, etc.
4. **Utility Classes**: Reusable styles for common patterns
5. **Media Queries**: Responsive design adjustments for different screen sizes

When modifying the CSS, maintain this organization to keep the code clean and maintainable.

## Future Enhancements

Potential improvements to consider:
- Implementing a search function for specific stores
- Adding data layers for different time periods
- Creating a heatmap view based on price differences
- Adding route planning to the nearest cheaper store
- Implementing user accounts for saving favorite stores
- Adding a comparison feature to directly compare prices between two stores
- Developing a mobile app version for offline use

## Hosting

To make this map publicly available through your organization's website:

1. Upload all files to your web server
2. Ensure the server allows access to the data files
3. Update any relative paths if necessary

## Dependencies

- [Leaflet](https://leafletjs.com/): Open-source JavaScript library for interactive maps
- [Leaflet.markercluster](https://github.com/Leaflet/Leaflet.markercluster): Plugin for clustering markers
- [Font Awesome](https://fontawesome.com/): Icon library for user interface elements

## License

All rights reserved. Based on publicly available price data from supermarket chains.
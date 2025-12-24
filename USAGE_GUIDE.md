# Quick Usage Guide: update_popular_items_view.py

## What This Script Does

The `update_popular_items_view.py` script updates the database view that determines which items are considered "popular" in your price comparison system. An item is "popular" when it appears in a minimum number of stores (e.g., 10+ stores).

This view is crucial because:
- It defines the baseline for price comparisons
- Only popular items are used to calculate average prices
- This ensures fair comparisons across stores

## When to Use This Script

Run this script whenever you:
- Get new price data for a different date
- Want to change the "popularity" threshold (minimum stores)
- Need to refresh the baseline price calculations

## Basic Usage

### Option 1: Interactive Mode (Easiest)

Simply run the script without any arguments:

```bash
python update_popular_items_view.py
```

The script will prompt you for:
1. Upload date (format: YYYY-MM-DD)
2. Minimum stores threshold (e.g., 10)
3. Whether you want a dry run (test mode)

### Option 2: Command-Line Arguments (Fastest)

Specify everything on the command line:

```bash
python update_popular_items_view.py --date 2025-11-02 --min-stores 10
```

Or using short form:

```bash
python update_popular_items_view.py -d 2025-11-02 -m 10
```

## Common Use Cases

### 1. Weekly Update with Standard Settings

When you get new data every week:

```bash
python update_popular_items_view.py -d 2025-11-10 -m 10
```

### 2. Testing Changes Before Applying

Use dry-run mode to preview the SQL without executing:

```bash
python update_popular_items_view.py --dry-run -d 2025-11-10 -m 10
```

This shows you exactly what SQL will be executed without making any changes.

### 3. Stricter Popular Items (More Stores)

If you want only items that appear in many stores:

```bash
python update_popular_items_view.py -d 2025-11-10 -m 15
```

This requires items to appear in at least 15 stores to be considered "popular".

### 4. More Inclusive (Fewer Stores)

If you want to include more items:

```bash
python update_popular_items_view.py -d 2025-11-10 -m 5
```

This considers items "popular" if they appear in just 5+ stores.

## Understanding the Parameters

### Date (`--date` or `-d`)

- **Format**: YYYY-MM-DD (e.g., 2025-11-02)
- **What it does**: Tells the system which day's price data to use
- **Important**: Make sure this date exists in your `allprices` table

### Minimum Stores (`--min-stores` or `-m`)

- **Format**: Positive integer (e.g., 10)
- **What it does**: Sets the threshold for "popular" items
- **Examples**:
  - `10` = Item must be in 10+ stores
  - `15` = Stricter, item must be in 15+ stores
  - `5` = More inclusive, item must be in 5+ stores

**Trade-offs**:
- **Higher values (15+)**: 
  - Fewer items in baseline
  - More reliable averages (wider distribution)
  - May miss regional variations
  
- **Lower values (5-8)**:
  - More items in baseline
  - Captures more products
  - May include less widely-available items

## What Happens When You Run It

1. **Validation**: Script validates your inputs
2. **Connection**: Connects to your PostgreSQL database
3. **Confirmation**: Asks for confirmation (unless dry-run)
4. **Execution**: Updates the `popular_items_avg_prices` view
5. **Verification**: Checks the view was created successfully
6. **Summary**: Shows count of popular items and sample data

## Example Output

```
============================================================
Updating popular_items_avg_prices view
============================================================
Date: 2025-11-02
Minimum stores threshold: 10
Dry run: False
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
  - 7290000066691: יוגורט טבעי 5% 500 גרם (avg: ₪4.80)
  - 7290000114972: גבינה צהובה 28% 200 גרם (avg: ₪9.50)

============================================================
Update completed successfully!
============================================================
```

## Troubleshooting

### Error: "Invalid date format"

Make sure your date is in YYYY-MM-DD format:
- ✓ Correct: `2025-11-02`
- ✗ Wrong: `02/11/2025`
- ✗ Wrong: `11-02-2025`

### Error: "Minimum stores must be at least 1"

The minimum stores value must be a positive integer:
- ✓ Correct: `10`
- ✗ Wrong: `0`
- ✗ Wrong: `-5`

### Error: "Database connection failed"

Check your `.env` file and make sure:
- All database credentials are correct
- The database server is accessible
- Your IP is allowed by AWS security groups

### No Items Found

If the view has 0 items, check:
- Does the date exist in your `allprices` table?
- Is the minimum stores threshold too high?
- Try with `--min-stores 5` to be more inclusive

## Best Practices

1. **Always test first**: Use `--dry-run` to preview changes
2. **Consistent dates**: Use the same date across all your scripts
3. **Standard threshold**: Stick with 10 stores unless you have a good reason to change
4. **Document changes**: Keep track of which parameters you used
5. **Run regularly**: Update weekly (or whenever you get new data)

## Integration with Other Scripts

After updating the view, run these scripts in order:

1. **Update view** (this script):
   ```bash
   python update_popular_items_view.py -d 2025-11-10 -m 10
   ```

2. **Export to CSV**:
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

## Command-Line Help

Get full help text anytime:

```bash
python update_popular_items_view.py --help
```

This shows all available options and examples.

## Security Notes

- The script uses **parameterized queries** to prevent SQL injection
- All database credentials are loaded from `.env` file
- Never commit your `.env` file to git
- The script requires confirmation before making changes (unless dry-run)

---

**Need Help?**

If you encounter any issues:
1. Check the error message carefully
2. Try dry-run mode first
3. Verify your database connection with `python debug_database.py`
4. Review the full README.md for more details

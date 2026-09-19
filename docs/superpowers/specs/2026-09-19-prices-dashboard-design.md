# Prices Dashboard Design

## Goal

Build a simple Streamlit dashboard for fertilizer/commodity prices where the changing data lives outside the application code. The dashboard must visualize historical and current price data by month/year, and new rows added to the live data source must appear in the dashboard without requiring code changes.

## Current Repository State

The repository currently contains price data files under `data/` but no Streamlit application code. Existing CSVs use the schema:

- `Date`
- `Commodity`
- `Price`
- `Unit`
- `Source`
- `Retrieved_At`

Existing data includes one-year and current-month files for Urea and Sulfur, plus `data/trading_economics_prices.xlsx`.

## Architecture

### 1. Live data source

Use Google Sheets as the preferred live source of truth for dashboard data. Streamlit will read a published CSV endpoint configured through an environment variable / Streamlit secret named `GOOGLE_SHEET_CSV_URL`.

If `GOOGLE_SHEET_CSV_URL` is missing or cannot be loaded, the application will fall back to the repository files under `data/` so the dashboard still runs.

No Postgres, Supabase, or additional database layer is required.

### 2. Canonical data shape

All loaded data will be normalized to these columns:

- `Date` — parsed as a real date
- `Commodity` — e.g. Urea or Sulfur
- `Price` — numeric
- `Unit` — e.g. USD/T or CNY/T
- `Source` — source URL or source name
- `Retrieved_At` — optional timestamp

The loader must also create derived fields used by the dashboard:

- `Year`
- `Month`
- `Month_Start`

If input data already contains separate `Year` and `Month` fields rather than a `Date`, the loader will construct `Date`/`Month_Start` from them. If `Date` exists, the year and month are derived from it.

### 3. Deduplication

When one-year and current-month files overlap, duplicate observations must not appear twice. The canonical deduplication key is:

`Commodity + Date + Unit`

For duplicate keys, keep the most recently loaded/available observation.

### 4. Dashboard views

The Streamlit application will provide:

- Commodity selector
- Unit-aware latest price metric
- Latest observation date
- One-year historical line chart
- Current-month line chart
- Monthly trend chart using month/year on the x-axis
- Data table showing the filtered underlying rows

The app will not combine commodities with incompatible units on a single y-axis. Urea and Sulfur are shown separately when their units differ.

### 5. Month/year visualization

Monthly visualization will be calculated from the normalized data. For daily observations, the dashboard will aggregate each commodity/month to the monthly mean price for the chart while preserving the daily records in the detailed table.

The month/year x-axis will be chronological, not alphabetical.

### 6. Google Sheets workflow

The live Sheet should use the same canonical column names whenever possible. A practical row looks like:

`2026-09-19 | Urea | 450.25 | USD/T | Trading Economics | 2026-09-19T15:00:00`

When a user appends another row, Streamlit will retrieve the updated sheet on refresh after its short cache expires. No Git commit is needed for ordinary price updates.

GitHub stores application code and backup data; Google Sheets stores frequently changing price rows.

### 7. Caching and refresh

Use Streamlit caching with a short TTL of 300 seconds via the supported `@st.cache_data(ttl=300)` form. Do not use the invalid `ttl_seconds` argument that previously caused the dashboard error.

Provide a visible `Refresh data` button that clears cached data and reruns the app immediately.

### 8. Failure behavior

If Google Sheets is unavailable:

1. Show a small warning that backup repository data is being used.
2. Load the local CSV/Excel backup data.
3. Keep the dashboard usable.

Malformed rows with invalid dates or non-numeric prices should be excluded from charts instead of crashing the application.

### 9. Files to create

Expected implementation structure:

- `app.py` — Streamlit UI and chart composition
- `price_data.py` — loading, normalization, deduplication, monthly aggregation
- `requirements.txt` — Streamlit/pandas/openpyxl/plotting dependencies
- `tests/test_price_data.py` — data behavior tests
- `.streamlit/secrets.toml.example` — example configuration only; never commit real secrets

Existing files in `data/` remain as backups.

## Testing Requirements

Automated tests must cover at least:

- Parsing current CSV schema
- Deriving month/year from `Date`
- Constructing dates from `Year` + `Month`
- Deduplicating overlapping one-year/current-month rows
- Monthly aggregation ordering
- Ignoring invalid price/date rows
- Falling back to repository data when the live Sheet is unavailable

Before completion, run the complete test suite and verify the Streamlit application imports successfully.

## Out of Scope

- Database infrastructure
- Authentication or user accounts
- Editing Google Sheets from within Streamlit
- Paid API integration
- Automated scraping inside the Streamlit process
- Power BI integration in this iteration

## Success Criteria

The feature is complete when a new valid price row added to the configured Google Sheet appears in the Streamlit dashboard after refresh/cache expiry; the charts show month/year chronologically; existing repository data is usable as backup; and the application continues to run when the live Sheet is unavailable.

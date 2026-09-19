# prices_dashboard

Streamlit dashboard for Urea and Sulfur prices.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Live Google Sheets data

The preferred live data source is a Google Sheet with these columns:

| Date | Commodity | Price | Unit | Source | Retrieved_At |
|---|---|---:|---|---|---|
| 2026-09-19 | Urea | 450.25 | USD/T | Trading Economics | 2026-09-19T15:00:00 |

The dashboard also accepts rows that use `Year` and `Month` instead of `Date`.

For a Sheet that can be read through a CSV export URL, use:

```text
https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv&gid=0
```

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and set:

```toml
GOOGLE_SHEET_CSV_URL = "YOUR_GOOGLE_SHEET_CSV_URL"
```

Do not commit `.streamlit/secrets.toml`.

After adding a new row to the Sheet, click **Refresh data** in the dashboard or allow the 5-minute cache to expire. No GitHub commit is needed for ordinary price updates.

## Backup data

If Google Sheets is unavailable or not configured, the app loads compatible CSV/XLSX files from `data/` and deduplicates overlapping observations.

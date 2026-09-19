# prices_dashboard

Streamlit dashboard for commodity prices stored directly in this GitHub repository.

## Run locally

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

## Add today's prices

Run:

```bash
python3 add_today_prices.py
```

The script asks for:

- Date (press Enter to use today's date)
- Urea price in USD/T
- Sulfur price in CNY/T

It writes two Excel files:

- `data/commodity_prices.xlsx` — master history that keeps all entered dates
- `data/latest_prices.xlsx` — only the rows entered in the latest run

If you enter the same date again, the script replaces that date's Urea/Sulfur values instead of creating duplicates.

Example:

```text
Date [2026-09-19]:
Urea price (USD/T): 451.25
Sulfur price (CNY/T): 7687.33
```

Then push the updated Excel files to GitHub:

```bash
git add data/commodity_prices.xlsx data/latest_prices.xlsx
git commit -m "data: update commodity prices"
git push
```

The dashboard reads compatible CSV/XLSX files from `data/`, combines them, and deduplicates overlapping observations by commodity, date, and unit.

## Dashboard refresh

After updating the repository data, restart Streamlit or click **Refresh data** in the dashboard. The app caches data for up to five minutes.

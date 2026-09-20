# prices_dashboard

Streamlit dashboard for commodity prices stored directly in this GitHub repository.

## 1. Pull the latest code

From the project folder:

```bash
cd /Users/macbookpro/Desktop/CIRAT/Prices/prices_dashboard
git pull
```

If you are working on the dashboard feature branch:

```bash
git switch feat/streamlit-prices-dashboard
git pull origin feat/streamlit-prices-dashboard
```

## 2. Update today's prices

Run:

```bash
python3 add_today_prices.py
```

The script asks for:

- Date — press Enter to use today's date
- Urea price in USD/T
- Sulfur price in CNY/T

Example:

```text
Date [2026-09-19]:
Urea price (USD/T): 451.25
Sulfur price (CNY/T): 7687.33
```

The script updates:

- `data/commodity_prices.xlsx` — full price history
- `data/latest_prices.xlsx` — only the latest entered prices

If the same date is entered again, that day's values are replaced instead of duplicated.

## 3. Save the new price data to GitHub

After entering the prices:

```bash
git add data/commodity_prices.xlsx data/latest_prices.xlsx
git commit -m "data: update commodity prices"
git push
```

That is the normal daily price-update workflow.

## 4. Merge new dashboard/code changes into `main`

When changes on `feat/streamlit-prices-dashboard` are ready to become the main version:

```bash
git switch main
git pull origin main
git merge feat/streamlit-prices-dashboard
git push origin main
```

After that, `main` contains the newest dashboard code and data workflow.

If Git reports a merge conflict, resolve the conflicting file first, then run:

```bash
git add .
git commit
git push origin main
```

## 5. Open the Streamlit dashboard

Install dependencies the first time:

```bash
python3 -m pip install -r requirements.txt
```

Start the dashboard:

```bash
python3 -m streamlit run app.py
```

Streamlit normally opens automatically in the browser. If it does not, open:

```text
http://localhost:8501
```

## Daily workflow

Most days, you only need these commands:

```bash
python3 add_today_prices.py
git add data/commodity_prices.xlsx data/latest_prices.xlsx
git commit -m "data: update commodity prices"
git push
python3 -m streamlit run app.py
```

The dashboard reads the compatible CSV/XLSX files inside `data/` and uses the newest value for duplicate commodity/date/unit combinations.

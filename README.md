# prices_dashboard

Streamlit dashboard for commodity prices stored directly in this GitHub repository.

## Dashboards

The Streamlit app now has two data views:

- **Commodity Prices Dashboard** — existing Urea and Sulfur monitoring.
- **USDA Fertilizer Prices** — automated USDA AMS Production Cost data with product and reporting-region filters.

The USDA page supports Urea, DAP, MAP, Potash, Ammonium Sulfate, Anhydrous Ammonia, Ammonium Nitrate, ATS, and UAN concentrations when those products are present in USDA reports.

## USDA fertilizer automation

USDA data is collected from the MyMarketNews MARS API and stored in:

```text
data/usda_fertilizer_prices.csv
```

The collector checks the current USDA Production Cost reports for Alabama, Illinois, Maryland, Inter-Mountain West, Iowa, North Carolina, Oklahoma, Pacific Northwest, Pennsylvania, and South Carolina. It keeps regional observations separate and deduplicates on date + region + fertilizer + unit.

### Local setup

Create your private environment file once:

```bash
cp .env.example .env
```

Then open `.env` and replace the placeholder:

```text
USDA_API_KEY=your_real_key_here
```

`.env` is ignored by Git and must never be committed.

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Fetch/update USDA fertilizer data:

```bash
python3 fetch_usda_prices.py
```

By default the script requests the most recent 60 days from each report, merges them with existing history, and replaces matching regional observations rather than duplicating them.

To request a wider window:

```bash
python3 fetch_usda_prices.py --days 180
```

### GitHub Actions automation

The workflow `.github/workflows/update_usda_fertilizer.yml` runs once per day and can also be started manually from the Actions tab.

Before the workflow can call USDA, add a repository Actions secret named exactly:

```text
USDA_API_KEY
```

The workflow then:

```text
GitHub Actions
   ↓
USDA MyMarketNews API
   ↓
fetch_usda_prices.py
   ↓
data/usda_fertilizer_prices.csv
   ↓
commit only when data changed
   ↓
Streamlit redeploys from GitHub
```

Scheduled GitHub Actions workflows run from the repository default branch, so the daily schedule becomes active after this feature is merged to `main`.

## Daily manual Urea + Sulfur workflow

From the repository on the `main` branch, run these two commands in this order:

```bash
git pull
python3 add_today_prices.py
```

Then enter the date, Urea price, and Sulfur price.

Example:

```text
Date [2026-09-20]:
Urea price (USD/T): 459.60
Sulfur price (CNY/T): 7669
```

After you enter the prices, the script automatically:

1. updates `data/commodity_prices.xlsx` with the full manual history
2. updates `data/latest_prices.xlsx` with the latest entered prices
3. commits only those two price files
4. rebases automatically if GitHub `main` changed
5. pushes the new price data to GitHub `main`
6. triggers Streamlit Cloud to redeploy from the updated GitHub repository

You do **not** need to run `git add`, `git commit`, `git push`, or another `git pull` after entering the prices.

The workflow is therefore:

```text
git pull
   ↓
python3 add_today_prices.py
   ↓
enter Urea + Sulfur prices
   ↓
Excel files update automatically
   ↓
GitHub main updates automatically
   ↓
Streamlit Cloud redeploys automatically
   ↓
Dashboard shows the newest date and prices
```

When the script finishes successfully, look for:

```text
GitHub sync: pushed to main successfully.
Streamlit Cloud will redeploy from the new GitHub data automatically.
```

If the same date is entered again, that date's manual values are replaced instead of duplicated.

The dashboard gives manual price data priority over the older backup CSV/XLSX files for the same commodity/date/unit. This means the newest manually entered date and price are used throughout the dashboard, including:

- Latest Price KPI
- Previous Price KPI
- Current Month Average
- Current Month High / Low
- Current Month chart
- Latest observation date
- Data tables

After the GitHub push, Streamlit Cloud may need a short time to redeploy. Refresh the deployed dashboard after the redeploy completes.

## Pull the latest code manually

If you ever need to make sure your local copy has the newest code:

```bash
git switch main
git pull origin main
```

## Run Streamlit locally

Install dependencies once:

```bash
python3 -m pip install -r requirements.txt
```

Run:

```bash
python3 -m streamlit run app.py
```

Local URL:

```text
http://localhost:8501
```

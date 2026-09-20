# prices_dashboard

Streamlit dashboard for commodity prices stored directly in this GitHub repository.

## Update today's prices

From the repository on the `main` branch, run:

```bash
python3 add_today_prices.py
```

Enter the date, Urea price, and Sulfur price. The script will automatically:

1. update `data/commodity_prices.xlsx` (full manual history)
2. update `data/latest_prices.xlsx` (latest entered date)
3. commit only those two data files
4. pull/rebase if GitHub `main` moved
5. push the price update to GitHub `main`
6. trigger Streamlit Cloud to redeploy from the updated repository

If the same date is entered again, that date's manual values are replaced instead of duplicated.

Example:

```text
Date [2026-09-20]:
Urea price (USD/T): 459.60
Sulfur price (CNY/T): 7669
```

When the script finishes successfully, look for:

```text
GitHub sync: pushed to main successfully.
Streamlit Cloud will redeploy from the new GitHub data automatically.
```

The dashboard gives manual data explicit priority over legacy backup files for the same commodity/date/unit, so the newly entered date and price are used in the KPI cards, current-month chart, and data tables.

## Pull the latest code

If needed:

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

## Normal daily workflow

Most days there is now only one command:

```bash
python3 add_today_prices.py
```

After the automatic GitHub push, Streamlit Cloud may take a short time to redeploy. Refresh the deployed dashboard after the redeploy completes.

# prices_dashboard

Streamlit dashboard for monitoring Urea, Sulfur, and fertilizer prices stored directly in this GitHub repository.

The repository supports:

- Urea and Sulfur manual price updates
- FertilizerPrice.com national fertilizer history
- Optional regional fertilizer observations
- Streamlit dashboards for historical trends and current prices
- Automatic GitHub commits/pushes from the price-update script
- Automatic Streamlit Cloud redeployment after new price data is pushed

## Tracked commodities

The dashboard currently supports:

- Urea
- Sulfur
- UAN 28%
- Anhydrous Ammonia
- DAP
- MAP
- Potash (MOP)
- Ammonium Sulfate (AMS)
- Liquid Phosphate 10-34-0 when observations are available

Urea can appear under more than one unit/source. For example:

- `USD/T` = the existing manually maintained Urea series
- `USD/short ton` = FertilizerPrice.com fertilizer series

These are intentionally kept separate so prices with different units are never mixed together.

---

# Quick start

If the repository is already cloned on your computer, go into the project folder and make sure you are on the newest `main` branch:

```bash
git switch main
git pull origin main
```

Install dependencies if needed:

```bash
python3 -m pip install -r requirements.txt
```

Run the dashboard locally:

```bash
python3 -m streamlit run app.py
```

Local URL:

```text
http://localhost:8501
```

---

# Normal price-update workflow

The main command used to update prices is:

```bash
python3 add_today_prices.py
```

Before running it, pull the newest version of `main`:

```bash
git switch main
git pull origin main
python3 add_today_prices.py
```

The update script saves the data locally, commits only the relevant price files, rebases automatically if GitHub changed, and pushes the new data to `main`.

You normally do **not** need to run `git add`, `git commit`, or `git push` yourself after the script completes successfully.

---

# Step 1 — Update Urea and Sulfur

When you run:

```bash
python3 add_today_prices.py
```

the script first asks for the date and the two original price series.

Example:

```text
Date [2026-09-28]:
Urea price (USD/T): 459.60
Sulfur price (CNY/T): 7669
```

These values update:

```text
data/commodity_prices.xlsx
data/latest_prices.xlsx
```

`commodity_prices.xlsx` stores the ongoing manual history.

`latest_prices.xlsx` stores the newest entered values and receives priority in the dashboard for the same commodity/date/unit.

If you enter the same date again, the previous value for that commodity/date/unit is replaced instead of duplicated.

---

# Step 2 — Update national fertilizer prices

After Urea and Sulfur, the script asks whether you want to update FertilizerPrice.com fertilizer prices.

You will see something similar to:

```text
Update FertilizerPrice.com fertilizer prices too? [Y/n]:
```

Press **Enter** or type `y` to continue.

The script then asks for the national average price for each supported fertilizer:

```text
Urea [blank = skip]:
UAN 28% [blank = skip]:
Anhydrous Ammonia [blank = skip]:
DAP [blank = skip]:
MAP [blank = skip]:
Potash (MOP) [blank = skip]:
Ammonium Sulfate (AMS) [blank = skip]:
Liquid Phosphate 10-34-0 [blank = skip]:
```

Enter only values that are actually available from the source.

If a product does not have a new observation, press **Enter** and leave it blank.

Do **not** copy the previous value just to fill the field. Missing observations should stay missing.

National fertilizer prices are stored in:

```text
data/fertilizer_prices.csv
```

The fertilizer series uses:

```text
USD/short ton
```

and is kept separate from the original Urea `USD/T` series.

---

# Step 3 — Optional regional fertilizer prices

After national prices, the script asks whether you want to enter regional observations.

Example:

```text
Add/update regional fertilizer observations? [y/N]:
```

If you do not have regional data, press **Enter** or type `n`.

If you type `y`, you can enter observations for supported regions such as:

- Corn Belt
- Southern Plains
- Southeast
- Delta States
- Mountain
- Pacific
- Northeast

Only enter regions and products for which FertilizerPrice.com actually publishes an observation.

Regional coverage is not identical for every fertilizer. Blank values are expected and should not be replaced with estimates.

Regional fertilizer data is stored in:

```text
regional_data/fertilizer_regional_prices.csv
```

---

# Files updated by the script

Depending on what you enter, `add_today_prices.py` can update these files:

```text
data/commodity_prices.xlsx
data/latest_prices.xlsx
data/fertilizer_prices.csv
regional_data/fertilizer_regional_prices.csv
```

The script only commits the price-data files that changed.

It does not intentionally commit unrelated local edits.

---

# Automatic GitHub sync

After prices are saved, the updater automatically attempts to sync them to GitHub `main`.

The workflow is:

```text
git pull
   ↓
python3 add_today_prices.py
   ↓
enter Urea + Sulfur
   ↓
optionally enter national fertilizer prices
   ↓
optionally enter regional fertilizer prices
   ↓
price files update locally
   ↓
script commits changed price files
   ↓
script rebases if remote main changed
   ↓
script pushes to GitHub main
   ↓
Streamlit Cloud redeploys
```

When the sync succeeds, look for a message similar to:

```text
GitHub sync: pushed to main successfully.
Streamlit Cloud will redeploy from the new GitHub data automatically.
```

If there were no actual price-file changes, the script can instead report that there was nothing new to push.

---

# Dashboard pages

## Main commodity dashboard

Run:

```bash
python3 -m streamlit run app.py
```

The main dashboard lets you choose a commodity from the sidebar and view:

- Latest price
- Previous price
- Price change
- Current-month average
- Current-month high and low
- Historical price trend
- Current-month chart
- Underlying observations
- Source and unit filters when applicable

Because different Urea series use different units, use the unit selector to choose the series you want to inspect.

## Regional Fertilizer Prices

The Streamlit sidebar also includes the regional fertilizer page.

This page uses:

```text
regional_data/fertilizer_regional_prices.csv
```

It lets you compare the latest available fertilizer observations across supported U.S. regions.

Regional gaps are legitimate missing source data, not dashboard errors.

---

# Historical fertilizer data

Historical FertilizerPrice.com national observations are stored in:

```text
data/fertilizer_prices.csv
```

The dashboard loads repository data automatically, so newly appended fertilizer observations become part of the historical charts after they are committed and pulled/deployed.

The project does not interpolate missing fertilizer prices.

If the source has no observation for a product/date, the dataset should remain blank for that product/date.

---

# Most common daily/weekly routine

For normal use, these are the main commands:

```bash
cd /path/to/prices_dashboard
git switch main
git pull origin main
python3 add_today_prices.py
python3 -m streamlit run app.py
```

If you only want to update GitHub/Streamlit Cloud and do not need to inspect the dashboard locally, you can stop after:

```bash
git switch main
git pull origin main
python3 add_today_prices.py
```

---

# First-time setup on a new computer

Clone the repository:

```bash
git clone https://github.com/Misha200304/prices_dashboard.git
cd prices_dashboard
```

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Run the application:

```bash
python3 -m streamlit run app.py
```

---

# If your local repository is behind GitHub

Run:

```bash
git switch main
git pull origin main
```

Then update prices normally:

```bash
python3 add_today_prices.py
```

---

# If the automatic GitHub push fails

Your price files are saved locally before the GitHub sync step.

First check your current branch:

```bash
git branch --show-current
```

The updater expects:

```text
main
```

Then pull/rebase and inspect the repository:

```bash
git pull --rebase --autostash origin main
git status
```

If necessary, rerun:

```bash
python3 add_today_prices.py
```

Do not blindly force-push the repository.

---

# Running tests

To verify the repository after changing code:

```bash
pytest
```

The tests cover the main price loader, update behavior, Git sync behavior, fertilizer helpers, and fertilizer update integration.

---

# Data-source rules

When updating the repository:

1. Preserve the original units.
2. Do not convert `USD/T` into `USD/short ton` unless an explicit conversion is intentionally added to the project.
3. Do not invent missing observations.
4. Do not carry forward an old fertilizer price just because a new observation is missing.
5. National and regional observations should remain distinguishable.
6. Use the source's actual observation date whenever possible.
7. If correcting the same commodity/date/unit, rerunning the updater should replace that observation rather than create a duplicate.

---

# Repository structure

Important files:

```text
app.py                                      Main Streamlit commodity dashboard
add_today_prices.py                         Interactive price updater + Git sync
price_data.py                               Main repository price loader/normalizer
fertilizer_data.py                          Fertilizer national/regional data helpers
pages/2_Regional_Fertilizer_Prices.py       Regional fertilizer Streamlit page

data/commodity_prices.xlsx                 Manual Urea/Sulfur history
data/latest_prices.xlsx                     Latest manual Urea/Sulfur observations
data/fertilizer_prices.csv                  National fertilizer history
regional_data/fertilizer_regional_prices.csv Regional fertilizer observations

tests/                                      Automated tests
```

---

# Short version

For day-to-day work:

```bash
git switch main
git pull origin main
python3 add_today_prices.py
```

To view everything locally afterward:

```bash
python3 -m streamlit run app.py
```

That is the standard workflow for keeping the repository, GitHub dashboard data, regional fertilizer data, and Streamlit deployment up to date.

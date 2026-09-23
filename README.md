# prices_dashboard

Streamlit dashboard for commodity prices stored directly in this GitHub repository.

The dashboard now combines the existing Urea/Sulfur data with a simple FertilizerPrice.com weekly history file. There is no USDA API, API key, `.env`, scraper, or scheduled fertilizer job.

## FertilizerPrice history

`data/fertilizerprice_history.csv` contains the national weekly fertilizer averages that FertilizerPrice.com publicly published in its market reports within the current one-year window. The public weekly report series currently starts on April 3, 2026, so no earlier weekly values were invented to fill the chart.

Tracked products are:

- Urea
- UAN 28%
- UAN 32%
- Anhydrous Ammonia
- DAP
- MAP
- Potash (MOP)
- Ammonium Sulfate (AMS)
- Liquid Phosphate 10-34-0 when a value is available

The FertilizerPrice observations use `USD/short ton`, which keeps them distinct from the older Urea series already in the repository.

Source pages:

- https://fertilizerprice.com/trends
- https://fertilizerprice.com/news

## Weekly fertilizer update

Once per week, open FertilizerPrice.com and enter the newest national averages manually:

```bash
git pull
python3 add_fertilizer_prices.py
```

The script asks for the report date and each fertilizer price. Press Enter to skip any product that is not reported that week. If the same product/date already exists, the new value replaces it instead of creating a duplicate.

After the script saves the CSV, push the new data:

```bash
git add data/fertilizerprice_history.csv
git commit -m "data: update fertilizer prices YYYY-MM-DD"
git push
```

Streamlit Cloud can then redeploy from the updated repository and the new weekly point will appear in the same commodity dashboard.

## Existing daily Urea/Sulfur workflow

From the repository on the `main` branch:

```bash
git pull
python3 add_today_prices.py
```

Enter the date, Urea price, and Sulfur price. That script automatically updates:

- `data/commodity_prices.xlsx`
- `data/latest_prices.xlsx`

and then commits and pushes those two files to `main`.

If the same date is entered again, that date's manual values are replaced rather than duplicated.

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

## Normal routines

For the existing daily Urea/Sulfur series:

```bash
git pull
python3 add_today_prices.py
```

For the fertilizer report, normally once per week:

```bash
git pull
python3 add_fertilizer_prices.py
```

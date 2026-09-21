"""One-off builder: convert scraped FertilizerPrice.com JSON into the canonical
dashboard CSV schema. Run once to (re)generate data/fertilizer_prices.csv."""
import json, csv
from pathlib import Path

RAW = Path("/Users/macbookpro/Desktop/fertilizer_prices/trends_ALL_raw.json")
OUT = Path(__file__).parent / "data" / "fertilizer_prices.csv"

# Map site slugs -> display names the user wants in the dashboard dropdown
DISPLAY = {
    "urea": "Urea",
    "uan-28": "UAN 28%",
    "uan-32": "UAN 32%",
    "anhydrous-ammonia": "Anhydrous Ammonia",
    "dap": "DAP",
    "map": "MAP",
    "potash-mop": "Potash",
    "ams": "AMS",
    "10-34-0": "Liquid Phosphate",
}
UNIT = "USD/short ton"
SOURCE = "FertilizerPrice.com"

data = json.load(open(RAW))
rows = []
for p in data:
    name = DISPLAY.get(p["slug"], p["name"])
    for r in p["data"]:
        rows.append({
            "Date": r["price_date"],
            "Commodity": name,
            "Price": r["price_per_ton"],
            "Unit": UNIT,
            "Source": SOURCE,
            "Retrieved_At": "2026-09-21T00:00:00",
        })

rows.sort(key=lambda r: (r["Date"], r["Commodity"]))
OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["Date","Commodity","Price","Unit","Source","Retrieved_At"])
    w.writeheader()
    w.writerows(rows)

print(f"Wrote {len(rows)} rows to {OUT}")
from collections import Counter
c = Counter(r["Commodity"] for r in rows)
for name in DISPLAY.values():
    print(f"  {name}: {c.get(name,0)} points")

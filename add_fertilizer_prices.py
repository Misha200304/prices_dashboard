from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Mapping

import pandas as pd

DATA_FILE = Path("data/fertilizerprice_history.csv")
UNIT = "USD/short ton"
SOURCE = "FertilizerPrice.com manual weekly update"

PRODUCTS = [
    "Urea",
    "UAN 28%",
    "UAN 32%",
    "Anhydrous Ammonia",
    "DAP",
    "MAP",
    "Potash (MOP)",
    "Ammonium Sulfate (AMS)",
]


def build_weekly_rows(
    price_date: str,
    prices: Mapping[str, float | None],
) -> pd.DataFrame:
    day = pd.to_datetime(price_date, errors="raise").normalize()
    retrieved_at = datetime.now().replace(microsecond=0).isoformat()

    rows = []
    for commodity, raw_price in prices.items():
        if raw_price is None:
            continue
        price = float(raw_price)
        if price <= 0:
            raise ValueError(f"{commodity} price must be greater than 0")
        rows.append(
            {
                "Date": day,
                "Commodity": str(commodity).strip(),
                "Price": price,
                "Unit": UNIT,
                "Source": SOURCE,
                "Retrieved_At": retrieved_at,
            }
        )

    return pd.DataFrame(
        rows,
        columns=["Date", "Commodity", "Price", "Unit", "Source", "Retrieved_At"],
    )


def update_fertilizer_history(
    new_rows: pd.DataFrame,
    output_path: str | Path = DATA_FILE,
) -> pd.DataFrame:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if output.exists():
        history = pd.read_csv(output)
    else:
        history = pd.DataFrame(columns=new_rows.columns)

    combined = pd.concat([history, new_rows], ignore_index=True)
    combined["Date"] = pd.to_datetime(combined["Date"], errors="coerce")
    combined["Price"] = pd.to_numeric(combined["Price"], errors="coerce")
    combined = combined.dropna(subset=["Date", "Commodity", "Price", "Unit"])

    combined = (
        combined.drop_duplicates(
            subset=["Commodity", "Date", "Unit"],
            keep="last",
        )
        .sort_values(["Date", "Commodity"])
        .reset_index(drop=True)
    )
    combined.to_csv(output, index=False, date_format="%Y-%m-%d")
    return combined


def _ask_optional_price(label: str) -> float | None:
    while True:
        raw = input(f"{label} ({UNIT}) [blank = skip]: ").strip()
        if not raw:
            return None
        try:
            value = float(raw.replace(",", ""))
        except ValueError:
            print("Please enter a number, for example 907.80, or press Enter to skip.")
            continue
        if value <= 0:
            print("Price must be greater than 0.")
            continue
        return value


def main() -> None:
    today = date.today().isoformat()
    entered_date = input(f"Report date [{today}]: ").strip() or today
    try:
        pd.to_datetime(entered_date, errors="raise")
    except Exception as exc:
        raise SystemExit("Invalid date. Use YYYY-MM-DD, for example 2026-09-25.") from exc

    print("\nEnter the national average prices shown on FertilizerPrice.com.")
    print("Press Enter for any product that is not reported that week.\n")

    prices = {product: _ask_optional_price(product) for product in PRODUCTS}
    rows = build_weekly_rows(entered_date, prices)
    if rows.empty:
        raise SystemExit("No prices entered; nothing was changed.")

    history = update_fertilizer_history(rows)
    print(f"\nSaved {len(rows)} weekly observations to {DATA_FILE}.")
    print(f"History now contains {len(history)} rows.")
    print("\nNext, commit and push the updated CSV so the Streamlit dashboard refreshes:")
    print("  git add data/fertilizerprice_history.csv")
    print(f"  git commit -m \"data: update fertilizer prices {entered_date}\"")
    print("  git push")


if __name__ == "__main__":
    main()

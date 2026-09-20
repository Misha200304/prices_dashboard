from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd

DATA_DIR = Path("data")
MASTER_FILE = DATA_DIR / "commodity_prices.xlsx"
LATEST_FILE = DATA_DIR / "latest_prices.xlsx"


def build_daily_rows(
    price_date: str,
    urea_price: float,
    sulfur_price: float,
) -> pd.DataFrame:
    day = pd.to_datetime(price_date, errors="raise").normalize()
    retrieved_at = datetime.now().replace(microsecond=0).isoformat()

    return pd.DataFrame(
        [
            {
                "Date": day,
                "Commodity": "Urea",
                "Price": float(urea_price),
                "Unit": "USD/T",
                "Source": "Manual entry",
                "Retrieved_At": retrieved_at,
            },
            {
                "Date": day,
                "Commodity": "Sulfur",
                "Price": float(sulfur_price),
                "Unit": "CNY/T",
                "Source": "Manual entry",
                "Retrieved_At": retrieved_at,
            },
        ]
    )


def update_excel_files(
    new_rows: pd.DataFrame,
    master_path: str | Path = MASTER_FILE,
    latest_path: str | Path = LATEST_FILE,
) -> pd.DataFrame:
    master_path = Path(master_path)
    latest_path = Path(latest_path)
    master_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.parent.mkdir(parents=True, exist_ok=True)

    if master_path.exists():
        history = pd.read_excel(master_path)
    else:
        history = pd.DataFrame(columns=new_rows.columns)

    if history.empty:
        combined = new_rows.copy()
    else:
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

    latest = new_rows.copy()
    latest["Date"] = pd.to_datetime(latest["Date"], errors="raise")

    combined.to_excel(master_path, index=False)
    latest.to_excel(latest_path, index=False)
    return combined


def _ask_price(label: str) -> float:
    while True:
        raw = input(f"{label}: ").strip()
        try:
            value = float(raw)
        except ValueError:
            print("Please enter a number, for example 451.25")
            continue

        if value <= 0:
            print("Price must be greater than 0.")
            continue
        return value


def main() -> None:
    today = date.today().isoformat()
    entered_date = input(f"Date [{today}]: ").strip() or today

    try:
        pd.to_datetime(entered_date, errors="raise")
    except Exception:
        raise SystemExit("Invalid date. Use YYYY-MM-DD, for example 2026-09-19.")

    urea_price = _ask_price("Urea price (USD/T)")
    sulfur_price = _ask_price("Sulfur price (CNY/T)")

    rows = build_daily_rows(entered_date, urea_price, sulfur_price)
    history = update_excel_files(rows)

    print("\nSaved successfully.")
    print(f"Master history: {MASTER_FILE}")
    print(f"Today's output: {LATEST_FILE}")
    print(f"Total history rows: {len(history)}")
    print("\nRows added/updated:")
    print(rows.to_string(index=False))


if __name__ == "__main__":
    main()

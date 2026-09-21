"""Manual weekly updater for FertilizerPrice.com fertilizer data.

Usage:
    python3 add_fertilizer_prices.py

It asks for one date, then walks through every fertilizer product. Press Enter
on any product to skip it (no new price available). Entering the same
Date + Commodity + Unit again replaces the existing observation instead of
creating a duplicate.

This script intentionally does NOT commit or push anything. It only updates
data/fertilizer_prices.csv locally. Run it on the feature branch, inspect the
diff, then commit manually.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd

DATA_DIR = Path("data")
FERTILIZER_FILE = DATA_DIR / "fertilizer_prices.csv"

UNIT = "USD/short ton"
SOURCE = "FertilizerPrice.com"

# Display name -> site slug, in the order shown to the user.
FERTILIZER_PRODUCTS: list[tuple[str, str]] = [
    ("Urea", "urea"),
    ("UAN 28%", "uan-28"),
    ("UAN 32%", "uan-32"),
    ("Anhydrous Ammonia", "anhydrous-ammonia"),
    ("DAP", "dap"),
    ("MAP", "map"),
    ("Potash", "potash-mop"),
    ("AMS", "ams"),
    ("Liquid Phosphate", "10-34-0"),
]


def build_new_rows(
    price_date: str,
    entries: dict[str, float],
) -> pd.DataFrame:
    """Build normalized new-observation rows for one date.

    entries maps a display product name to a positive float price. Products
    not in entries (or with non-positive values) are simply omitted, which is
    how "press Enter to skip" is represented.
    """
    day = pd.to_datetime(price_date, errors="raise").normalize()
    retrieved_at = datetime.now().replace(microsecond=0).isoformat()

    rows: list[dict] = []
    for display_name, _slug in FERTILIZER_PRODUCTS:
        if display_name not in entries:
            continue
        value = entries[display_name]
        if value is None or value <= 0:
            continue
        rows.append(
            {
                "Date": day,
                "Commodity": display_name,
                "Price": float(value),
                "Unit": UNIT,
                "Source": SOURCE,
                "Retrieved_At": retrieved_at,
            }
        )
    return pd.DataFrame(rows, columns=["Date", "Commodity", "Price", "Unit", "Source", "Retrieved_At"])


def update_fertilizer_csv(
    new_rows: pd.DataFrame,
    file_path: str | Path = FERTILIZER_FILE,
) -> pd.DataFrame:
    """Merge new_rows into the fertilizer CSV, replacing same Date+Commodity+Unit.

    Returns the full sorted history that was written back to disk.
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if file_path.exists():
        history = pd.read_csv(file_path)
    else:
        history = pd.DataFrame(
            columns=["Date", "Commodity", "Price", "Unit", "Source", "Retrieved_At"]
        )

    if new_rows.empty or history.empty:
        combined = new_rows.copy() if history.empty else history.copy()
    else:
        combined = pd.concat([history, new_rows], ignore_index=True)

    combined["Date"] = pd.to_datetime(combined["Date"], errors="coerce")
    combined["Price"] = pd.to_numeric(combined["Price"], errors="coerce")
    combined = combined.dropna(subset=["Date", "Commodity", "Price", "Unit"])

    # Replace existing observation for the same Date + Commodity + Unit.
    combined = (
        combined.drop_duplicates(
            subset=["Commodity", "Date", "Unit"],
            keep="last",
        )
        .sort_values(["Date", "Commodity"])
        .reset_index(drop=True)
    )

    combined.to_csv(file_path, index=False)
    return combined


def _ask_date(default_today: str) -> str:
    while True:
        raw = input(f"Date [{default_today}]: ").strip() or default_today
        try:
            pd.to_datetime(raw, errors="raise")
            return raw
        except Exception:
            print("Invalid date. Use YYYY-MM-DD, for example 2026-09-26.")


def _ask_price(label: str) -> float | None:
    """Return a positive float, or None when the user presses Enter to skip."""
    while True:
        raw = input(f"{label} (USD/short ton, Enter to skip): ").strip()
        if raw == "":
            return None
        try:
            value = float(raw)
        except ValueError:
            print("Please enter a number, for example 907.80")
            continue
        if value <= 0:
            print("Price must be greater than 0.")
            continue
        return value


def main() -> None:
    today = date.today().isoformat()
    entered_date = _ask_date(today)

    entries: dict[str, float] = {}
    print(
        "\nEnter the newest weekly price for each fertilizer in USD/short ton."
        "\nPress Enter to skip a product if no new price is available.\n"
    )
    for display_name, _slug in FERTILIZER_PRODUCTS:
        price = _ask_price(display_name)
        if price is not None:
            entries[display_name] = price

    if not entries:
        print("\nNo prices entered. Nothing to update.")
        return

    new_rows = build_new_rows(entered_date, entries)
    history = update_fertilizer_csv(new_rows, FERTILIZER_FILE)

    print("\nSaved successfully.")
    print(f"File: {FERTILIZER_FILE}")
    print(f"Total fertilizer history rows: {len(history)}")
    print("\nRows added/updated:")
    print(new_rows.to_string(index=False))
    print("\nNo git commit or push was performed. Inspect the diff and commit manually.")


if __name__ == "__main__":
    main()
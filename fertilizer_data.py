from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

FERTILIZER_PRODUCTS = [
    "Urea",
    "UAN 28%",
    "Anhydrous Ammonia",
    "DAP",
    "MAP",
    "Potash (MOP)",
    "Ammonium Sulfate (AMS)",
    "Liquid Phosphate 10-34-0",
]

REGIONS = [
    "Corn Belt",
    "Southern Plains",
    "Southeast",
    "Delta States",
    "Mountain",
    "Pacific",
    "Northeast",
]

NATIONAL_UNIT = "USD/short ton"
DEFAULT_SOURCE = "FertilizerPrice.com"


def _retrieved_at() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def build_fertilizer_rows(
    price_date: str,
    prices: dict[str, float | None],
    source: str = DEFAULT_SOURCE,
) -> pd.DataFrame:
    day = pd.to_datetime(price_date, errors="raise").normalize()
    retrieved_at = _retrieved_at()
    rows: list[dict[str, object]] = []
    for product in FERTILIZER_PRODUCTS:
        value = prices.get(product)
        if value is None:
            continue
        rows.append(
            {
                "Date": day,
                "Commodity": product,
                "Price": float(value),
                "Unit": NATIONAL_UNIT,
                "Source": source,
                "Retrieved_At": retrieved_at,
            }
        )
    return pd.DataFrame(
        rows,
        columns=["Date", "Commodity", "Price", "Unit", "Source", "Retrieved_At"],
    )


def build_regional_rows(
    price_date: str,
    region_prices: dict[str, dict[str, float | None]],
    source: str = DEFAULT_SOURCE,
) -> pd.DataFrame:
    day = pd.to_datetime(price_date, errors="raise").normalize()
    retrieved_at = _retrieved_at()
    rows: list[dict[str, object]] = []
    for region in REGIONS:
        product_prices = region_prices.get(region, {})
        for product in FERTILIZER_PRODUCTS:
            value = product_prices.get(product)
            if value is None:
                continue
            rows.append(
                {
                    "Date": day,
                    "Commodity": product,
                    "Region": region,
                    "Price": float(value),
                    "Unit": NATIONAL_UNIT,
                    "Source": source,
                    "Retrieved_At": retrieved_at,
                }
            )
    return pd.DataFrame(
        rows,
        columns=["Date", "Commodity", "Region", "Price", "Unit", "Source", "Retrieved_At"],
    )


def update_csv_history(
    new_rows: pd.DataFrame,
    path: str | Path,
    dedupe_columns: Iterable[str],
) -> pd.DataFrame:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        history = pd.read_csv(path)
    else:
        history = pd.DataFrame(columns=new_rows.columns)

    if history.empty:
        combined = new_rows.copy()
    elif new_rows.empty:
        combined = history.copy()
    else:
        combined = pd.concat([history, new_rows], ignore_index=True)

    if "Date" in combined.columns:
        combined["Date"] = pd.to_datetime(combined["Date"], errors="coerce")
    if "Price" in combined.columns:
        combined["Price"] = pd.to_numeric(combined["Price"], errors="coerce")

    required = [column for column in ["Date", "Commodity", "Price", "Unit"] if column in combined.columns]
    if required:
        combined = combined.dropna(subset=required)

    combined = combined.drop_duplicates(subset=list(dedupe_columns), keep="last")
    sort_columns = [column for column in ["Date", "Commodity", "Region"] if column in combined.columns]
    if sort_columns:
        combined = combined.sort_values(sort_columns)
    combined = combined.reset_index(drop=True)

    combined.to_csv(path, index=False, date_format="%Y-%m-%d")
    return combined

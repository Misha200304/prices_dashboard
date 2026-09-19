from __future__ import annotations

import pandas as pd

CANONICAL_COLUMNS = [
    "Date",
    "Commodity",
    "Price",
    "Unit",
    "Source",
    "Retrieved_At",
]


def normalize_prices(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()

    if "Date" not in work.columns:
        if not {"Year", "Month"}.issubset(work.columns):
            raise ValueError("Input must contain Date or both Year and Month columns")
        work["Date"] = pd.to_datetime(
            {
                "year": pd.to_numeric(work["Year"], errors="coerce"),
                "month": pd.to_numeric(work["Month"], errors="coerce"),
                "day": 1,
            },
            errors="coerce",
        )
    else:
        work["Date"] = pd.to_datetime(work["Date"], errors="coerce")

    work["Price"] = pd.to_numeric(work.get("Price"), errors="coerce")

    for column in ["Commodity", "Unit", "Source", "Retrieved_At"]:
        if column not in work.columns:
            work[column] = pd.NA

    work = work.dropna(subset=["Date", "Commodity", "Price", "Unit"]).copy()
    work["Year"] = work["Date"].dt.year
    work["Month"] = work["Date"].dt.month
    work["Month_Start"] = work["Date"].dt.to_period("M").dt.to_timestamp()

    ordered = CANONICAL_COLUMNS + ["Year", "Month", "Month_Start"]
    return work[ordered].reset_index(drop=True)


def combine_price_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    normalized = [normalize_prices(frame) for frame in frames if frame is not None and not frame.empty]
    if not normalized:
        return pd.DataFrame(columns=CANONICAL_COLUMNS + ["Year", "Month", "Month_Start"])

    combined = pd.concat(normalized, ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["Commodity", "Date", "Unit"],
        keep="last",
    )
    return combined.sort_values(["Commodity", "Date"]).reset_index(drop=True)


def monthly_prices(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Commodity", "Unit", "Month_Start", "Price"])

    result = (
        df.groupby(["Commodity", "Unit", "Month_Start"], as_index=False)["Price"]
        .mean()
        .sort_values(["Commodity", "Unit", "Month_Start"])
        .reset_index(drop=True)
    )
    return result

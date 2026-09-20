from __future__ import annotations

from pathlib import Path

import pandas as pd

CANONICAL_COLUMNS = [
    "Date",
    "Commodity",
    "Price",
    "Unit",
    "Source",
    "Retrieved_At",
]

DERIVED_COLUMNS = ["Year", "Month", "Month_Start"]
ALL_COLUMNS = CANONICAL_COLUMNS + DERIVED_COLUMNS


def empty_prices() -> pd.DataFrame:
    return pd.DataFrame(columns=ALL_COLUMNS)


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
        work["Date"] = pd.to_datetime(work["Date"], errors="coerce", format="mixed")

    if "Price" not in work.columns:
        raise ValueError("Input must contain Price")
    work["Price"] = pd.to_numeric(work["Price"], errors="coerce")

    for column in ["Commodity", "Unit", "Source", "Retrieved_At"]:
        if column not in work.columns:
            work[column] = pd.NA

    work = work.dropna(subset=["Date", "Commodity", "Price", "Unit"]).copy()
    work["Commodity"] = work["Commodity"].astype(str).str.strip()
    work["Unit"] = work["Unit"].astype(str).str.strip()
    work = work.loc[(work["Commodity"] != "") & (work["Unit"] != "")].copy()

    work["Year"] = work["Date"].dt.year.astype("int64")
    work["Month"] = work["Date"].dt.month.astype("int64")
    work["Month_Start"] = work["Date"].dt.to_period("M").dt.to_timestamp()

    return work[ALL_COLUMNS].reset_index(drop=True)


def combine_price_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    normalized: list[pd.DataFrame] = []
    for frame in frames:
        if frame is None or frame.empty:
            continue
        try:
            clean = normalize_prices(frame)
        except (ValueError, KeyError, TypeError):
            continue
        if not clean.empty:
            normalized.append(clean)

    if not normalized:
        return empty_prices()

    combined = pd.concat(normalized, ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["Commodity", "Date", "Unit"],
        keep="last",
    )
    return combined.sort_values(["Commodity", "Date", "Unit"]).reset_index(drop=True)


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


def load_live_sheet(sheet_url: str) -> pd.DataFrame:
    return normalize_prices(pd.read_csv(sheet_url))


def load_repository_data(data_dir: str | Path = "data") -> pd.DataFrame:
    root = Path(data_dir)
    if not root.exists():
        return empty_prices()

    frames: list[pd.DataFrame] = []

    csv_paths = sorted(
        root.glob("*.csv"),
        key=lambda p: ("current_month" in p.stem.lower(), p.name.lower()),
    )
    for path in csv_paths:
        try:
            frames.append(pd.read_csv(path))
        except Exception:
            continue

    def excel_priority(path: Path) -> tuple[int, str]:
        name = path.name.lower()
        if name == "latest_prices.xlsx":
            return (2, name)
        if name == "commodity_prices.xlsx":
            return (1, name)
        return (0, name)

    for path in sorted(root.glob("*.xlsx"), key=excel_priority):
        try:
            workbook = pd.read_excel(path, sheet_name=None)
        except Exception:
            continue
        for frame in workbook.values():
            if not isinstance(frame, pd.DataFrame) or frame.empty:
                continue
            if "Date" in frame.columns or {"Year", "Month"}.issubset(frame.columns):
                frames.append(frame)

    return combine_price_frames(frames)


def load_prices(
    sheet_url: str | None,
    data_dir: str | Path = "data",
) -> tuple[pd.DataFrame, str]:
    if sheet_url:
        try:
            live = load_live_sheet(sheet_url)
            if not live.empty:
                return live, "google_sheets"
        except Exception:
            pass

    return load_repository_data(data_dir), "repository_backup"

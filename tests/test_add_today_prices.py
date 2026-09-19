from pathlib import Path

import pandas as pd

from add_today_prices import build_daily_rows, update_excel_files


def test_build_daily_rows_creates_urea_and_sulfur_rows():
    rows = build_daily_rows("2026-09-19", 451.25, 7687.33)

    assert rows["Commodity"].tolist() == ["Urea", "Sulfur"]
    assert rows["Price"].tolist() == [451.25, 7687.33]
    assert rows["Unit"].tolist() == ["USD/T", "CNY/T"]
    assert rows["Date"].tolist() == [pd.Timestamp("2026-09-19"), pd.Timestamp("2026-09-19")]


def test_update_excel_files_appends_history_and_writes_latest(tmp_path: Path):
    master = tmp_path / "commodity_prices.xlsx"
    latest = tmp_path / "latest_prices.xlsx"

    first = build_daily_rows("2026-09-18", 450.0, 7600.0)
    second = build_daily_rows("2026-09-19", 451.25, 7687.33)

    update_excel_files(first, master, latest)
    result = update_excel_files(second, master, latest)

    assert len(result) == 4
    assert master.exists()
    assert latest.exists()

    latest_df = pd.read_excel(latest)
    assert len(latest_df) == 2
    assert set(latest_df["Commodity"]) == {"Urea", "Sulfur"}


def test_update_excel_files_replaces_same_date_instead_of_duplicating(tmp_path: Path):
    master = tmp_path / "commodity_prices.xlsx"
    latest = tmp_path / "latest_prices.xlsx"

    original = build_daily_rows("2026-09-19", 451.25, 7687.33)
    corrected = build_daily_rows("2026-09-19", 455.0, 7700.0)

    update_excel_files(original, master, latest)
    result = update_excel_files(corrected, master, latest)

    assert len(result) == 2
    urea = result.loc[result["Commodity"] == "Urea", "Price"].iloc[0]
    sulfur = result.loc[result["Commodity"] == "Sulfur", "Price"].iloc[0]
    assert urea == 455.0
    assert sulfur == 7700.0

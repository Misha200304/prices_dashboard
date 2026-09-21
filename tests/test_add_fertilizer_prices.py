from pathlib import Path

import pandas as pd

from add_fertilizer_prices import build_new_rows, update_fertilizer_csv, UNIT, SOURCE


def test_build_new_rows_only_includes_entered_products():
    entries = {"Urea": 907.80, "DAP": 760.0}
    rows = build_new_rows("2026-09-18", entries)
    assert rows["Commodity"].tolist() == ["Urea", "DAP"]
    assert rows["Price"].tolist() == [907.80, 760.0]
    assert (rows["Unit"] == UNIT).all()
    assert (rows["Source"] == SOURCE).all()
    assert rows["Date"].tolist() == [pd.Timestamp("2026-09-18"), pd.Timestamp("2026-09-18")]


def test_build_new_rows_skips_non_positive_prices():
    rows = build_new_rows("2026-09-18", {"Urea": 907.80, "DAP": 0, "MAP": -5})
    # Only the positive entry survives.
    assert rows["Commodity"].tolist() == ["Urea"]


def test_update_replaces_same_date_commodity_unit(tmp_path: Path):
    csv_path = tmp_path / "fertilizer_prices.csv"
    first = build_new_rows("2026-09-18", {"Urea": 907.80})
    update_fertilizer_csv(first, csv_path)
    corrected = build_new_rows("2026-09-18", {"Urea": 912.50})
    history = update_fertilizer_csv(corrected, csv_path)
    urea_rows = history.loc[history["Commodity"] == "Urea"]
    assert len(urea_rows) == 1
    assert urea_rows["Price"].iloc[0] == 912.50


def test_update_keeps_different_dates_and_skipped_products(tmp_path: Path):
    csv_path = tmp_path / "fertilizer_prices.csv"
    week1 = build_new_rows("2026-09-11", {"Urea": 900.0, "DAP": 750.0})
    update_fertilizer_csv(week1, csv_path)
    # Urea skipped (Enter to skip), only DAP entered for the new week.
    week2 = build_new_rows("2026-09-18", {"DAP": 760.0})
    history = update_fertilizer_csv(week2, csv_path)
    assert len(history) == 3
    assert set(history["Commodity"].unique()) == {"Urea", "DAP"}
    # Urea still only has the week-1 observation.
    assert history.loc[history["Commodity"] == "Urea", "Date"].iloc[0] == pd.Timestamp("2026-09-11")
    # DAP has both weeks.
    dap_dates = history.loc[history["Commodity"] == "DAP", "Date"].tolist()
    assert dap_dates == [pd.Timestamp("2026-09-11"), pd.Timestamp("2026-09-18")]


def test_update_no_duplicate_date_commodity_unit(tmp_path: Path):
    csv_path = tmp_path / "fertilizer_prices.csv"
    first = build_new_rows("2026-09-18", {"Urea": 907.80, "DAP": 760.0})
    update_fertilizer_csv(first, csv_path)
    # Re-enter the same date/products with new prices.
    second = build_new_rows("2026-09-18", {"Urea": 910.0, "DAP": 765.0})
    history = update_fertilizer_csv(second, csv_path)
    dupes = history.duplicated(subset=["Commodity", "Date", "Unit"]).sum()
    assert dupes == 0
    assert len(history) == 2


def test_fertilizer_urea_does_not_mix_with_other_unit(tmp_path: Path):
    """FertilizerPrice Urea (USD/short ton) and Trading Economics Urea (USD/T)
    coexist without colliding, because the dedup key includes Unit."""
    csv_path = tmp_path / "fertilizer_prices.csv"
    # Seed with a Trading-Economics-style Urea row in a different unit.
    other = pd.DataFrame(
        {
            "Date": ["2026-09-18"],
            "Commodity": ["Urea"],
            "Price": [459.6],
            "Unit": ["USD/T"],
            "Source": ["tradingeconomics.com"],
        }
    )
    other.to_csv(csv_path, index=False)
    fert = build_new_rows("2026-09-18", {"Urea": 907.80})
    history = update_fertilizer_csv(fert, csv_path)
    urea = history.loc[history["Commodity"] == "Urea"]
    # Both unit groups survive.
    assert set(urea["Unit"].unique()) == {"USD/T", "USD/short ton"}
    assert len(urea) == 2
    assert dup_count(history) == 0


def dup_count(df: pd.DataFrame) -> int:
    return int(df.duplicated(subset=["Commodity", "Date", "Unit"]).sum())
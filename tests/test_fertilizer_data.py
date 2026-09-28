from pathlib import Path

from fertilizer_data import (
    FERTILIZER_PRODUCTS,
    REGIONS,
    build_fertilizer_rows,
    build_regional_rows,
    update_csv_history,
)


def test_build_fertilizer_rows_skips_missing_prices():
    rows = build_fertilizer_rows(
        "2026-09-25",
        {"Urea": 800.0, "DAP": 790.0, "MAP": None},
    )
    assert rows["Commodity"].tolist() == ["Urea", "DAP"]
    assert rows["Unit"].tolist() == ["USD/short ton", "USD/short ton"]
    assert rows["Price"].tolist() == [800.0, 790.0]


def test_build_regional_rows_preserves_region_dimension():
    rows = build_regional_rows(
        "2026-09-25",
        {"Corn Belt": {"Urea": 720.0, "DAP": 930.0}},
    )
    assert rows[["Commodity", "Region", "Price"]].to_dict("records") == [
        {"Commodity": "Urea", "Region": "Corn Belt", "Price": 720.0},
        {"Commodity": "DAP", "Region": "Corn Belt", "Price": 930.0},
    ]


def test_update_csv_history_replaces_same_observation(tmp_path: Path):
    path = tmp_path / "fertilizer_prices.csv"
    first = build_fertilizer_rows("2026-09-25", {"Urea": 800.0})
    corrected = build_fertilizer_rows("2026-09-25", {"Urea": 805.0})
    update_csv_history(first, path, ["Commodity", "Date", "Unit"])
    result = update_csv_history(corrected, path, ["Commodity", "Date", "Unit"])
    assert len(result) == 1
    assert result.iloc[0]["Price"] == 805.0


def test_product_and_region_lists_cover_dashboard_options():
    assert FERTILIZER_PRODUCTS == [
        "Urea",
        "UAN 28%",
        "Anhydrous Ammonia",
        "DAP",
        "MAP",
        "Potash (MOP)",
        "Ammonium Sulfate (AMS)",
        "Liquid Phosphate 10-34-0",
    ]
    assert "Corn Belt" in REGIONS
    assert "Northeast" in REGIONS

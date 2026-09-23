from pathlib import Path

import pandas as pd

from add_fertilizer_prices import (
    PRODUCTS,
    build_weekly_rows,
    update_fertilizer_history,
)


def test_weekly_updater_includes_all_trends_products():
    assert "Liquid Phosphate 10-34-0" in PRODUCTS


def test_build_weekly_rows_keeps_only_entered_products():
    rows = build_weekly_rows(
        "2026-09-25",
        {
            "Urea": 910.25,
            "DAP": 955.00,
            "MAP": None,
        },
    )

    assert rows["Commodity"].tolist() == ["Urea", "DAP"]
    assert rows["Price"].tolist() == [910.25, 955.00]
    assert set(rows["Unit"]) == {"USD/short ton"}
    assert set(rows["Source"]) == {"FertilizerPrice.com manual weekly update"}


def test_update_fertilizer_history_replaces_same_date_product(tmp_path: Path):
    output = tmp_path / "fertilizerprice_history.csv"
    pd.DataFrame(
        [
            {
                "Date": "2026-09-18",
                "Commodity": "Urea",
                "Price": 900.0,
                "Unit": "USD/short ton",
                "Source": "old",
                "Retrieved_At": "2026-09-18T12:00:00",
            }
        ]
    ).to_csv(output, index=False)

    new_rows = build_weekly_rows("2026-09-18", {"Urea": 907.80})
    combined = update_fertilizer_history(new_rows, output)

    assert len(combined) == 1
    assert combined.iloc[0]["Price"] == 907.80
    assert combined.iloc[0]["Source"] == "FertilizerPrice.com manual weekly update"

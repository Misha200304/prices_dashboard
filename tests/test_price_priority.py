from pathlib import Path

import pandas as pd

from price_data import load_repository_data


def test_manual_latest_file_wins_over_legacy_files(tmp_path: Path):
    legacy = pd.DataFrame(
        {
            "Date": ["2026-09-20"],
            "Commodity": ["Urea"],
            "Price": [440.0],
            "Unit": ["USD/T"],
            "Source": ["legacy"],
        }
    )
    master = pd.DataFrame(
        {
            "Date": ["2026-09-20"],
            "Commodity": ["Urea"],
            "Price": [455.0],
            "Unit": ["USD/T"],
            "Source": ["Manual entry"],
        }
    )
    latest = pd.DataFrame(
        {
            "Date": ["2026-09-20"],
            "Commodity": ["Urea"],
            "Price": [459.6],
            "Unit": ["USD/T"],
            "Source": ["Manual entry"],
        }
    )

    legacy.to_excel(tmp_path / "trading_economics_prices.xlsx", index=False)
    master.to_excel(tmp_path / "commodity_prices.xlsx", index=False)
    latest.to_excel(tmp_path / "latest_prices.xlsx", index=False)

    result = load_repository_data(tmp_path)
    row = result.loc[
        (result["Commodity"] == "Urea")
        & (result["Date"] == pd.Timestamp("2026-09-20"))
    ].iloc[0]

    assert row["Price"] == 459.6
    assert row["Source"] == "Manual entry"

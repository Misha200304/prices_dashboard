import pandas as pd

from price_data import normalize_prices


def test_normalize_derives_year_month_and_month_start_from_date():
    raw = pd.DataFrame({
        "Date": ["2026-09-19"],
        "Commodity": ["Urea"],
        "Price": [450.25],
        "Unit": ["USD/T"],
        "Source": ["Trading Economics"],
        "Retrieved_At": ["2026-09-19T15:00:00"],
    })

    result = normalize_prices(raw)

    assert result.loc[0, "Date"] == pd.Timestamp("2026-09-19")
    assert result.loc[0, "Year"] == 2026
    assert result.loc[0, "Month"] == 9
    assert result.loc[0, "Month_Start"] == pd.Timestamp("2026-09-01")


def test_normalize_constructs_date_from_year_and_month():
    raw = pd.DataFrame({
        "Year": [2026],
        "Month": [9],
        "Commodity": ["Urea"],
        "Price": [450.25],
        "Unit": ["USD/T"],
        "Source": ["Manual"],
    })

    result = normalize_prices(raw)

    assert result.loc[0, "Date"] == pd.Timestamp("2026-09-01")
    assert result.loc[0, "Month_Start"] == pd.Timestamp("2026-09-01")


def test_normalize_drops_invalid_date_and_price_rows():
    raw = pd.DataFrame({
        "Date": ["bad-date", "2026-09-19", "2026-09-20"],
        "Commodity": ["Urea", "Urea", "Urea"],
        "Price": [100, "not-a-number", 450.25],
        "Unit": ["USD/T", "USD/T", "USD/T"],
        "Source": ["x", "x", "x"],
    })

    result = normalize_prices(raw)

    assert len(result) == 1
    assert result.iloc[0]["Price"] == 450.25

from price_data import combine_price_frames, monthly_prices


def test_combine_deduplicates_and_later_frame_wins():
    older = pd.DataFrame({
        "Date": ["2026-09-19"],
        "Commodity": ["Urea"],
        "Price": [440.0],
        "Unit": ["USD/T"],
        "Source": ["older"],
    })
    newer = pd.DataFrame({
        "Date": ["2026-09-19"],
        "Commodity": ["Urea"],
        "Price": [450.25],
        "Unit": ["USD/T"],
        "Source": ["newer"],
    })

    result = combine_price_frames([older, newer])

    assert len(result) == 1
    assert result.iloc[0]["Price"] == 450.25
    assert result.iloc[0]["Source"] == "newer"


def test_monthly_prices_are_chronological_across_year_boundary():
    raw = pd.DataFrame({
        "Date": ["2026-01-10", "2025-12-10", "2025-11-10"],
        "Commodity": ["Urea", "Urea", "Urea"],
        "Price": [300, 200, 100],
        "Unit": ["USD/T", "USD/T", "USD/T"],
        "Source": ["x", "x", "x"],
    })

    result = monthly_prices(normalize_prices(raw))

    assert result["Month_Start"].tolist() == [
        pd.Timestamp("2025-11-01"),
        pd.Timestamp("2025-12-01"),
        pd.Timestamp("2026-01-01"),
    ]

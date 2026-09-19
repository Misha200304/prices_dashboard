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


from pathlib import Path

from price_data import load_prices, load_repository_data


def test_repository_loader_combines_csv_files_and_deduplicates(tmp_path: Path):
    one_year = pd.DataFrame({
        "Date": ["2026-09-18", "2026-09-19"],
        "Commodity": ["Urea", "Urea"],
        "Price": [440.0, 445.0],
        "Unit": ["USD/T", "USD/T"],
        "Source": ["history", "history"],
    })
    current = pd.DataFrame({
        "Date": ["2026-09-19"],
        "Commodity": ["Urea"],
        "Price": [450.25],
        "Unit": ["USD/T"],
        "Source": ["current"],
    })
    one_year.to_csv(tmp_path / "urea_1y.csv", index=False)
    current.to_csv(tmp_path / "urea_current_month.csv", index=False)

    result = load_repository_data(tmp_path)

    assert len(result) == 2
    assert result.loc[result["Date"] == pd.Timestamp("2026-09-19"), "Price"].iloc[0] == 450.25


def test_load_prices_falls_back_when_live_loader_fails(monkeypatch, tmp_path: Path):
    backup = pd.DataFrame({
        "Date": ["2026-09-19"],
        "Commodity": ["Urea"],
        "Price": [450.25],
        "Unit": ["USD/T"],
        "Source": ["backup"],
    })
    backup.to_csv(tmp_path / "urea.csv", index=False)

    def boom(url):
        raise RuntimeError("sheet unavailable")

    monkeypatch.setattr("price_data.load_live_sheet", boom)

    result, source = load_prices("https://example.invalid/sheet.csv", tmp_path)

    assert source == "repository_backup"
    assert len(result) == 1


def test_load_prices_falls_back_when_live_sheet_has_bad_schema(monkeypatch, tmp_path: Path):
    backup = pd.DataFrame({
        "Date": ["2026-09-19"],
        "Commodity": ["Sulfur"],
        "Price": [3000.0],
        "Unit": ["CNY/T"],
        "Source": ["backup"],
    })
    backup.to_csv(tmp_path / "sulfur.csv", index=False)

    real_read_csv = pd.read_csv

    def fake_read_csv(target, *args, **kwargs):
        if isinstance(target, str) and target.startswith("https://"):
            return pd.DataFrame({"SomethingElse": [1]})
        return real_read_csv(target, *args, **kwargs)

    monkeypatch.setattr("price_data.pd.read_csv", fake_read_csv)

    result, source = load_prices("https://example.com/sheet.csv", tmp_path)

    assert source == "repository_backup"
    assert result.iloc[0]["Commodity"] == "Sulfur"

from pathlib import Path

import pandas as pd

from usda_auth import validate_api_key
from usda_fertilizer import (
    extract_price_rows,
    merge_history,
    normalize_product,
)


def test_normalize_product_keeps_core_fertilizer_classes():
    assert normalize_product("Urea (46-0-0)") == "Urea"
    assert normalize_product("DAP (Diammonium Phosphate 18-46-0)") == "DAP"
    assert normalize_product("MAP (Monoammonium Phosphate 11-52-0)") == "MAP"
    assert normalize_product("Potash (Red 0-0-60)") == "Potash"
    assert normalize_product("Ammonium Sulfate") == "Ammonium Sulfate"
    assert normalize_product("Anhydrous Ammonia") == "Anhydrous Ammonia"
    assert normalize_product("Liquid Nitrogen (32-0-0)") == "UAN 32-0-0"


def test_normalize_product_rejects_non_fertilizer_rows():
    assert normalize_product("No. 2 Diesel (Farm)") is None
    assert normalize_product("Propane") is None
    assert normalize_product("Lime") is None


def test_extract_price_rows_parses_nested_usda_payload_and_filters_fuels():
    payload = {
        "reportSection": "Fertilizer (Synthetic)",
        "results": [
            {
                "report_begin_date": "09/18/2026",
                "class": "Urea (46-0-0)",
                "price_range": "825.00 - 970.00",
                "average": "897.50",
                "change": "(5.00)",
                "freight": "F.O.B.",
                "delivery_period": "Current",
            },
            {
                "report_begin_date": "09/18/2026",
                "class": "No. 2 Diesel (Farm)",
                "price_range": "4.41 - 4.99",
                "average": "4.56",
                "change": "0.13",
            },
        ],
    }

    result = extract_price_rows(
        payload,
        region="North Carolina",
        slug_id=3159,
        retrieved_at="2026-09-21T16:00:00",
    )

    assert len(result) == 1
    row = result.iloc[0]
    assert row["Date"] == pd.Timestamp("2026-09-18")
    assert row["Commodity"] == "Urea"
    assert row["Price"] == 897.50
    assert row["Low"] == 825.00
    assert row["High"] == 970.00
    assert row["Reported_Change"] == -5.00
    assert row["Region"] == "North Carolina"
    assert row["Slug_ID"] == 3159
    assert row["Unit"] == "USD/T"
    assert row["Freight"] == "F.O.B."


def test_extract_price_rows_inherits_date_from_parent_record():
    payload = {
        "report_begin_date": "09/04/2026",
        "reportSections": [
            {
                "name": "Fertilizer (Synthetic)",
                "results": [
                    {
                        "class": "Potash (Red 0-0-60)",
                        "low": "500.00",
                        "high": "590.00",
                        "average": "528.60",
                        "change": "4.17",
                    }
                ],
            }
        ],
    }

    result = extract_price_rows(
        payload,
        region="Alabama",
        slug_id=3051,
        retrieved_at="2026-09-21T16:00:00",
    )

    assert len(result) == 1
    row = result.iloc[0]
    assert row["Date"] == pd.Timestamp("2026-09-04")
    assert row["Commodity"] == "Potash"
    assert row["Low"] == 500.0
    assert row["High"] == 590.0


def test_merge_history_replaces_same_region_product_date_without_duplicates(tmp_path: Path):
    output = tmp_path / "usda_fertilizer_prices.csv"

    old = pd.DataFrame(
        [
            {
                "Date": "2026-09-18",
                "Commodity": "Urea",
                "Price": 890.0,
                "Low": 820.0,
                "High": 960.0,
                "Reported_Change": 0.0,
                "Unit": "USD/T",
                "Region": "North Carolina",
                "Source": "USDA AMS",
                "Slug_ID": 3159,
                "Source_URL": "https://mymarketnews.ams.usda.gov/viewReport/3159",
                "Freight": "F.O.B.",
                "Delivery_Period": "Current",
                "Retrieved_At": "2026-09-19T12:00:00",
            }
        ]
    )
    old.to_csv(output, index=False)

    new = old.copy()
    new.loc[0, "Price"] = 897.5
    new.loc[0, "Retrieved_At"] = "2026-09-21T16:00:00"

    merged = merge_history(new, output)

    assert len(merged) == 1
    assert merged.iloc[0]["Price"] == 897.5
    assert merged.iloc[0]["Retrieved_At"] == "2026-09-21T16:00:00"


class _FakeResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeSession:
    def __init__(self, status_code: int):
        self.status_code = status_code
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _FakeResponse(self.status_code)


def test_validate_api_key_reports_401_as_credentials_problem():
    session = _FakeSession(401)

    try:
        validate_api_key(session, "example-key")
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected invalid USDA credentials to raise RuntimeError")

    assert "401" in message
    assert "USDA_API_KEY" in message
    assert "MyMarketNews" in message
    assert session.calls[0][1]["auth"] == ("example-key", "")

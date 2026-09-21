from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import re
from typing import Any, Iterable, Mapping
from urllib.parse import quote

import pandas as pd
import requests

API_BASE = "https://marsapi.ams.usda.gov/services/v1.2/reports"
DEFAULT_OUTPUT = Path("data/usda_fertilizer_prices.csv")

# Current USDA AMS Production Cost reports listed by AMS.
REPORTS: dict[str, int] = {
    "Alabama": 3051,
    "Illinois": 3195,
    "Maryland": 3776,
    "Inter-Mountain West": 3883,
    "Iowa": 2863,
    "North Carolina": 3159,
    "Oklahoma": 3621,
    "Pacific Northwest": 3657,
    "Pennsylvania": 3726,
    "South Carolina": 2789,
}

HISTORY_COLUMNS = [
    "Date",
    "Commodity",
    "Price",
    "Low",
    "High",
    "Reported_Change",
    "Unit",
    "Region",
    "Source",
    "Slug_ID",
    "Source_URL",
    "Freight",
    "Delivery_Period",
    "Retrieved_At",
]

_DATE_KEYS = (
    "report_end_date",
    "report_date",
    "report_begin_date",
    "week_ending",
    "published_date",
    "publication_date",
    "date",
)
_PRODUCT_KEYS = (
    "class",
    "commodity",
    "commodity_name",
    "product",
    "product_name",
    "item",
)
_AVERAGE_KEYS = (
    "average",
    "avg",
    "average_price",
    "avg_price",
    "price",
)
_LOW_KEYS = ("low", "low_price", "price_low", "min", "minimum")
_HIGH_KEYS = ("high", "high_price", "price_high", "max", "maximum")
_RANGE_KEYS = ("price_range", "price range", "range")
_CHANGE_KEYS = ("change", "price_change", "reported_change")
_FREIGHT_KEYS = ("freight", "freight_code")
_DELIVERY_KEYS = ("delivery_period", "delivery period", "delivery")


def _normalized_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _lookup(record: Mapping[str, Any], *names: str) -> Any:
    normalized = {_normalized_key(key): value for key, value in record.items()}
    for name in names:
        key = _normalized_key(name)
        if key in normalized:
            value = normalized[key]
            if value is not None and str(value).strip() != "":
                return value
    return None


def parse_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "n/a", "na", "-"}:
        return None

    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    text = text.replace(",", "").replace("$", "")
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None

    number = float(match.group(0))
    return -abs(number) if negative else number


def _parse_range(value: Any) -> tuple[float | None, float | None]:
    if value is None:
        return None, None
    text = str(value).replace(",", "").replace("$", "")
    numbers = re.findall(r"\d+(?:\.\d+)?", text)
    if not numbers:
        return None, None
    if len(numbers) == 1:
        number = float(numbers[0])
        return number, number
    return float(numbers[0]), float(numbers[1])


def normalize_product(raw_name: Any) -> str | None:
    if raw_name is None:
        return None

    text = re.sub(r"\s+", " ", str(raw_name)).strip()
    lowered = text.lower()

    # Explicitly ignore non-fertilizer rows that appear in the same reports.
    blocked = (
        "diesel",
        "propane",
        "lime",
        "manure",
        "interest rate",
        "seed",
    )
    if any(term in lowered for term in blocked):
        return None

    if "urea" in lowered and "liquid" not in lowered:
        return "Urea"
    if lowered.startswith("dap") or "diammonium phosphate" in lowered:
        return "DAP"
    if lowered.startswith("map") or "monoammonium phosphate" in lowered:
        return "MAP"
    if "potash" in lowered:
        return "Potash"
    if "ammonium sulfate" in lowered:
        return "Ammonium Sulfate"
    if "anhydrous ammonia" in lowered:
        return "Anhydrous Ammonia"
    if "ammonium nitrate" in lowered:
        return "Ammonium Nitrate"
    if "ats" in lowered and "sulfate" in lowered:
        return "ATS (Sulfate)"

    if "liquid nitrogen" in lowered or lowered.startswith("uan"):
        concentration = re.search(r"(?:\(|\b)(28|30|32)-0-0(?:\)|\b)", lowered)
        if concentration:
            return f"UAN {concentration.group(1)}-0-0"
        return "UAN"

    return None


def _is_scalar(value: Any) -> bool:
    return not isinstance(value, (dict, list, tuple))


def _walk_records(
    value: Any,
    inherited: Mapping[str, Any] | None = None,
) -> Iterable[dict[str, Any]]:
    context = dict(inherited or {})

    if isinstance(value, Mapping):
        current = dict(context)

        # Carry report dates and section labels into nested result rows.
        for key, item in value.items():
            normalized = _normalized_key(key)
            if _is_scalar(item) and (
                normalized in {_normalized_key(name) for name in _DATE_KEYS}
                or normalized in {"report_section", "section", "section_name"}
            ):
                current[key] = item

        candidate = dict(current)
        candidate.update(value)
        product = _lookup(candidate, *_PRODUCT_KEYS)
        average = _lookup(candidate, *_AVERAGE_KEYS)
        if product is not None and average is not None:
            yield candidate

        for key, item in value.items():
            if isinstance(item, (Mapping, list, tuple)):
                child_context = dict(current)
                if _normalized_key(key) not in {"results", "data", "rows"}:
                    if "fertilizer" in str(key).lower():
                        child_context["section"] = str(key)
                yield from _walk_records(item, child_context)

    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_records(item, context)


def _record_date(record: Mapping[str, Any]) -> pd.Timestamp | None:
    for key in _DATE_KEYS:
        raw = _lookup(record, key)
        if raw is None:
            continue
        parsed = pd.to_datetime(raw, errors="coerce")
        if not pd.isna(parsed):
            if isinstance(parsed, pd.DatetimeIndex):
                parsed = parsed[0]
            return pd.Timestamp(parsed).normalize()
    return None


def extract_price_rows(
    payload: Any,
    region: str,
    slug_id: int,
    retrieved_at: str | None = None,
) -> pd.DataFrame:
    retrieved_at = retrieved_at or datetime.now().replace(microsecond=0).isoformat()
    source_url = f"https://mymarketnews.ams.usda.gov/viewReport/{slug_id}"
    rows: list[dict[str, Any]] = []

    for record in _walk_records(payload):
        commodity = normalize_product(_lookup(record, *_PRODUCT_KEYS))
        if commodity is None:
            continue

        price = parse_number(_lookup(record, *_AVERAGE_KEYS))
        report_date = _record_date(record)
        if price is None or report_date is None:
            continue

        low = parse_number(_lookup(record, *_LOW_KEYS))
        high = parse_number(_lookup(record, *_HIGH_KEYS))
        if low is None or high is None:
            range_low, range_high = _parse_range(_lookup(record, *_RANGE_KEYS))
            low = low if low is not None else range_low
            high = high if high is not None else range_high

        rows.append(
            {
                "Date": report_date,
                "Commodity": commodity,
                "Price": price,
                "Low": low,
                "High": high,
                "Reported_Change": parse_number(_lookup(record, *_CHANGE_KEYS)),
                "Unit": "USD/T",
                "Region": region,
                "Source": "USDA AMS",
                "Slug_ID": int(slug_id),
                "Source_URL": source_url,
                "Freight": _lookup(record, *_FREIGHT_KEYS),
                "Delivery_Period": _lookup(record, *_DELIVERY_KEYS),
                "Retrieved_At": retrieved_at,
            }
        )

    if not rows:
        return pd.DataFrame(columns=HISTORY_COLUMNS)

    result = pd.DataFrame(rows)
    result = result.drop_duplicates(
        subset=["Date", "Region", "Commodity", "Unit"],
        keep="last",
    )
    return result[HISTORY_COLUMNS].sort_values(
        ["Date", "Region", "Commodity"]
    ).reset_index(drop=True)


def _report_sections(payload: Any) -> list[str]:
    if not isinstance(payload, Mapping):
        return []

    raw = payload.get("reportSections") or payload.get("report_sections") or []
    sections: list[str] = []
    if isinstance(raw, str):
        raw = [raw]

    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                sections.append(item)
            elif isinstance(item, Mapping):
                name = _lookup(item, "name", "section", "report_section", "section_name")
                if name:
                    sections.append(str(name))

    return list(dict.fromkeys(sections))


def _query_params(days: int) -> dict[str, str]:
    end = date.today()
    start = end - timedelta(days=max(1, int(days)))
    date_range = f"{start:%m/%d/%Y}:{end:%m/%d/%Y}"
    return {
        "q": f"report_begin_date={date_range}",
        "allSections": "true",
    }


def _request_json(
    session: requests.Session,
    url: str,
    api_key: str,
    params: Mapping[str, str] | None = None,
) -> Any:
    response = session.get(
        url,
        auth=(api_key, ""),
        params=params,
        timeout=30,
        headers={"Accept": "application/json", "User-Agent": "prices-dashboard/1.0"},
    )
    response.raise_for_status()
    return response.json()


def fetch_report(
    session: requests.Session,
    api_key: str,
    region: str,
    slug_id: int,
    days: int = 60,
) -> pd.DataFrame:
    base_url = f"{API_BASE}/{slug_id}"
    params = _query_params(days)
    payload = _request_json(session, base_url, api_key, params=params)
    rows = extract_price_rows(payload, region=region, slug_id=slug_id)
    if not rows.empty:
        return rows

    # Some MARS reports expose only a section index on the root endpoint.
    # If that happens, query fertilizer sections individually.
    section_frames: list[pd.DataFrame] = []
    sections = _report_sections(payload)
    fertilizer_sections = [
        section for section in sections if "fertilizer" in section.lower()
    ]
    for section in fertilizer_sections:
        section_url = f"{base_url}/{quote(section, safe='')}"
        section_payload = _request_json(
            session,
            section_url,
            api_key,
            params={"q": params["q"]},
        )
        frame = extract_price_rows(section_payload, region=region, slug_id=slug_id)
        if not frame.empty:
            section_frames.append(frame)

    if section_frames:
        return pd.concat(section_frames, ignore_index=True).drop_duplicates(
            subset=["Date", "Region", "Commodity", "Unit"],
            keep="last",
        )

    # Last fallback used by many v1.2 MARS reports.
    details_payload = _request_json(
        session,
        f"{base_url}/Details",
        api_key,
        params={"lastDays": str(max(1, int(days)))},
    )
    return extract_price_rows(details_payload, region=region, slug_id=slug_id)


def fetch_all_reports(
    api_key: str,
    days: int = 60,
    reports: Mapping[str, int] | None = None,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    if not api_key or not api_key.strip():
        raise ValueError("USDA_API_KEY is required")

    report_map = dict(reports or REPORTS)
    http = session or requests.Session()
    frames: list[pd.DataFrame] = []
    errors: list[str] = []

    for region, slug_id in report_map.items():
        try:
            frame = fetch_report(
                http,
                api_key=api_key.strip(),
                region=region,
                slug_id=slug_id,
                days=days,
            )
        except Exception as exc:  # keep other regions updating if one USDA report fails
            errors.append(f"{region} ({slug_id}): {exc}")
            continue

        if frame.empty:
            errors.append(f"{region} ({slug_id}): no fertilizer rows returned")
            continue
        frames.append(frame)

    if not frames:
        detail = "; ".join(errors) if errors else "no reports returned data"
        raise RuntimeError(f"USDA API returned no usable fertilizer data: {detail}")

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["Date", "Region", "Commodity", "Unit"],
        keep="last",
    ).sort_values(["Date", "Region", "Commodity"])

    if errors:
        print("Warnings while fetching USDA reports:")
        for error in errors:
            print(f"  - {error}")

    return combined[HISTORY_COLUMNS].reset_index(drop=True)


def _normalize_history_frame(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    for column in HISTORY_COLUMNS:
        if column not in work.columns:
            work[column] = pd.NA

    work["Date"] = pd.to_datetime(work["Date"], errors="coerce")
    for column in ["Price", "Low", "High", "Reported_Change"]:
        work[column] = pd.to_numeric(work[column], errors="coerce")
    work["Slug_ID"] = pd.to_numeric(work["Slug_ID"], errors="coerce").astype("Int64")

    work = work.dropna(subset=["Date", "Commodity", "Price", "Region", "Unit"])
    work["Commodity"] = work["Commodity"].astype(str).str.strip()
    work["Region"] = work["Region"].astype(str).str.strip()
    work["Unit"] = work["Unit"].astype(str).str.strip()
    return work[HISTORY_COLUMNS]


def load_history(path: str | Path = DEFAULT_OUTPUT) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=HISTORY_COLUMNS)
    return _normalize_history_frame(pd.read_csv(path))


def merge_history(
    new_rows: pd.DataFrame,
    output_path: str | Path = DEFAULT_OUTPUT,
) -> pd.DataFrame:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    existing = load_history(output)
    incoming = _normalize_history_frame(new_rows)
    combined = pd.concat([existing, incoming], ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["Date", "Region", "Commodity", "Unit"],
        keep="last",
    ).sort_values(["Date", "Region", "Commodity"]).reset_index(drop=True)

    export = combined.copy()
    export["Date"] = export["Date"].dt.strftime("%Y-%m-%d")
    export.to_csv(output, index=False)
    return combined

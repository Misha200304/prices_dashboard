from __future__ import annotations

import argparse
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://fertilizerprice.com"
REPORT_PREFIX = f"{BASE_URL}/news/fertilizer-prices-week-"
DEFAULT_OUTPUT = Path("data/fertilizer_prices.csv")
EARLIEST_STRUCTURED_REPORT = date(2026, 4, 3)

COLUMNS = [
    "Date",
    "Commodity",
    "Price",
    "Unit",
    "Source",
    "Regions_Reported",
    "Series",
    "Source_URL",
    "Retrieved_At",
]


def _fridays(start: date, end: date):
    current = start + timedelta(days=(4 - start.weekday()) % 7)
    while current <= end:
        yield current
        current += timedelta(days=7)


def _price(text: str) -> float:
    cleaned = re.sub(r"[^0-9.]", "", text)
    if not cleaned:
        raise ValueError(f"Could not parse price from {text!r}")
    return float(cleaned)


def parse_report_html(html: str, source_url: str) -> pd.DataFrame:
    match = re.search(r"(\d{4}-\d{2}-\d{2})$", source_url)
    if not match:
        raise ValueError(f"Report URL does not end in YYYY-MM-DD: {source_url}")
    report_date = match.group(1)

    soup = BeautifulSoup(html, "html.parser")
    table = None
    for candidate in soup.find_all("table"):
        headers = [
            th.get_text(" ", strip=True)
            for th in candidate.find_all("th")
        ]
        if "Product" in headers and "Avg Price/Ton" in headers and "Regions" in headers:
            table = candidate
            break

    if table is None:
        raise ValueError(f"Price table not found on {source_url}")

    rows = []
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    for tr in table.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in tr.find_all("td")]
        if len(cells) < 6:
            continue

        product = cells[0].strip()
        if not product:
            continue

        rows.append(
            {
                "Date": report_date,
                "Commodity": product,
                "Price": _price(cells[2]),
                "Unit": "USD/short ton",
                "Source": "FertilizerPrice.com weekly report",
                "Regions_Reported": int(cells[5]),
                "Series": "reported_national",
                "Source_URL": source_url,
                "Retrieved_At": retrieved_at,
            }
        )

    if not rows:
        raise ValueError(f"No fertilizer rows parsed from {source_url}")

    return pd.DataFrame(rows, columns=COLUMNS)


def fetch_report(
    session: requests.Session,
    report_date: date,
    timeout: int = 30,
) -> pd.DataFrame | None:
    url = f"{REPORT_PREFIX}{report_date.isoformat()}"
    response = session.get(url, timeout=timeout)

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return parse_report_html(response.text, url)


def _verified_existing(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)

    existing = pd.read_csv(path)

    for column in COLUMNS:
        if column not in existing.columns:
            existing[column] = pd.NA

    verified = existing.loc[
        (existing["Source"].astype(str) == "FertilizerPrice.com weekly report")
        | (existing["Series"].astype(str) == "reported_national")
    ].copy()

    return verified[COLUMNS]


def update_history(
    output: Path = DEFAULT_OUTPUT,
    start: date | None = None,
    end: date | None = None,
    full: bool = False,
) -> pd.DataFrame:
    output = Path(output)
    end = end or date.today()

    existing = _verified_existing(output)

    if start is None:
        if full or existing.empty:
            start = EARLIEST_STRUCTURED_REPORT
        else:
            latest = pd.to_datetime(existing["Date"], errors="coerce").max()
            if pd.isna(latest):
                start = EARLIEST_STRUCTURED_REPORT
            else:
                start = max(
                    EARLIEST_STRUCTURED_REPORT,
                    latest.date() - timedelta(days=35),
                )

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "prices_dashboard/1.0 "
                "(historical fertilizer price updater; public report pages only)"
            )
        }
    )

    fetched = []
    for report_date in _fridays(start, end):
        try:
            frame = fetch_report(session, report_date)
        except requests.RequestException as exc:
            print(f"WARNING {report_date}: request failed: {exc}")
            continue
        except (ValueError, TypeError) as exc:
            print(f"WARNING {report_date}: parse failed: {exc}")
            continue

        if frame is not None:
            fetched.append(frame)
            print(f"FOUND {report_date}: {len(frame)} products")

    if fetched:
        new_rows = pd.concat(fetched, ignore_index=True)
        combined = pd.concat([existing, new_rows], ignore_index=True)
    else:
        combined = existing.copy()

    if combined.empty:
        raise RuntimeError("No verified FertilizerPrice.com weekly reports were found.")

    combined["Date"] = pd.to_datetime(combined["Date"], errors="coerce")
    combined["Price"] = pd.to_numeric(combined["Price"], errors="coerce")
    combined["Regions_Reported"] = pd.to_numeric(
        combined["Regions_Reported"], errors="coerce"
    ).astype("Int64")

    combined = combined.dropna(
        subset=["Date", "Commodity", "Price", "Unit", "Regions_Reported"]
    )
    combined = (
        combined.drop_duplicates(
            subset=["Date", "Commodity", "Unit", "Series"],
            keep="last",
        )
        .sort_values(["Date", "Commodity"])
        .reset_index(drop=True)
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output, index=False, date_format="%Y-%m-%d")

    print(
        f"Saved {len(combined)} verified rows covering "
        f"{combined['Date'].min().date()} through {combined['Date'].max().date()} "
        f"to {output}"
    )
    return combined


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill verified FertilizerPrice.com weekly market-report prices. "
            "Only structured public report pages are used."
        )
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--start", help="YYYY-MM-DD")
    parser.add_argument("--end", help="YYYY-MM-DD")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Recheck every Friday from the earliest structured report.",
    )
    args = parser.parse_args()

    start = date.fromisoformat(args.start) if args.start else None
    end = date.fromisoformat(args.end) if args.end else None

    update_history(
        output=Path(args.output),
        start=start,
        end=end,
        full=args.full,
    )


if __name__ == "__main__":
    main()

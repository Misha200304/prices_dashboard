# Prices Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Streamlit commodity-price dashboard that reads live Google Sheets data when configured, falls back to repository data, and visualizes daily plus chronological month/year trends for Urea and Sulfur.

**Architecture:** Keep data logic separate from UI. `price_data.py` owns loading, normalization, deduplication, monthly aggregation, and fallback behavior; `app.py` only composes Streamlit controls/metrics/charts from those functions. Google Sheets is read through a CSV URL configured by `GOOGLE_SHEET_CSV_URL`, while repository CSV/XLSX files remain the backup source.

**Tech Stack:** Python 3.11+, pandas, Streamlit, openpyxl, pytest

**Spec:** `docs/superpowers/specs/2026-09-19-prices-dashboard-design.md`

## Global Constraints

- No Postgres, Supabase, or additional database layer.
- Google Sheets is the preferred live source of truth.
- Use `@st.cache_data(ttl=300)`, never `ttl_seconds`.
- Never commit real Streamlit secrets.
- Preserve existing files under `data/` as backup inputs.
- Canonical columns are `Date`, `Commodity`, `Price`, `Unit`, `Source`, `Retrieved_At`.
- Deduplicate on `Commodity + Date + Unit`, keeping the newest available observation.
- Do not plot commodities with incompatible units on the same y-axis.
- Invalid dates and non-numeric prices must be dropped from chart data rather than crash the app.
- Monthly charts use chronological `Month_Start` and monthly mean price.

## Review Focus

- A Google Sheet containing `Year` and `Month` but no `Date` should still normalize successfully.
- Duplicate rows from one-year and current-month sources should collapse to one observation, with the later-loaded row winning.
- A malformed live Sheet should not prevent fallback repository data from loading.
- Empty or fully invalid data should produce a controlled empty DataFrame / Streamlit warning rather than an exception.
- Month labels crossing a year boundary must remain chronologically ordered, e.g. Nov 2025, Dec 2025, Jan 2026.

---

### Task 1: Canonical price normalization and monthly aggregation

**Files:**
- Create: `price_data.py`
- Create: `tests/test_price_data.py`

**Interfaces:**
- Consumes: pandas DataFrames matching either canonical `Date` format or `Year` + `Month` format.
- Produces: `normalize_prices(df: pd.DataFrame) -> pd.DataFrame`, `combine_price_frames(frames: list[pd.DataFrame]) -> pd.DataFrame`, `monthly_prices(df: pd.DataFrame) -> pd.DataFrame`.

- [ ] **Step 1: Write failing normalization tests**

```python
# tests/test_price_data.py
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
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
pytest tests/test_price_data.py -v
```

Expected: import failure because `price_data.py` / `normalize_prices` does not exist yet.

- [ ] **Step 3: Implement minimal normalization**

```python
# price_data.py
from __future__ import annotations

import pandas as pd

CANONICAL_COLUMNS = [
    "Date",
    "Commodity",
    "Price",
    "Unit",
    "Source",
    "Retrieved_At",
]


def normalize_prices(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()

    if "Date" not in work.columns:
        if not {"Year", "Month"}.issubset(work.columns):
            raise ValueError("Input must contain Date or both Year and Month columns")
        work["Date"] = pd.to_datetime(
            {
                "year": pd.to_numeric(work["Year"], errors="coerce"),
                "month": pd.to_numeric(work["Month"], errors="coerce"),
                "day": 1,
            },
            errors="coerce",
        )
    else:
        work["Date"] = pd.to_datetime(work["Date"], errors="coerce")

    work["Price"] = pd.to_numeric(work.get("Price"), errors="coerce")

    for column in ["Commodity", "Unit", "Source", "Retrieved_At"]:
        if column not in work.columns:
            work[column] = pd.NA

    work = work.dropna(subset=["Date", "Commodity", "Price", "Unit"]).copy()
    work["Year"] = work["Date"].dt.year
    work["Month"] = work["Date"].dt.month
    work["Month_Start"] = work["Date"].dt.to_period("M").dt.to_timestamp()

    ordered = CANONICAL_COLUMNS + ["Year", "Month", "Month_Start"]
    return work[ordered].reset_index(drop=True)
```

- [ ] **Step 4: Run normalization tests and verify GREEN**

```bash
pytest tests/test_price_data.py -v
```

Expected: all three tests pass.

- [ ] **Step 5: Write failing deduplication and month-order tests**

Append to `tests/test_price_data.py`:

```python
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
```

- [ ] **Step 6: Run the new tests and verify RED**

```bash
pytest tests/test_price_data.py -v
```

Expected: failures because `combine_price_frames` and `monthly_prices` do not yet exist.

- [ ] **Step 7: Implement minimal combine and aggregation functions**

Append to `price_data.py`:

```python
def combine_price_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    normalized = [normalize_prices(frame) for frame in frames if frame is not None and not frame.empty]
    if not normalized:
        return pd.DataFrame(columns=CANONICAL_COLUMNS + ["Year", "Month", "Month_Start"])

    combined = pd.concat(normalized, ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["Commodity", "Date", "Unit"],
        keep="last",
    )
    return combined.sort_values(["Commodity", "Date"]).reset_index(drop=True)


def monthly_prices(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Commodity", "Unit", "Month_Start", "Price"])

    result = (
        df.groupby(["Commodity", "Unit", "Month_Start"], as_index=False)["Price"]
        .mean()
        .sort_values(["Commodity", "Unit", "Month_Start"])
        .reset_index(drop=True)
    )
    return result
```

- [ ] **Step 8: Run Task 1 tests and commit**

```bash
pytest tests/test_price_data.py -v
git add price_data.py tests/test_price_data.py
git commit -m "feat: normalize and aggregate price data"
```

Expected: all tests pass.

---

### Task 2: Google Sheets live loading with repository fallback

**Files:**
- Modify: `price_data.py`
- Modify: `tests/test_price_data.py`

**Interfaces:**
- Consumes: `sheet_url: str | None`, `data_dir: str | Path`.
- Produces: `load_live_sheet(sheet_url: str) -> pd.DataFrame`, `load_repository_data(data_dir: str | Path = "data") -> pd.DataFrame`, `load_prices(sheet_url: str | None, data_dir: str | Path = "data") -> tuple[pd.DataFrame, str]` where source label is `"google_sheets"` or `"repository_backup"`.

- [ ] **Step 1: Write failing repository-loader and fallback tests**

Append to `tests/test_price_data.py`:

```python
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
```

- [ ] **Step 2: Run tests and verify RED**

```bash
pytest tests/test_price_data.py -v
```

Expected: failures because loading functions do not exist.

- [ ] **Step 3: Implement live, backup, and fallback loaders**

Append to `price_data.py`:

```python
from pathlib import Path


def load_live_sheet(sheet_url: str) -> pd.DataFrame:
    return normalize_prices(pd.read_csv(sheet_url))


def load_repository_data(data_dir: str | Path = "data") -> pd.DataFrame:
    root = Path(data_dir)
    frames: list[pd.DataFrame] = []

    for path in sorted(root.glob("*.csv")):
        frames.append(pd.read_csv(path))

    for path in sorted(root.glob("*.xlsx")):
        try:
            workbook = pd.read_excel(path, sheet_name=None)
        except Exception:
            continue
        for frame in workbook.values():
            if isinstance(frame, pd.DataFrame) and (
                "Date" in frame.columns or {"Year", "Month"}.issubset(frame.columns)
            ):
                frames.append(frame)

    return combine_price_frames(frames)


def load_prices(
    sheet_url: str | None,
    data_dir: str | Path = "data",
) -> tuple[pd.DataFrame, str]:
    if sheet_url:
        try:
            live = load_live_sheet(sheet_url)
            if not live.empty:
                return live, "google_sheets"
        except Exception:
            pass

    return load_repository_data(data_dir), "repository_backup"
```

- [ ] **Step 4: Add malformed-live-sheet fallback test**

Append to `tests/test_price_data.py`:

```python
def test_load_prices_falls_back_when_live_sheet_has_bad_schema(monkeypatch, tmp_path: Path):
    backup = pd.DataFrame({
        "Date": ["2026-09-19"],
        "Commodity": ["Sulfur"],
        "Price": [3000.0],
        "Unit": ["CNY/T"],
        "Source": ["backup"],
    })
    backup.to_csv(tmp_path / "sulfur.csv", index=False)

    monkeypatch.setattr(
        "price_data.pd.read_csv",
        lambda url: pd.DataFrame({"SomethingElse": [1]}),
    )

    result, source = load_prices("https://example.com/sheet.csv", tmp_path)

    assert source == "repository_backup"
    assert result.iloc[0]["Commodity"] == "Sulfur"
```

- [ ] **Step 5: Run Task 2 tests and commit**

```bash
pytest tests/test_price_data.py -v
git add price_data.py tests/test_price_data.py
git commit -m "feat: load Google Sheets with repository fallback"
```

Expected: all tests pass.

---

### Task 3: Streamlit dashboard UI, refresh behavior, and month/year charts

**Files:**
- Create: `app.py`
- Create: `requirements.txt`
- Create: `.streamlit/secrets.toml.example`

**Interfaces:**
- Consumes: `load_prices(...)` and `monthly_prices(...)` from `price_data.py`.
- Produces: runnable Streamlit app at `streamlit run app.py`.

- [ ] **Step 1: Add runtime dependencies**

Create `requirements.txt`:

```text
streamlit>=1.39,<2
pandas>=2.2,<3
openpyxl>=3.1,<4
pytest>=8,<9
```

Create `.streamlit/secrets.toml.example`:

```toml
# Use the CSV-export URL for the Google Sheet.
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/export?format=csv&gid=0"
```

- [ ] **Step 2: Create the Streamlit app with supported cache syntax**

Create `app.py`:

```python
from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from price_data import load_prices, monthly_prices

st.set_page_config(page_title="Commodity Prices Dashboard", layout="wide")


def get_sheet_url() -> str | None:
    if "GOOGLE_SHEET_CSV_URL" in st.secrets:
        return str(st.secrets["GOOGLE_SHEET_CSV_URL"])
    return os.getenv("GOOGLE_SHEET_CSV_URL")


@st.cache_data(ttl=300)
def cached_prices(sheet_url: str | None):
    return load_prices(sheet_url, "data")


st.title("Commodity Prices Dashboard")
st.caption("Urea and sulfur price monitoring with Google Sheets live sync and repository backup data.")

if st.button("Refresh data"):
    st.cache_data.clear()
    st.rerun()

prices, data_source = cached_prices(get_sheet_url())

if data_source == "repository_backup":
    st.warning("Live Google Sheets data is unavailable or not configured. Using repository backup data.")
else:
    st.success("Using live Google Sheets data.")

if prices.empty:
    st.warning("No valid price observations are available.")
    st.stop()

commodities = sorted(prices["Commodity"].dropna().astype(str).unique())
commodity = st.selectbox("Commodity", commodities)
filtered = prices.loc[prices["Commodity"].astype(str) == commodity].sort_values("Date")

units = sorted(filtered["Unit"].dropna().astype(str).unique())
unit = st.selectbox("Unit", units) if len(units) > 1 else units[0]
filtered = filtered.loc[filtered["Unit"].astype(str) == unit].copy()

latest = filtered.iloc[-1]
metric1, metric2 = st.columns(2)
metric1.metric("Latest price", f"{latest['Price']:,.2f} {unit}")
metric2.metric("Latest observation", latest["Date"].strftime("%Y-%m-%d"))

st.subheader("One-year history")
one_year_cutoff = filtered["Date"].max() - pd.DateOffset(years=1)
one_year = filtered.loc[filtered["Date"] >= one_year_cutoff]
st.line_chart(one_year.set_index("Date")[["Price"]], use_container_width=True)

st.subheader("Current month")
latest_month = filtered["Date"].max().to_period("M")
current_month = filtered.loc[filtered["Date"].dt.to_period("M") == latest_month]
st.line_chart(current_month.set_index("Date")[["Price"]], use_container_width=True)

st.subheader("Monthly trend")
monthly = monthly_prices(filtered)
st.line_chart(monthly.set_index("Month_Start")[["Price"]], use_container_width=True)

st.subheader("Underlying data")
st.dataframe(
    filtered.sort_values("Date", ascending=False),
    use_container_width=True,
    hide_index=True,
)
```

- [ ] **Step 3: Verify the application imports and cache API is valid**

Run:

```bash
python -m py_compile app.py price_data.py
python -c "import app"
```

Expected: no `ttl_seconds` error and no syntax/import error. The second command may emit Streamlit bare-mode warnings but must exit successfully.

- [ ] **Step 4: Run the full automated test suite**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 5: Smoke-test Streamlit startup**

Run:

```bash
streamlit run app.py --server.headless true --server.port 8501
```

Expected: Streamlit reports a local URL and starts without traceback. Stop it after startup verification.

- [ ] **Step 6: Commit the UI**

```bash
git add app.py requirements.txt .streamlit/secrets.toml.example
git commit -m "feat: add Streamlit commodity price dashboard"
```

---

### Task 4: Document Google Sheets workflow and final verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: final dashboard behavior.
- Produces: reproducible local run and Google Sheets setup instructions.

- [ ] **Step 1: Replace README with operating instructions**

Use this content:

```markdown
# prices_dashboard

Streamlit dashboard for Urea and Sulfur prices.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Live Google Sheets data

The preferred live data source is a Google Sheet with these columns:

| Date | Commodity | Price | Unit | Source | Retrieved_At |
|---|---|---:|---|---|---|
| 2026-09-19 | Urea | 450.25 | USD/T | Trading Economics | 2026-09-19T15:00:00 |

The dashboard also accepts rows that use `Year` and `Month` instead of `Date`.

For a Sheet that can be read through a CSV export URL, use:

```text
https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv&gid=0
```

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and set:

```toml
GOOGLE_SHEET_CSV_URL = "YOUR_GOOGLE_SHEET_CSV_URL"
```

Do not commit `.streamlit/secrets.toml`.

After adding a new row to the Sheet, click **Refresh data** in the dashboard or allow the 5-minute cache to expire. No GitHub commit is needed for ordinary price updates.

## Backup data

If Google Sheets is unavailable or not configured, the app loads compatible CSV/XLSX files from `data/` and deduplicates overlapping observations.
```

- [ ] **Step 2: Ensure local secrets are ignored**

Create or update `.gitignore` with:

```text
.streamlit/secrets.toml
__pycache__/
.pytest_cache/
```

- [ ] **Step 3: Run final verification**

```bash
pytest -v
python -m py_compile app.py price_data.py
git status --short
```

Expected: tests pass, compile succeeds, and only intended README / `.gitignore` changes remain before commit.

- [ ] **Step 4: Commit documentation**

```bash
git add README.md .gitignore
git commit -m "docs: explain Google Sheets dashboard workflow"
```

- [ ] **Step 5: Final acceptance check**

With `GOOGLE_SHEET_CSV_URL` configured to a valid sheet:

1. Start `streamlit run app.py`.
2. Confirm the app says it is using live Google Sheets data.
3. Add one new valid price row to the Sheet.
4. Click **Refresh data**.
5. Confirm the new date/price appears in the table and relevant chart.
6. Temporarily remove the URL and restart.
7. Confirm the app warns that repository backup data is being used and still renders.

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import subprocess

import pandas as pd

from fertilizer_data import (
    FERTILIZER_PRODUCTS,
    REGIONS,
    build_fertilizer_rows,
    build_regional_rows,
    update_csv_history,
)

DATA_DIR = Path("data")
MASTER_FILE = DATA_DIR / "commodity_prices.xlsx"
LATEST_FILE = DATA_DIR / "latest_prices.xlsx"
FERTILIZER_FILE = DATA_DIR / "fertilizer_prices.csv"
REGIONAL_FILE = Path("regional_data/fertilizer_regional_prices.csv")


def build_daily_rows(
    price_date: str,
    urea_price: float,
    sulfur_price: float,
) -> pd.DataFrame:
    day = pd.to_datetime(price_date, errors="raise").normalize()
    retrieved_at = datetime.now().replace(microsecond=0).isoformat()

    return pd.DataFrame(
        [
            {
                "Date": day,
                "Commodity": "Urea",
                "Price": float(urea_price),
                "Unit": "USD/T",
                "Source": "Manual entry",
                "Retrieved_At": retrieved_at,
            },
            {
                "Date": day,
                "Commodity": "Sulfur",
                "Price": float(sulfur_price),
                "Unit": "CNY/T",
                "Source": "Manual entry",
                "Retrieved_At": retrieved_at,
            },
        ]
    )


def update_excel_files(
    new_rows: pd.DataFrame,
    master_path: str | Path = MASTER_FILE,
    latest_path: str | Path = LATEST_FILE,
) -> pd.DataFrame:
    master_path = Path(master_path)
    latest_path = Path(latest_path)
    master_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.parent.mkdir(parents=True, exist_ok=True)

    if master_path.exists():
        history = pd.read_excel(master_path)
    else:
        history = pd.DataFrame(columns=new_rows.columns)

    if history.empty:
        combined = new_rows.copy()
    else:
        combined = pd.concat([history, new_rows], ignore_index=True)

    combined["Date"] = pd.to_datetime(combined["Date"], errors="coerce")
    combined["Price"] = pd.to_numeric(combined["Price"], errors="coerce")
    combined = combined.dropna(subset=["Date", "Commodity", "Price", "Unit"])

    combined = (
        combined.drop_duplicates(
            subset=["Commodity", "Date", "Unit"],
            keep="last",
        )
        .sort_values(["Date", "Commodity"])
        .reset_index(drop=True)
    )

    latest = new_rows.copy()
    latest["Date"] = pd.to_datetime(latest["Date"], errors="raise")

    combined.to_excel(master_path, index=False)
    latest.to_excel(latest_path, index=False)
    return combined


def update_fertilizer_files(
    price_date: str,
    national_prices: dict[str, float | None],
    regional_prices: dict[str, dict[str, float | None]] | None = None,
    national_path: str | Path = FERTILIZER_FILE,
    regional_path: str | Path = REGIONAL_FILE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    national_rows = build_fertilizer_rows(price_date, national_prices)
    national_history = update_csv_history(
        national_rows,
        national_path,
        ["Commodity", "Date", "Unit"],
    )

    regional_rows = build_regional_rows(price_date, regional_prices or {})
    regional_history = update_csv_history(
        regional_rows,
        regional_path,
        ["Commodity", "Region", "Date", "Unit"],
    )
    return national_history, regional_history


def _run_git(
    repo_root: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
    return result


def sync_price_files_to_git(
    repo_root: str | Path | None = None,
    branch: str = "main",
    message: str | None = None,
) -> bool:
    root = (
        Path(repo_root)
        if repo_root is not None
        else Path(__file__).resolve().parent
    )
    tracked_paths = [
        Path("data/commodity_prices.xlsx"),
        Path("data/latest_prices.xlsx"),
        Path("data/fertilizer_prices.csv"),
        Path("regional_data/fertilizer_regional_prices.csv"),
    ]
    tracked_paths = [path for path in tracked_paths if (root / path).exists()]

    current_branch = _run_git(
        root, "rev-parse", "--abbrev-ref", "HEAD"
    ).stdout.strip()
    if current_branch != branch:
        raise RuntimeError(
            f"Price sync must run from branch '{branch}', but current branch is '{current_branch}'."
        )

    if not tracked_paths:
        return False

    _run_git(root, "add", "--", *[str(path) for path in tracked_paths])
    diff = _run_git(
        root,
        "diff",
        "--cached",
        "--quiet",
        "--",
        *[str(path) for path in tracked_paths],
        check=False,
    )
    if diff.returncode == 0:
        return False
    if diff.returncode != 1:
        raise RuntimeError("Could not determine whether the price files changed.")

    commit_message = message or f"data: update prices {date.today().isoformat()}"
    _run_git(
        root,
        "commit",
        "-m",
        commit_message,
        "--",
        *[str(path) for path in tracked_paths],
    )

    push = _run_git(root, "push", "origin", branch, check=False)
    if push.returncode != 0:
        pull = _run_git(
            root,
            "pull",
            "--rebase",
            "--autostash",
            "origin",
            branch,
            check=False,
        )
        if pull.returncode != 0:
            detail = pull.stderr.strip() or pull.stdout.strip() or "unknown git pull error"
            raise RuntimeError(
                "Price files were committed locally, but GitHub sync failed "
                f"while rebasing: {detail}"
            )
        _run_git(root, "push", "origin", branch)

    return True


def _ask_price(label: str) -> float:
    while True:
        raw = input(f"{label}: ").strip()
        try:
            value = float(raw)
        except ValueError:
            print("Please enter a number, for example 451.25")
            continue

        if value <= 0:
            print("Price must be greater than 0.")
            continue
        return value


def _ask_optional_price(label: str) -> float | None:
    while True:
        raw = input(f"{label} [blank = skip]: ").strip()
        if raw == "":
            return None
        try:
            value = float(raw)
        except ValueError:
            print("Please enter a number or leave blank to skip.")
            continue
        if value <= 0:
            print("Price must be greater than 0.")
            continue
        return value


def _ask_yes_no(label: str, default: bool = False) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    raw = input(f"{label} {suffix}: ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes"}


def _collect_fertilizer_prices() -> dict[str, float | None]:
    print("\nFertilizerPrice.com national averages (USD/short ton).")
    print("Leave any value blank if it did not update or you do not have it.")
    return {
        product: _ask_optional_price(product)
        for product in FERTILIZER_PRODUCTS
    }


def _collect_regional_prices() -> dict[str, dict[str, float | None]]:
    result: dict[str, dict[str, float | None]] = {}
    print("\nRegional observations are optional.")
    for region in REGIONS:
        if not _ask_yes_no(f"Enter prices for {region}?"):
            continue
        result[region] = {
            product: _ask_optional_price(f"{region} - {product}")
            for product in FERTILIZER_PRODUCTS
        }
    return result


def main() -> None:
    today = date.today().isoformat()
    entered_date = input(f"Date [{today}]: ").strip() or today

    try:
        pd.to_datetime(entered_date, errors="raise")
    except Exception:
        raise SystemExit("Invalid date. Use YYYY-MM-DD, for example 2026-09-19.")

    urea_price = _ask_price("Urea price (USD/T)")
    sulfur_price = _ask_price("Sulfur price (CNY/T)")

    rows = build_daily_rows(entered_date, urea_price, sulfur_price)
    history = update_excel_files(rows)

    fertilizer_history = None
    regional_history = None
    if _ask_yes_no("Update FertilizerPrice.com fertilizer prices too?", default=True):
        national_prices = _collect_fertilizer_prices()
        regional_prices = (
            _collect_regional_prices()
            if _ask_yes_no("Add/update regional fertilizer observations?")
            else {}
        )
        fertilizer_history, regional_history = update_fertilizer_files(
            entered_date,
            national_prices,
            regional_prices,
        )

    print("\nSaved successfully.")
    print(f"Master history: {MASTER_FILE}")
    print(f"Today's output: {LATEST_FILE}")
    print(f"Total history rows: {len(history)}")
    if fertilizer_history is not None:
        print(f"Fertilizer national history: {FERTILIZER_FILE} ({len(fertilizer_history)} rows)")
    if regional_history is not None:
        print(f"Fertilizer regional history: {REGIONAL_FILE} ({len(regional_history)} rows)")
    print("\nUrea/Sulfur rows added/updated:")
    print(rows.to_string(index=False))

    try:
        pushed = sync_price_files_to_git(
            message=(
                "data: update prices "
                f"{pd.to_datetime(entered_date).date().isoformat()}"
            )
        )
    except RuntimeError as exc:
        raise SystemExit(
            f"Prices were saved locally, but GitHub sync failed: {exc}"
        ) from exc

    if pushed:
        print("\nGitHub sync: pushed to main successfully.")
        print("Streamlit Cloud will redeploy from the new GitHub data automatically.")
    else:
        print("\nGitHub sync: no price-file changes to push.")


if __name__ == "__main__":
    main()

from pathlib import Path
import subprocess

import pandas as pd

from add_today_prices import update_fertilizer_files, sync_price_files_to_git


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, text=True, capture_output=True)


def test_update_fertilizer_files_writes_national_and_regional_csv(tmp_path: Path):
    national_path = tmp_path / "data" / "fertilizer_prices.csv"
    regional_path = tmp_path / "regional_data" / "fertilizer_regional_prices.csv"
    national, regional = update_fertilizer_files(
        "2026-09-25",
        {"Urea": 800.0, "DAP": 790.0},
        {"Corn Belt": {"Urea": 720.0}},
        national_path=national_path,
        regional_path=regional_path,
    )
    assert national_path.exists()
    assert regional_path.exists()
    assert set(national["Commodity"]) == {"Urea", "DAP"}
    assert regional.iloc[0]["Region"] == "Corn Belt"


def test_sync_price_files_to_git_includes_fertilizer_csv_files(tmp_path: Path):
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    _git(tmp_path, "init", "--bare", str(remote))
    _git(tmp_path, "init", "-b", "main", str(repo))
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "data").mkdir()
    (repo / "regional_data").mkdir()
    (repo / "README.md").write_text("base\n")
    pd.DataFrame({"Date": ["2026-09-19"], "Commodity": ["Urea"], "Price": [450], "Unit": ["USD/T"]}).to_excel(repo / "data/commodity_prices.xlsx", index=False)
    pd.DataFrame({"Date": ["2026-09-19"], "Commodity": ["Urea"], "Price": [450], "Unit": ["USD/T"]}).to_excel(repo / "data/latest_prices.xlsx", index=False)
    pd.DataFrame({"Date": ["2026-09-19"], "Commodity": ["DAP"], "Price": [780], "Unit": ["USD/short ton"]}).to_csv(repo / "data/fertilizer_prices.csv", index=False)
    pd.DataFrame({"Date": ["2026-09-19"], "Commodity": ["DAP"], "Region": ["Corn Belt"], "Price": [900], "Unit": ["USD/short ton"]}).to_csv(repo / "regional_data/fertilizer_regional_prices.csv", index=False)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", "main")

    df = pd.read_csv(repo / "data/fertilizer_prices.csv")
    df.loc[0, "Price"] = 790
    df.to_csv(repo / "data/fertilizer_prices.csv", index=False)
    regional = pd.read_csv(repo / "regional_data/fertilizer_regional_prices.csv")
    regional.loc[0, "Price"] = 910
    regional.to_csv(repo / "regional_data/fertilizer_regional_prices.csv", index=False)

    changed = sync_price_files_to_git(repo_root=repo, branch="main", message="data: update fertilizer")
    assert changed is True
    shown = _git(repo, "show", "--name-only", "--pretty=format:", "origin/main").stdout
    assert "data/fertilizer_prices.csv" in shown
    assert "regional_data/fertilizer_regional_prices.csv" in shown

from pathlib import Path
import subprocess

import pandas as pd

from add_today_prices import build_daily_rows, update_excel_files, sync_price_files_to_git


def test_build_daily_rows_creates_urea_and_sulfur_rows():
    rows = build_daily_rows("2026-09-19", 451.25, 7687.33)
    assert rows["Commodity"].tolist() == ["Urea", "Sulfur"]
    assert rows["Price"].tolist() == [451.25, 7687.33]
    assert rows["Unit"].tolist() == ["USD/T", "CNY/T"]
    assert rows["Date"].tolist() == [pd.Timestamp("2026-09-19"), pd.Timestamp("2026-09-19")]


def test_update_excel_files_appends_history_and_writes_latest(tmp_path: Path):
    master = tmp_path / "commodity_prices.xlsx"
    latest = tmp_path / "latest_prices.xlsx"
    first = build_daily_rows("2026-09-18", 450.0, 7600.0)
    second = build_daily_rows("2026-09-19", 451.25, 7687.33)
    update_excel_files(first, master, latest)
    result = update_excel_files(second, master, latest)
    assert len(result) == 4
    assert master.exists()
    assert latest.exists()


def test_update_excel_files_replaces_same_date_instead_of_duplicating(tmp_path: Path):
    master = tmp_path / "commodity_prices.xlsx"
    latest = tmp_path / "latest_prices.xlsx"
    original = build_daily_rows("2026-09-19", 451.25, 7687.33)
    corrected = build_daily_rows("2026-09-19", 455.0, 7700.0)
    update_excel_files(original, master, latest)
    result = update_excel_files(corrected, master, latest)
    assert len(result) == 2
    assert result.loc[result["Commodity"] == "Urea", "Price"].iloc[0] == 455.0
    assert result.loc[result["Commodity"] == "Sulfur", "Price"].iloc[0] == 7700.0


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, text=True, capture_output=True)


def test_sync_price_files_to_git_commits_and_pushes_only_price_files(tmp_path: Path):
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    _git(tmp_path, "init", "--bare", str(remote))
    _git(tmp_path, "init", "-b", "main", str(repo))
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "data").mkdir()
    (repo / "README.md").write_text("base\n")
    pd.DataFrame({"Date": ["2026-09-19"], "Commodity": ["Urea"], "Price": [450], "Unit": ["USD/T"]}).to_excel(repo / "data/commodity_prices.xlsx", index=False)
    pd.DataFrame({"Date": ["2026-09-19"], "Commodity": ["Urea"], "Price": [450], "Unit": ["USD/T"]}).to_excel(repo / "data/latest_prices.xlsx", index=False)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", "main")

    pd.DataFrame({"Date": ["2026-09-20"], "Commodity": ["Urea"], "Price": [459.6], "Unit": ["USD/T"]}).to_excel(repo / "data/commodity_prices.xlsx", index=False)
    pd.DataFrame({"Date": ["2026-09-20"], "Commodity": ["Urea"], "Price": [459.6], "Unit": ["USD/T"]}).to_excel(repo / "data/latest_prices.xlsx", index=False)
    (repo / "README.md").write_text("unrelated local edit\n")

    changed = sync_price_files_to_git(repo_root=repo, branch="main", message="data: update prices 2026-09-20")

    assert changed is True
    remote_log = _git(repo, "log", "origin/main", "-1", "--pretty=%s").stdout.strip()
    assert remote_log == "data: update prices 2026-09-20"
    status = _git(repo, "status", "--short").stdout
    assert "README.md" in status
    assert "commodity_prices.xlsx" not in status
    assert "latest_prices.xlsx" not in status


def test_sync_price_files_to_git_rebases_when_remote_moved(tmp_path: Path):
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    other = tmp_path / "other"
    _git(tmp_path, "init", "--bare", str(remote))
    _git(tmp_path, "init", "-b", "main", str(repo))
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "data").mkdir()
    (repo / "README.md").write_text("base\n")
    pd.DataFrame({"Date": ["2026-09-19"], "Commodity": ["Urea"], "Price": [450], "Unit": ["USD/T"]}).to_excel(repo / "data/commodity_prices.xlsx", index=False)
    pd.DataFrame({"Date": ["2026-09-19"], "Commodity": ["Urea"], "Price": [450], "Unit": ["USD/T"]}).to_excel(repo / "data/latest_prices.xlsx", index=False)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", "main")

    _git(tmp_path, "clone", "-b", "main", str(remote), str(other))
    _git(other, "config", "user.email", "other@example.com")
    _git(other, "config", "user.name", "Other User")
    (other / "README.md").write_text("remote update\n")
    _git(other, "add", "README.md")
    _git(other, "commit", "-m", "remote update")
    _git(other, "push", "origin", "main")

    pd.DataFrame({"Date": ["2026-09-20"], "Commodity": ["Urea"], "Price": [459.6], "Unit": ["USD/T"]}).to_excel(repo / "data/commodity_prices.xlsx", index=False)
    pd.DataFrame({"Date": ["2026-09-20"], "Commodity": ["Urea"], "Price": [459.6], "Unit": ["USD/T"]}).to_excel(repo / "data/latest_prices.xlsx", index=False)

    changed = sync_price_files_to_git(repo_root=repo, branch="main", message="data: update prices 2026-09-20")

    assert changed is True
    subjects = _git(repo, "log", "origin/main", "-2", "--pretty=%s").stdout.splitlines()
    assert subjects[0] == "data: update prices 2026-09-20"
    assert subjects[1] == "remote update"

from pathlib import Path


def test_readme_documents_live_sheet_refresh_workflow():
    readme = Path("README.md").read_text()

    assert "## Live Google Sheets data" in readme
    assert "Refresh data" in readme
    assert "No GitHub commit is needed" in readme
    assert "GOOGLE_SHEET_CSV_URL" in readme


def test_gitignore_excludes_real_streamlit_secret():
    ignored = Path(".gitignore").read_text().splitlines()

    assert ".streamlit/secrets.toml" in ignored

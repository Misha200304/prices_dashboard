from pathlib import Path


def test_streamlit_app_uses_supported_cache_and_refresh_contract():
    source = Path("app.py").read_text()

    assert "@st.cache_data(ttl=300)" in source
    assert "ttl_seconds" not in source
    assert 'st.button("Refresh data")' in source
    assert 'st.subheader("Monthly trend")' in source


def test_app_executes_with_streamlit_api_stub(monkeypatch):
    import importlib
    import sys
    import types

    import pandas as pd
    import price_data

    class CacheData:
        def __call__(self, func=None, *, ttl=None, **kwargs):
            if func is None:
                return lambda wrapped: wrapped
            return func

        def clear(self):
            return None

    class MetricColumn:
        def metric(self, *args, **kwargs):
            return None

    fake_st = types.ModuleType("streamlit")
    fake_st.cache_data = CacheData()
    fake_st.secrets = {}
    fake_st.set_page_config = lambda **kwargs: None
    fake_st.title = lambda *args, **kwargs: None
    fake_st.caption = lambda *args, **kwargs: None
    fake_st.button = lambda *args, **kwargs: False
    fake_st.rerun = lambda: None
    fake_st.warning = lambda *args, **kwargs: None
    fake_st.success = lambda *args, **kwargs: None
    fake_st.stop = lambda: (_ for _ in ()).throw(RuntimeError("unexpected stop"))
    fake_st.selectbox = lambda label, options: list(options)[0]
    fake_st.columns = lambda n: [MetricColumn() for _ in range(n)]
    fake_st.subheader = lambda *args, **kwargs: None
    fake_st.line_chart = lambda *args, **kwargs: None
    fake_st.dataframe = lambda *args, **kwargs: None

    sample = price_data.normalize_prices(pd.DataFrame({
        "Date": ["2026-08-01", "2026-09-01"],
        "Commodity": ["Urea", "Urea"],
        "Price": [440.0, 450.25],
        "Unit": ["USD/T", "USD/T"],
        "Source": ["x", "x"],
    }))

    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    monkeypatch.setattr(price_data, "load_prices", lambda *args, **kwargs: (sample, "google_sheets"))
    sys.modules.pop("app", None)

    imported = importlib.import_module("app")

    assert imported.prices.iloc[-1]["Price"] == 450.25


def test_app_uses_environment_url_without_requiring_secrets_file(monkeypatch):
    import importlib
    import sys
    import types

    import pandas as pd
    import price_data

    class MissingSecrets:
        def __contains__(self, key):
            raise RuntimeError("no secrets file")

        def get(self, key, default=None):
            raise RuntimeError("no secrets file")

    class CacheData:
        def __call__(self, func=None, *, ttl=None, **kwargs):
            if func is None:
                return lambda wrapped: wrapped
            return func

        def clear(self):
            return None

    class MetricColumn:
        def metric(self, *args, **kwargs):
            return None

    fake_st = types.ModuleType("streamlit")
    fake_st.cache_data = CacheData()
    fake_st.secrets = MissingSecrets()
    fake_st.set_page_config = lambda **kwargs: None
    fake_st.title = lambda *args, **kwargs: None
    fake_st.caption = lambda *args, **kwargs: None
    fake_st.button = lambda *args, **kwargs: False
    fake_st.rerun = lambda: None
    fake_st.warning = lambda *args, **kwargs: None
    fake_st.success = lambda *args, **kwargs: None
    fake_st.stop = lambda: (_ for _ in ()).throw(RuntimeError("unexpected stop"))
    fake_st.selectbox = lambda label, options: list(options)[0]
    fake_st.columns = lambda n: [MetricColumn() for _ in range(n)]
    fake_st.subheader = lambda *args, **kwargs: None
    fake_st.line_chart = lambda *args, **kwargs: None
    fake_st.dataframe = lambda *args, **kwargs: None

    sample = price_data.normalize_prices(pd.DataFrame({
        "Date": ["2026-09-19"],
        "Commodity": ["Urea"],
        "Price": [450.25],
        "Unit": ["USD/T"],
        "Source": ["x"],
    }))

    monkeypatch.setenv("GOOGLE_SHEET_CSV_URL", "https://example.com/live.csv")
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    monkeypatch.setattr(price_data, "load_prices", lambda url, *args, **kwargs: (sample, "google_sheets"))
    sys.modules.pop("app", None)

    imported = importlib.import_module("app")

    assert imported.get_sheet_url() == "https://example.com/live.csv"

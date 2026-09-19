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

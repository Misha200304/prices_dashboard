from __future__ import annotations

import pandas as pd
import streamlit as st

from price_data import load_repository_data, monthly_prices

st.set_page_config(page_title="Commodity Prices Dashboard", layout="wide")


@st.cache_data(ttl=300)
def cached_prices():
    return load_repository_data("data")


st.title("Commodity Prices Dashboard")
st.caption("Commodity price monitoring using data stored in this GitHub repository.")

controls_left, controls_right = st.columns([1, 4])
with controls_left:
    if st.button("Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

prices = cached_prices()

with controls_right:
    st.info("Data source: GitHub repository files in data/")

if prices.empty:
    st.warning("No valid price observations are available.")
    st.stop()

commodities = sorted(prices["Commodity"].dropna().astype(str).unique())
commodity = st.sidebar.selectbox("Commodity", commodities)
filtered = prices.loc[prices["Commodity"].astype(str) == commodity].sort_values("Date")

units = sorted(filtered["Unit"].dropna().astype(str).unique())
if not units:
    st.warning("No valid units are available for the selected commodity.")
    st.stop()
unit = st.sidebar.selectbox("Unit", units) if len(units) > 1 else units[0]
filtered = filtered.loc[filtered["Unit"].astype(str) == unit].copy()

sources = sorted(filtered["Source"].dropna().astype(str).unique())
if len(sources) > 1:
    selected_sources = st.sidebar.multiselect("Source", sources, default=sources)
    filtered = filtered.loc[filtered["Source"].astype(str).isin(selected_sources)]

if filtered.empty:
    st.warning("No rows match the selected filters.")
    st.stop()

min_date = filtered["Date"].min().date()
max_date = filtered["Date"].max().date()
selected_dates = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
    filtered = filtered.loc[
        (filtered["Date"].dt.date >= start_date)
        & (filtered["Date"].dt.date <= end_date)
    ]

if filtered.empty:
    st.warning("No rows exist in the selected date range.")
    st.stop()

filtered = filtered.sort_values("Date")
latest = filtered.iloc[-1]
previous = filtered.iloc[-2] if len(filtered) > 1 else None
change = float(latest["Price"] - previous["Price"]) if previous is not None else None

metric1, metric2, metric3 = st.columns(3)
metric1.metric(
    "Latest price",
    f"{latest['Price']:,.2f} {unit}",
    delta=f"{change:+,.2f}" if change is not None else None,
)
metric2.metric("Latest observation", latest["Date"].strftime("%Y-%m-%d"))
metric3.metric("Observations", f"{len(filtered):,}")

st.subheader("Historical price")
st.line_chart(
    filtered.set_index("Date")[["Price"]],
    use_container_width=True,
)

latest_month = filtered["Date"].max().to_period("M")
current_month = filtered.loc[filtered["Date"].dt.to_period("M") == latest_month]
st.subheader(f"Current month — {latest_month.strftime('%B %Y')}")
st.line_chart(
    current_month.set_index("Date")[["Price"]],
    use_container_width=True,
)

st.subheader("Monthly trend")
monthly = monthly_prices(filtered)
st.line_chart(
    monthly.set_index("Month_Start")[["Price"]],
    use_container_width=True,
)

st.subheader("Underlying data")
display_columns = [
    column
    for column in [
        "Date",
        "Commodity",
        "Price",
        "Unit",
        "Source",
        "Retrieved_At",
        "Year",
        "Month",
    ]
    if column in filtered.columns
]
st.dataframe(
    filtered[display_columns].sort_values("Date", ascending=False),
    use_container_width=True,
    hide_index=True,
)

csv_bytes = filtered[display_columns].to_csv(index=False).encode("utf-8")
st.download_button(
    "Download filtered CSV",
    data=csv_bytes,
    file_name=f"{commodity.lower().replace(' ', '_')}_prices.csv",
    mime="text/csv",
)

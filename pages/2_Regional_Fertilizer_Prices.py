from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from fertilizer_data import REGIONS

REGIONAL_FILE = Path("regional_data/fertilizer_regional_prices.csv")
NATIONAL_FILE = Path("data/fertilizer_prices.csv")

st.set_page_config(page_title="Regional Fertilizer Prices", page_icon="🗺️", layout="wide")
st.title("Regional Fertilizer Prices")
st.caption("FertilizerPrice.com national averages and available regional observations.")

if not REGIONAL_FILE.exists():
    st.warning("No regional fertilizer data file is available yet.")
    st.stop()

regional = pd.read_csv(REGIONAL_FILE)
regional["Date"] = pd.to_datetime(regional["Date"], errors="coerce")
regional["Price"] = pd.to_numeric(regional["Price"], errors="coerce")
regional = regional.dropna(subset=["Date", "Commodity", "Region", "Price"])

if regional.empty:
    st.warning("The regional fertilizer data file contains no valid observations.")
    st.stop()

products = sorted(regional["Commodity"].astype(str).unique())
product = st.sidebar.selectbox("Fertilizer", products)
product_data = regional.loc[regional["Commodity"] == product].copy()

dates = sorted(product_data["Date"].dt.date.unique(), reverse=True)
selected_date = st.sidebar.selectbox("Observation date", dates)
snapshot = product_data.loc[product_data["Date"].dt.date == selected_date].copy()

national_price = None
if NATIONAL_FILE.exists():
    national = pd.read_csv(NATIONAL_FILE)
    national["Date"] = pd.to_datetime(national["Date"], errors="coerce")
    national["Price"] = pd.to_numeric(national["Price"], errors="coerce")
    match = national.loc[
        (national["Commodity"] == product)
        & (national["Date"].dt.date == selected_date)
    ].sort_values("Date")
    if not match.empty:
        national_price = float(match.iloc[-1]["Price"])

left, right = st.columns([1, 3])
with left:
    if national_price is not None:
        st.metric("National Average", f"${national_price:,.2f} / short ton")
    st.metric("Regions Reported", f"{snapshot['Region'].nunique()}")
    st.metric("Regional Average", f"${snapshot['Price'].mean():,.2f} / short ton")

with right:
    chart = snapshot[["Region", "Price"]].drop_duplicates("Region", keep="last").set_index("Region")
    st.bar_chart(chart, use_container_width=True, height=430)

st.subheader("Regional observations")
ordered = snapshot.copy()
ordered["Region"] = pd.Categorical(ordered["Region"], categories=REGIONS, ordered=True)
ordered = ordered.sort_values("Region")
st.dataframe(
    ordered[["Date", "Commodity", "Region", "Price", "Unit", "Source"]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Date": st.column_config.DateColumn("Date", format="MMM DD, YYYY"),
        "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
    },
)

st.info("Blank regions mean FertilizerPrice.com did not publish an observation for that product/date. No values are interpolated.")

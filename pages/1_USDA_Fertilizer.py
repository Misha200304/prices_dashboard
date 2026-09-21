from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd
import streamlit as st

from usda_fertilizer import DEFAULT_OUTPUT, load_history


st.set_page_config(
    page_title="USDA Fertilizer Prices",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }
        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(120, 120, 120, 0.18);
        }
        .dashboard-title {
            font-size: 2.15rem;
            font-weight: 700;
            margin-bottom: 0.15rem;
        }
        .dashboard-subtitle {
            font-size: 0.98rem;
            opacity: 0.68;
            margin-bottom: 1.4rem;
        }
        .section-title {
            font-size: 1.25rem;
            font-weight: 650;
            margin-top: 0.4rem;
            margin-bottom: 0.2rem;
        }
        .section-description {
            font-size: 0.88rem;
            opacity: 0.62;
            margin-bottom: 0.7rem;
        }
        .data-badge {
            display: inline-block;
            padding: 0.35rem 0.65rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            border: 1px solid rgba(120, 120, 120, 0.25);
            margin-bottom: 0.5rem;
        }
        div[data-testid="stMetric"] {
            padding: 0.35rem 0;
        }
        div[data-testid="stMetricLabel"] {
            font-size: 0.82rem;
            opacity: 0.72;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.65rem;
        }
        div[data-testid="stDataFrame"] {
            border-radius: 10px;
            overflow: hidden;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    return load_history(DEFAULT_OUTPUT)


prices = load_data()

header_left, header_right = st.columns([4, 1])
with header_left:
    st.markdown(
        '<div class="dashboard-title">USDA Fertilizer Prices</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="dashboard-subtitle">'
        "Automated USDA AMS Production Cost prices by fertilizer and reporting region."
        "</div>",
        unsafe_allow_html=True,
    )

with header_right:
    st.markdown(
        '<div class="data-badge">● USDA AMS data</div>',
        unsafe_allow_html=True,
    )
    if st.button("↻ Refresh data", use_container_width=True, type="secondary"):
        st.cache_data.clear()
        st.rerun()

if prices.empty:
    st.warning(
        "No USDA fertilizer history has been collected yet. Run `python3 fetch_usda_prices.py` "
        "after adding USDA_API_KEY to your local .env file."
    )
    st.stop()

prices = prices.sort_values(["Date", "Region", "Commodity"]).reset_index(drop=True)

st.sidebar.markdown("## Dashboard Filters")
commodities = sorted(prices["Commodity"].dropna().astype(str).unique())
commodity = st.sidebar.selectbox("Fertilizer", commodities)

product_rows = prices.loc[prices["Commodity"] == commodity].copy()
regions = sorted(product_rows["Region"].dropna().astype(str).unique())
region_choice = st.sidebar.selectbox(
    "Reporting region",
    ["All reporting regions", *regions],
)

if region_choice == "All reporting regions":
    selected_raw = product_rows.copy()
    series = (
        selected_raw.groupby("Date", as_index=False)
        .agg(
            Price=("Price", "mean"),
            Low=("Low", "min"),
            High=("High", "max"),
            Region_Count=("Region", "nunique"),
        )
        .sort_values("Date")
        .reset_index(drop=True)
    )
    view_label = "Mean of reporting regions"
else:
    selected_raw = product_rows.loc[product_rows["Region"] == region_choice].copy()
    series = (
        selected_raw[["Date", "Price", "Low", "High"]]
        .sort_values("Date")
        .drop_duplicates(subset=["Date"], keep="last")
        .reset_index(drop=True)
    )
    series["Region_Count"] = 1
    view_label = region_choice

if series.empty:
    st.warning("No data matches the selected fertilizer and region.")
    st.stop()

latest = series.iloc[-1]
previous = series.iloc[-2] if len(series) > 1 else None
latest_date = pd.Timestamp(latest["Date"])
latest_price = float(latest["Price"])
previous_price = float(previous["Price"]) if previous is not None else None
absolute_change = latest_price - previous_price if previous_price is not None else None
percent_change = (
    (absolute_change / previous_price) * 100
    if previous_price not in (None, 0)
    else None
)

latest_period = latest_date.to_period("M")
current_month = series.loc[
    series["Date"].dt.to_period("M") == latest_period
].copy()
month_average = float(current_month["Price"].mean())
month_high = float(current_month["Price"].max())
month_low = float(current_month["Price"].min())

st.markdown(
    f'<div class="section-title">{escape(str(commodity))} Market Snapshot</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="section-description">'
    f'{escape(view_label)} • Latest observation: {latest_date.strftime("%B %d, %Y")}'
    "</div>",
    unsafe_allow_html=True,
)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    with st.container(border=True):
        st.metric("Latest Price", f"${latest_price:,.2f}/ton")

with kpi2:
    with st.container(border=True):
        if previous_price is None:
            st.metric("Previous Price", "N/A")
        else:
            st.metric(
                "Previous Price",
                f"${previous_price:,.2f}/ton",
                delta=f"{absolute_change:+,.2f} ({percent_change:+.2f}%)",
            )

with kpi3:
    with st.container(border=True):
        st.metric(
            f"{latest_period.strftime('%B')} Average",
            f"${month_average:,.2f}/ton",
        )

with kpi4:
    with st.container(border=True):
        st.metric(
            "Current Month Range",
            f"${month_low:,.2f} – ${month_high:,.2f}",
        )

secondary1, secondary2, secondary3 = st.columns(3)
with secondary1:
    with st.container(border=True):
        latest_regions = int(latest.get("Region_Count", 1))
        st.metric("Regions in Latest Observation", f"{latest_regions:,}")
with secondary2:
    with st.container(border=True):
        st.metric("Current Month Observations", f"{len(current_month):,}")
with secondary3:
    with st.container(border=True):
        st.metric("Unit", "USD per ton")

st.divider()

st.sidebar.markdown("---")
st.sidebar.markdown("### Historical Range")
min_date = series["Date"].min().date()
max_date = series["Date"].max().date()
date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

historical = series.copy()
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
    historical = historical.loc[
        (historical["Date"].dt.date >= start_date)
        & (historical["Date"].dt.date <= end_date)
    ].copy()

if region_choice == "All reporting regions":
    st.info(
        "The all-regions line is a simple mean of USDA regions reporting that fertilizer "
        "on each date. The mix of reporting regions can change between dates."
    )

overview_tab, month_tab, data_tab = st.tabs(
    ["📈 Overview", "📅 Current Month", "📋 USDA Data"]
)

with overview_tab:
    st.markdown(
        '<div class="section-title">Historical Price Trend</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-description">USDA reported average prices within the selected range.</div>',
        unsafe_allow_html=True,
    )

    if historical.empty:
        st.info("No observations exist in the selected historical range.")
    else:
        st.line_chart(
            historical[["Date", "Price"]].set_index("Date"),
            use_container_width=True,
            height=430,
        )
        h1, h2, h3, h4 = st.columns(4)
        with h1:
            st.metric("Range Average", f"${historical['Price'].mean():,.2f}")
        with h2:
            st.metric("Range High", f"${historical['Price'].max():,.2f}")
        with h3:
            st.metric("Range Low", f"${historical['Price'].min():,.2f}")
        with h4:
            st.metric("Observations", f"{len(historical):,}")

with month_tab:
    month_name = latest_period.strftime("%B %Y")
    st.markdown(
        f'<div class="section-title">{month_name} Prices</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-description">Weekly, bi-weekly or monthly USDA observations available in the latest month.</div>',
        unsafe_allow_html=True,
    )

    st.line_chart(
        current_month[["Date", "Price"]].set_index("Date"),
        use_container_width=True,
        height=430,
    )

    if not current_month.empty:
        m1, m2, m3, m4 = st.columns(4)
        opening = float(current_month.iloc[0]["Price"])
        closing = float(current_month.iloc[-1]["Price"])
        month_change = closing - opening
        month_pct = (month_change / opening * 100) if opening else 0.0
        with m1:
            st.metric("Opening Price", f"${opening:,.2f}")
        with m2:
            st.metric("Latest Price", f"${closing:,.2f}")
        with m3:
            st.metric("Month Change", f"{month_change:+,.2f}", delta=f"{month_pct:+.2f}%")
        with m4:
            st.metric("Average", f"${month_average:,.2f}")

with data_tab:
    st.markdown(
        '<div class="section-title">Underlying USDA Observations</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-description">Regional low/high ranges and USDA simple average prices used by the dashboard.</div>',
        unsafe_allow_html=True,
    )

    display = selected_raw[
        [
            "Date",
            "Region",
            "Commodity",
            "Price",
            "Low",
            "High",
            "Reported_Change",
            "Freight",
            "Delivery_Period",
            "Source_URL",
            "Retrieved_At",
        ]
    ].sort_values(["Date", "Region"], ascending=[False, True])

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Date": st.column_config.DateColumn("Date", format="MMM DD, YYYY"),
            "Price": st.column_config.NumberColumn("Average", format="$%.2f"),
            "Low": st.column_config.NumberColumn("Low", format="$%.2f"),
            "High": st.column_config.NumberColumn("High", format="$%.2f"),
            "Reported_Change": st.column_config.NumberColumn("USDA Change", format="%+.2f"),
            "Source_URL": st.column_config.LinkColumn("USDA Report"),
        },
    )

    csv_bytes = display.to_csv(index=False).encode("utf-8")
    st.download_button(
        "↓ Download filtered USDA data",
        data=csv_bytes,
        file_name=f"usda_{commodity.lower().replace(' ', '_')}_prices.csv",
        mime="text/csv",
    )

st.divider()
st.caption(
    f"Dashboard refreshed {datetime.now().strftime('%Y-%m-%d %H:%M')} • "
    "Source: USDA Agricultural Marketing Service, MyMarketNews"
)

from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd
import streamlit as st

from price_data import load_repository_data


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Commodity Prices Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# STYLING
# ============================================================

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

        hr {
            margin-top: 1.25rem;
            margin-bottom: 1.25rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATA
# ============================================================

@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    return load_repository_data("data")


prices = load_data()


# ============================================================
# HEADER
# ============================================================

header_left, header_right = st.columns([4, 1])

with header_left:
    st.markdown(
        '<div class="dashboard-title">Commodity Prices Dashboard</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="dashboard-subtitle">'
        "Urea and sulfur market-price monitoring from repository data."
        "</div>",
        unsafe_allow_html=True,
    )

with header_right:
    st.markdown(
        '<div class="data-badge">● GitHub repository data</div>',
        unsafe_allow_html=True,
    )

    if st.button(
        "↻ Refresh data",
        use_container_width=True,
        type="secondary",
    ):
        st.cache_data.clear()
        st.rerun()


# ============================================================
# VALIDATION
# ============================================================

if prices.empty:
    st.error(
        "No valid price observations were found in the data folder."
    )
    st.stop()


# ============================================================
# SIDEBAR FILTERS
# ============================================================

st.sidebar.markdown("## Dashboard Filters")

commodities = sorted(
    prices["Commodity"]
    .dropna()
    .astype(str)
    .unique()
)

commodity = st.sidebar.selectbox(
    "Commodity",
    commodities,
)

commodity_data = (
    prices.loc[
        prices["Commodity"].astype(str) == commodity
    ]
    .copy()
    .sort_values("Date")
)


units = sorted(
    commodity_data["Unit"]
    .dropna()
    .astype(str)
    .unique()
)

if not units:
    st.error("No valid units exist for this commodity.")
    st.stop()

unit = (
    st.sidebar.selectbox("Unit", units)
    if len(units) > 1
    else units[0]
)

commodity_data = (
    commodity_data.loc[
        commodity_data["Unit"].astype(str) == unit
    ]
    .copy()
    .sort_values("Date")
)


# Source filter
sources = sorted(
    commodity_data["Source"]
    .dropna()
    .astype(str)
    .unique()
)

if len(sources) > 1:
    selected_sources = st.sidebar.multiselect(
        "Source",
        sources,
        default=sources,
    )

    commodity_data = commodity_data.loc[
        commodity_data["Source"]
        .astype(str)
        .isin(selected_sources)
    ].copy()


if commodity_data.empty:
    st.warning("No data matches the selected filters.")
    st.stop()


# ============================================================
# LATEST / CURRENT MONTH DATA
# ============================================================

commodity_data = commodity_data.sort_values("Date").reset_index(drop=True)

latest = commodity_data.iloc[-1]

latest_date = latest["Date"]
latest_price = float(latest["Price"])

previous = (
    commodity_data.iloc[-2]
    if len(commodity_data) > 1
    else None
)

previous_price = (
    float(previous["Price"])
    if previous is not None
    else None
)

absolute_change = (
    latest_price - previous_price
    if previous_price is not None
    else None
)

percent_change = (
    (absolute_change / previous_price) * 100
    if previous_price not in (None, 0)
    else None
)


# Current month = month of latest available observation
latest_period = latest_date.to_period("M")

current_month = (
    commodity_data.loc[
        commodity_data["Date"].dt.to_period("M") == latest_period
    ]
    .copy()
    .sort_values("Date")
)


month_average = float(current_month["Price"].mean())
month_high = float(current_month["Price"].max())
month_low = float(current_month["Price"].min())
month_observations = len(current_month)


# ============================================================
# KPI CARDS
# ============================================================

st.markdown(
    f'<div class="section-title">{escape(str(commodity))} Market Snapshot</div>',
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="section-description">'
    f'Latest available observation: {latest_date.strftime("%B %d, %Y")}'
    f"</div>",
    unsafe_allow_html=True,
)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    with st.container(border=True):
        st.metric(
            "Latest Price",
            f"{latest_price:,.2f} {unit}",
        )

with kpi2:
    with st.container(border=True):
        if previous_price is not None:
            delta_text = (
                f"{absolute_change:+,.2f} "
                f"({percent_change:+.2f}%)"
            )

            st.metric(
                "Previous Price",
                f"{previous_price:,.2f} {unit}",
                delta=delta_text,
            )
        else:
            st.metric(
                "Previous Price",
                "N/A",
            )

with kpi3:
    with st.container(border=True):
        st.metric(
            f"{latest_period.strftime('%B')} Average",
            f"{month_average:,.2f} {unit}",
        )

with kpi4:
    with st.container(border=True):
        st.metric(
            "Current Month Range",
            f"{month_low:,.2f} – {month_high:,.2f}",
        )


secondary1, secondary2, secondary3 = st.columns(3)

with secondary1:
    with st.container(border=True):
        st.metric(
            "Current Month High",
            f"{month_high:,.2f} {unit}",
        )

with secondary2:
    with st.container(border=True):
        st.metric(
            "Current Month Low",
            f"{month_low:,.2f} {unit}",
        )

with secondary3:
    with st.container(border=True):
        st.metric(
            "Current Month Observations",
            f"{month_observations:,}",
        )


st.divider()


# ============================================================
# HISTORICAL DATE RANGE
# ============================================================

st.sidebar.markdown("---")
st.sidebar.markdown("### Historical Range")

min_date = commodity_data["Date"].min().date()
max_date = commodity_data["Date"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

historical = commodity_data.copy()

if (
    isinstance(date_range, (tuple, list))
    and len(date_range) == 2
):
    start_date, end_date = date_range

    historical = historical.loc[
        (historical["Date"].dt.date >= start_date)
        & (historical["Date"].dt.date <= end_date)
    ].copy()


# ============================================================
# TABS
# ============================================================

overview_tab, month_tab, data_tab = st.tabs(
    [
        "📈 Overview",
        "📅 Current Month",
        "📋 Data",
    ]
)


# ============================================================
# OVERVIEW TAB
# ============================================================

with overview_tab:

    st.markdown(
        '<div class="section-title">Historical Price Trend</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-description">'
        "Historical observations within the selected date range."
        "</div>",
        unsafe_allow_html=True,
    )

    if historical.empty:
        st.info("No observations exist in the selected historical range.")
    else:
        chart_data = (
            historical[["Date", "Price"]]
            .drop_duplicates(subset=["Date"], keep="last")
            .set_index("Date")
        )

        st.line_chart(
            chart_data,
            use_container_width=True,
            height=430,
        )

        history1, history2, history3, history4 = st.columns(4)

        with history1:
            st.metric(
                "Range Average",
                f"{historical['Price'].mean():,.2f}",
            )

        with history2:
            st.metric(
                "Range High",
                f"{historical['Price'].max():,.2f}",
            )

        with history3:
            st.metric(
                "Range Low",
                f"{historical['Price'].min():,.2f}",
            )

        with history4:
            st.metric(
                "Observations",
                f"{len(historical):,}",
            )


# ============================================================
# CURRENT MONTH TAB
# ============================================================

with month_tab:

    month_name = latest_period.strftime("%B %Y")

    st.markdown(
        f'<div class="section-title">{month_name} Prices</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-description">'
        "Daily price observations during the latest available month."
        "</div>",
        unsafe_allow_html=True,
    )

    if current_month.empty:
        st.info("No observations are available for the current month.")

    else:

        current_chart = (
            current_month[["Date", "Price"]]
            .drop_duplicates(
                subset=["Date"],
                keep="last",
            )
            .set_index("Date")
        )

        st.line_chart(
            current_chart,
            use_container_width=True,
            height=430,
        )

        month_stats1, month_stats2, month_stats3, month_stats4 = (
            st.columns(4)
        )

        with month_stats1:
            st.metric(
                "Opening Price",
                f"{current_month.iloc[0]['Price']:,.2f}",
            )

        with month_stats2:
            st.metric(
                "Latest Price",
                f"{current_month.iloc[-1]['Price']:,.2f}",
            )

        with month_stats3:
            month_change = (
                current_month.iloc[-1]["Price"]
                - current_month.iloc[0]["Price"]
            )

            month_pct = (
                month_change
                / current_month.iloc[0]["Price"]
                * 100
                if current_month.iloc[0]["Price"] != 0
                else 0
            )

            st.metric(
                "Month Change",
                f"{month_change:+,.2f}",
                delta=f"{month_pct:+.2f}%",
            )

        with month_stats4:
            st.metric(
                "Average",
                f"{month_average:,.2f}",
            )

        st.markdown("#### Current Month Observations")

        month_table = current_month[
            [
                "Date",
                "Price",
                "Unit",
                "Source",
            ]
        ].copy()

        month_table["Change"] = (
            month_table["Price"].diff()
        )

        month_table["Change %"] = (
            month_table["Price"]
            .pct_change()
            .mul(100)
        )

        month_table = month_table.sort_values(
            "Date",
            ascending=False,
        )

        st.dataframe(
            month_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Date": st.column_config.DateColumn(
                    "Date",
                    format="MMM DD, YYYY",
                ),
                "Price": st.column_config.NumberColumn(
                    "Price",
                    format="%.2f",
                ),
                "Change": st.column_config.NumberColumn(
                    "Daily Change",
                    format="%+.2f",
                ),
                "Change %": st.column_config.NumberColumn(
                    "Daily Change %",
                    format="%+.2f%%",
                ),
            },
        )


# ============================================================
# DATA TAB
# ============================================================

with data_tab:

    st.markdown(
        '<div class="section-title">Underlying Data</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-description">'
        "All observations matching the selected commodity, unit and source."
        "</div>",
        unsafe_allow_html=True,
    )

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
        if column in commodity_data.columns
    ]

    display_data = (
        commodity_data[display_columns]
        .sort_values("Date", ascending=False)
        .copy()
    )

    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Date": st.column_config.DateColumn(
                "Date",
                format="MMM DD, YYYY",
            ),
            "Price": st.column_config.NumberColumn(
                "Price",
                format="%.2f",
            ),
        },
    )

    csv_bytes = display_data.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        "↓ Download filtered data",
        data=csv_bytes,
        file_name=(
            f"{commodity.lower().replace(' ', '_')}"
            "_prices.csv"
        ),
        mime="text/csv",
        use_container_width=False,
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    f"Dashboard refreshed {datetime.now().strftime('%Y-%m-%d %H:%M')} • "
    "Source: GitHub repository data"
)
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from fertilizer_data import FERTILIZER_PRODUCTS, REGIONS


REGIONAL_FILE = Path("regional_data/fertilizer_regional_prices.csv")
NATIONAL_FILE = Path("data/fertilizer_prices.csv")


st.set_page_config(
    page_title="Regional Fertilizer Prices",
    page_icon="🗺️",
    layout="wide",
)

st.title("Regional Fertilizer Prices")
st.caption(
    "Latest available FertilizerPrice.com regional observations, "
    "with the matching national average when available."
)


@st.cache_data(ttl=300)
def load_regional_data() -> pd.DataFrame:
    if not REGIONAL_FILE.exists():
        return pd.DataFrame()

    frame = pd.read_csv(REGIONAL_FILE)
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame["Price"] = pd.to_numeric(frame["Price"], errors="coerce")

    return (
        frame.dropna(subset=["Date", "Commodity", "Region", "Price"])
        .sort_values(["Commodity", "Date", "Region"])
        .reset_index(drop=True)
    )


@st.cache_data(ttl=300)
def load_national_data() -> pd.DataFrame:
    if not NATIONAL_FILE.exists():
        return pd.DataFrame()

    frame = pd.read_csv(NATIONAL_FILE)
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame["Price"] = pd.to_numeric(frame["Price"], errors="coerce")

    required = ["Date", "Commodity", "Price"]
    return (
        frame.dropna(subset=required)
        .sort_values(["Commodity", "Date"])
        .reset_index(drop=True)
    )


regional = load_regional_data()
national = load_national_data()

if regional.empty:
    st.warning("No regional fertilizer data is available yet.")
    st.stop()


available_products = set(regional["Commodity"].astype(str).unique())
products = [
    product for product in FERTILIZER_PRODUCTS
    if product in available_products
]
products.extend(
    sorted(available_products.difference(products))
)

default_product_index = (
    products.index("Urea")
    if "Urea" in products
    else 0
)

st.sidebar.markdown("## Regional Filters")

product = st.sidebar.selectbox(
    "Fertilizer",
    products,
    index=default_product_index,
)

product_data = (
    regional.loc[regional["Commodity"].astype(str) == product]
    .copy()
    .sort_values("Date")
)

dates = sorted(
    product_data["Date"].dt.date.unique(),
    reverse=True,
)

selected_date = st.sidebar.selectbox(
    "Observation date",
    dates,
    index=0,
    help="The newest regional observation for the selected fertilizer is shown first.",
)

snapshot = (
    product_data.loc[
        product_data["Date"].dt.date == selected_date
    ]
    .copy()
    .sort_values("Region")
)

regional_latest_date = product_data["Date"].max()
overall_regional_latest_date = regional["Date"].max()

product_national = pd.DataFrame()
if not national.empty:
    product_national = (
        national.loc[
            national["Commodity"].astype(str) == product
        ]
        .copy()
        .sort_values("Date")
    )

national_latest_date = (
    product_national["Date"].max()
    if not product_national.empty
    else pd.NaT
)

matching_national = pd.DataFrame()
if not product_national.empty:
    matching_national = product_national.loc[
        product_national["Date"].dt.date == selected_date
    ].copy()

national_price = (
    float(matching_national.iloc[-1]["Price"])
    if not matching_national.empty
    else None
)

unit = (
    str(snapshot["Unit"].dropna().iloc[-1])
    if "Unit" in snapshot.columns and snapshot["Unit"].notna().any()
    else "USD/short ton"
)

st.caption(
    f"Latest regional observation for {product}: "
    f"{regional_latest_date.strftime('%B %d, %Y')}"
)

if (
    pd.notna(national_latest_date)
    and regional_latest_date.normalize() < national_latest_date.normalize()
):
    st.info(
        f"Regional coverage for {product} currently ends on "
        f"{regional_latest_date.strftime('%B %d, %Y')}. "
        f"The national series continues through "
        f"{national_latest_date.strftime('%B %d, %Y')}."
    )
elif regional_latest_date.normalize() < overall_regional_latest_date.normalize():
    st.info(
        f"This fertilizer's latest regional observation is "
        f"{regional_latest_date.strftime('%B %d, %Y')}; "
        f"other fertilizers have regional data through "
        f"{overall_regional_latest_date.strftime('%B %d, %Y')}."
    )


kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    with st.container(border=True):
        st.metric(
            "National Average",
            f"${national_price:,.2f}" if national_price is not None else "N/A",
        )
        st.caption(
            f"{unit} • matching date"
            if national_price is not None
            else "No national observation for this date"
        )

with kpi2:
    with st.container(border=True):
        st.metric(
            "Regional Average",
            f"${snapshot['Price'].mean():,.2f}",
        )
        st.caption(unit)

with kpi3:
    with st.container(border=True):
        st.metric(
            "Regions Reported",
            f"{snapshot['Region'].nunique():,}",
        )
        st.caption("Published regional observations")

with kpi4:
    with st.container(border=True):
        st.metric(
            "Observation Date",
            pd.Timestamp(selected_date).strftime("%b %d, %Y"),
        )
        st.caption("Selected regional snapshot")


st.subheader(f"{product} by region")
st.caption(
    f"Regional prices for "
    f"{pd.Timestamp(selected_date).strftime('%B %d, %Y')}."
)

chart = (
    snapshot[["Region", "Price"]]
    .drop_duplicates("Region", keep="last")
    .set_index("Region")
)

st.bar_chart(
    chart,
    use_container_width=True,
    height=430,
)


st.subheader("Regional observations")

ordered = snapshot.copy()
ordered["Region"] = pd.Categorical(
    ordered["Region"],
    categories=REGIONS,
    ordered=True,
)
ordered = ordered.sort_values("Region")

display_columns = [
    column
    for column in [
        "Date",
        "Commodity",
        "Region",
        "Price",
        "Unit",
        "Source",
        "Retrieved_At",
    ]
    if column in ordered.columns
]

st.dataframe(
    ordered[display_columns],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Date": st.column_config.DateColumn(
            "Date",
            format="MMM DD, YYYY",
        ),
        "Price": st.column_config.NumberColumn(
            "Price",
            format="$%.2f",
        ),
    },
)


st.divider()
st.subheader("Latest regional coverage by fertilizer")
st.caption(
    "Each row uses that fertilizer's newest available regional observation. "
    "Dates can differ because FertilizerPrice.com does not publish every "
    "product/region combination on every report date."
)

latest_rows: list[dict[str, object]] = []

for fertilizer, group in regional.groupby("Commodity", sort=False):
    latest_date = group["Date"].max()
    latest_group = group.loc[group["Date"] == latest_date].copy()

    national_match = pd.DataFrame()
    if not national.empty:
        national_match = national.loc[
            (national["Commodity"].astype(str) == str(fertilizer))
            & (national["Date"].dt.normalize() == latest_date.normalize())
        ].copy()

    latest_rows.append(
        {
            "Fertilizer": fertilizer,
            "Latest regional date": latest_date,
            "Regional average": latest_group["Price"].mean(),
            "Regional low": latest_group["Price"].min(),
            "Regional high": latest_group["Price"].max(),
            "Regions": latest_group["Region"].nunique(),
            "National average": (
                float(national_match.iloc[-1]["Price"])
                if not national_match.empty
                else None
            ),
        }
    )

coverage = pd.DataFrame(latest_rows)

coverage_order = {
    product_name: index
    for index, product_name in enumerate(FERTILIZER_PRODUCTS)
}
coverage["_order"] = coverage["Fertilizer"].map(
    coverage_order
).fillna(len(coverage_order))
coverage = (
    coverage.sort_values(["_order", "Fertilizer"])
    .drop(columns="_order")
    .reset_index(drop=True)
)

st.dataframe(
    coverage,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Latest regional date": st.column_config.DateColumn(
            "Latest regional date",
            format="MMM DD, YYYY",
        ),
        "Regional average": st.column_config.NumberColumn(
            "Regional average",
            format="$%.2f",
        ),
        "Regional low": st.column_config.NumberColumn(
            "Regional low",
            format="$%.2f",
        ),
        "Regional high": st.column_config.NumberColumn(
            "Regional high",
            format="$%.2f",
        ),
        "National average": st.column_config.NumberColumn(
            "National average",
            format="$%.2f",
        ),
        "Regions": st.column_config.NumberColumn(
            "Regions",
            format="%d",
        ),
    },
)

st.info(
    "Blank regions mean FertilizerPrice.com did not publish an observation "
    "for that product/date. No values are interpolated."
)

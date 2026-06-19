import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard import analytics, business_logic, charts, data_loader, forecasting, insights

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sadat.dashboard")

COMPANY_NAME = "Sadat Surgical and Medical Supplies"
PRODUCT_TITLE = "Inventory Intelligence"
TAGLINE = "Smart insights for better inventory decisions"

PAGE_OVERVIEW = "Inventory Overview"
PAGE_SALES = "Sales & Demand"
PAGE_FORECAST = "7-Day Demand Forecast"
PAGE_ATTENTION = "Needs Attention"
PAGE_REORDER = "Reorder Recommendations"
PAGE_PRODUCTS = "Products"
PAGE_STORY = "Business Story"

PAGES = {
    PAGE_OVERVIEW: "📊",
    PAGE_SALES: "📈",
    PAGE_FORECAST: "🔮",
    PAGE_ATTENTION: "⚠️",
    PAGE_REORDER: "🛒",
    PAGE_PRODUCTS: "🏆",
    PAGE_STORY: "📖",
}

ALL_CATEGORIES = "All Categories"
ALL_STATUSES = "All Statuses"

DATE_RANGES = {
    "Last 7 Days": 7,
    "Last 30 Days": 30,
    "Last 90 Days": 90,
    "Last 6 Months": 182,
    "Last 12 Months": 365,
    "Custom Range": None,
}

FRIENDLY_ERROR = (
    "We're unable to load this information right now. Please refresh the dashboard."
)

STYLES = """
<style>
    #MainMenu, footer, header [data-testid="stToolbar"] {visibility: hidden;}
    .stDeployButton {display: none;}

    .stApp {
        background: linear-gradient(180deg, #F6F8FB 0%, #EEF3F7 100%);
    }

    .block-container {
        padding-top: 2.2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0F4C5C 0%, #103F4C 100%);
    }

    section[data-testid="stSidebar"] * {
        color: #E8F1F3;
    }

    section[data-testid="stSidebar"] .stRadio label p {
        font-size: 0.95rem;
        font-weight: 500;
    }

    section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
    section[data-testid="stSidebar"] div[data-baseweb="input"],
    section[data-testid="stSidebar"] input {
        background-color: rgba(255, 255, 255, 0.10);
        border-color: rgba(232, 241, 243, 0.30);
        color: #FFFFFF;
    }

    section[data-testid="stSidebar"] div[data-baseweb="base-input"] {
        background-color: transparent;
    }

    section[data-testid="stSidebar"] input::placeholder {
        color: rgba(232, 241, 243, 0.55);
    }

    section[data-testid="stSidebar"] div[data-baseweb="select"] svg {
        fill: rgba(232, 241, 243, 0.75);
    }

    section[data-testid="stSidebar"] .stButton button {
        background-color: rgba(255, 255, 255, 0.12);
        border: 1px solid rgba(232, 241, 243, 0.35);
        color: #FFFFFF;
        font-weight: 600;
    }

    section[data-testid="stSidebar"] .stButton button:hover {
        background-color: rgba(255, 255, 255, 0.22);
        border-color: #8FD6C9;
        color: #FFFFFF;
    }

    .brand-block {
        padding: 0.4rem 0 1.1rem 0;
        border-bottom: 1px solid rgba(232, 241, 243, 0.18);
        margin-bottom: 1.2rem;
    }

    .brand-name {
        font-size: 1.20rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        line-height: 1.35;
        color: #FFFFFF;
    }

    .brand-sub {
        font-size: 0.78rem;
        font-weight: 500;
        letter-spacing: 0.18em;
        color: rgba(232, 241, 243, 0.72);
        margin-top: 0.15rem;
    }

    .brand-product {
        margin-top: 0.85rem;
        font-size: 0.80rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: #8FD6C9;
        font-weight: 600;
    }

    .page-header {
        margin-bottom: 1.4rem;
    }

    .page-header .company {
        font-size: 0.80rem;
        letter-spacing: 0.20em;
        text-transform: uppercase;
        color: #5C7183;
        font-weight: 600;
    }

    .page-header .title {
        font-size: 2.15rem;
        font-weight: 700;
        color: #16202B;
        line-height: 1.2;
        margin-top: 0.25rem;
    }

    .page-header .tagline {
        font-size: 1.0rem;
        color: #6B7A8C;
        margin-top: 0.35rem;
    }

    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E6ECF2;
        border-radius: 16px;
        padding: 1.05rem 1.2rem 1.1rem 1.2rem;
        box-shadow: 0 6px 18px rgba(22, 32, 43, 0.05);
        height: 100%;
    }

    .kpi-card .kpi-label {
        font-size: 0.78rem;
        letter-spacing: 0.10em;
        text-transform: uppercase;
        color: #6B7A8C;
        font-weight: 600;
    }

    .kpi-card .kpi-value {
        font-size: 2.05rem;
        font-weight: 700;
        color: #16202B;
        line-height: 1.25;
        margin-top: 0.30rem;
    }

    .kpi-card .kpi-caption {
        font-size: 0.82rem;
        color: #7C8B9B;
        margin-top: 0.15rem;
    }

    .kpi-accent {
        height: 4px;
        width: 42px;
        border-radius: 4px;
        margin-bottom: 0.85rem;
    }

    .panel-title {
        font-size: 1.18rem;
        font-weight: 700;
        color: #16202B;
        margin-bottom: 0.15rem;
    }

    .panel-note {
        font-size: 0.93rem;
        color: #6B7A8C;
        margin-bottom: 0.6rem;
    }

    .interpretation {
        background: #F2F7F8;
        border-left: 3px solid #2A9D8F;
        border-radius: 8px;
        padding: 0.75rem 0.95rem;
        color: #33475B;
        font-size: 0.94rem;
        line-height: 1.5;
    }

    .insight-item {
        background: #FFFFFF;
        border: 1px solid #E6ECF2;
        border-radius: 12px;
        padding: 0.8rem 0.95rem;
        margin-bottom: 0.6rem;
        color: #33475B;
        font-size: 0.93rem;
        line-height: 1.5;
        box-shadow: 0 3px 10px rgba(22, 32, 43, 0.04);
    }

    .attention-card {
        background: #FFFFFF;
        border: 1px solid #E6ECF2;
        border-left: 5px solid #8D99AE;
        border-radius: 14px;
        padding: 0.95rem 1.1rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 4px 14px rgba(22, 32, 43, 0.05);
    }

    .attention-card .product {
        font-size: 1.05rem;
        font-weight: 700;
        color: #16202B;
    }

    .attention-card .category {
        font-size: 0.78rem;
        color: #8494A4;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }

    .attention-figures {
        display: flex;
        gap: 1.8rem;
        margin-top: 0.7rem;
    }

    .attention-figures .figure-label {
        font-size: 0.74rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #8494A4;
        font-weight: 600;
    }

    .attention-figures .figure-value {
        font-size: 1.25rem;
        font-weight: 700;
        color: #16202B;
    }

    .status-pill {
        display: inline-block;
        padding: 0.18rem 0.65rem;
        border-radius: 999px;
        font-size: 0.80rem;
        font-weight: 600;
        margin-top: 0.75rem;
    }

    .action-line {
        margin-top: 0.65rem;
        font-size: 0.90rem;
        color: #33475B;
    }

    .action-line strong {
        color: #16202B;
    }

    .story-card {
        background: #FFFFFF;
        border: 1px solid #E6ECF2;
        border-radius: 16px;
        padding: 1.25rem 1.45rem;
        margin-bottom: 0.9rem;
        box-shadow: 0 5px 16px rgba(22, 32, 43, 0.05);
    }

    .story-card .story-heading {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0F4C5C;
        margin-bottom: 0.35rem;
    }

    .story-card .story-body {
        font-size: 0.97rem;
        color: #33475B;
        line-height: 1.6;
    }

    .section-heading {
        font-size: 1.45rem;
        font-weight: 700;
        color: #16202B;
        margin: 0.8rem 0 0.4rem 0;
    }

    .updated-note {
        font-size: 0.80rem;
        color: rgba(232, 241, 243, 0.70);
        margin-top: 0.6rem;
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.6rem;
    }
</style>
"""


@st.cache_data(show_spinner=False)
def load_dataset():
    return data_loader.load_business_data()


@st.cache_data(show_spinner=False)
def load_forecast(sales):
    return forecasting.build_weekly_forecast(sales)


def kpi_card(label, value, caption, accent):
    return (
        f"<div class='kpi-card'>"
        f"<div class='kpi-accent' style='background:{accent};'></div>"
        f"<div class='kpi-label'>{label}</div>"
        f"<div class='kpi-value'>{value}</div>"
        f"<div class='kpi-caption'>{caption}</div>"
        f"</div>"
    )


def render_kpi_row(cards):
    columns = st.columns(len(cards), gap="medium")
    for column, card in zip(columns, cards):
        with column:
            st.markdown(kpi_card(*card), unsafe_allow_html=True)


def render_page_header(title, tagline):
    st.markdown(
        f"<div class='page-header'>"
        f"<div class='company'>{COMPANY_NAME}</div>"
        f"<div class='title'>{title}</div>"
        f"<div class='tagline'>{tagline}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_panel_title(title, note=None):
    markup = f"<div class='panel-title'>{title}</div>"
    if note:
        markup += f"<div class='panel-note'>{note}</div>"
    st.markdown(markup, unsafe_allow_html=True)


def render_interpretation(message):
    st.markdown(f"<div class='interpretation'>{message}</div>", unsafe_allow_html=True)


def status_pill(status):
    colour = charts.STATUS_COLOURS[status]
    icon = business_logic.STATUS_ICONS[status]
    return (
        f"<span class='status-pill' style='background:{colour}1F;color:{colour};'>"
        f"{icon} {status}</span>"
    )


def render_attention_card(row):
    colour = charts.STATUS_COLOURS[row["status"]]
    unit = row["unit_of_measure"]
    st.markdown(
        f"<div class='attention-card' style='border-left-color:{colour};'>"
        f"<div class='product'>{row['product_name']}</div>"
        f"<div class='category'>{row['category']}</div>"
        f"<div class='attention-figures'>"
        f"<div><div class='figure-label'>Current Stock</div>"
        f"<div class='figure-value'>{int(row['current_stock']):,} {unit}</div></div>"
        f"<div><div class='figure-label'>Expected 7-Day Demand</div>"
        f"<div class='figure-value'>{int(row['expected_demand']):,} {unit}</div></div>"
        f"</div>"
        f"{status_pill(row['status'])}"
        f"<div class='action-line'>Suggested action: "
        f"<strong>{row['suggested_action']}</strong></div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_setup_notice():
    st.markdown(STYLES, unsafe_allow_html=True)
    render_page_header(PRODUCT_TITLE, TAGLINE)
    st.warning(
        "The business data for this dashboard has not been prepared yet. "
        "Please run the setup step below once, then reopen the dashboard."
    )
    st.code(data_loader.SETUP_COMMAND, language="text")


def render_friendly_error():
    st.error(FRIENDLY_ERROR)


def resolve_date_window(sales, range_label, custom_range):
    latest = data_loader.latest_business_date(sales)
    earliest = data_loader.earliest_business_date(sales)
    if range_label == "Custom Range" and custom_range:
        start = pd.Timestamp(custom_range[0])
        end = pd.Timestamp(custom_range[-1])
        return max(start, earliest), min(end, latest)
    days = DATE_RANGES[range_label] or 30
    return max(latest - pd.Timedelta(days=days - 1), earliest), latest


def build_sidebar(products, sales, generated_on):
    with st.sidebar:
        st.markdown(
            "<div class='brand-block'>"
            "<div class='brand-name'>SADAT SURGICAL</div>"
            "<div class='brand-sub'>&amp; MEDICAL SUPPLIES</div>"
            "<div class='brand-product'>Inventory Intelligence</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        page = st.radio(
            "Go to",
            list(PAGES.keys()),
            format_func=lambda name: f"{PAGES[name]}  {name}",
            label_visibility="collapsed",
        )
        st.markdown("---")
        st.markdown("**Filters**")
        range_label = st.selectbox("Period", list(DATE_RANGES.keys()), index=1)
        custom_range = None
        if range_label == "Custom Range":
            custom_range = st.date_input(
                "Choose dates",
                value=(
                    data_loader.latest_business_date(sales) - pd.Timedelta(days=29),
                    data_loader.latest_business_date(sales),
                ),
                min_value=data_loader.earliest_business_date(sales),
                max_value=data_loader.latest_business_date(sales),
            )
        category = st.selectbox(
            "Category", [ALL_CATEGORIES] + sorted(products["category"].unique())
        )
        status_choice = st.selectbox(
            "Inventory status", [ALL_STATUSES] + business_logic.STATUS_SEQUENCE
        )
        search_term = st.text_input(
            "Find a product",
            placeholder="e.g. Surgical Gloves",
            help="Narrows the product lists on the product, forecast and reorder pages.",
        )
        st.markdown("---")
        if st.button("🔄 Refresh Dashboard", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.markdown(
            f"<div class='updated-note'>Last updated: "
            f"{datetime.now().strftime('%d %B %Y, %I:%M %p')}<br>"
            f"Business data prepared on {generated_on}</div>",
            unsafe_allow_html=True,
        )
    return {
        "page": page,
        "range_label": range_label,
        "custom_range": custom_range,
        "category": category,
        "status": status_choice,
        "search": search_term.strip(),
    }


def apply_product_filters(status_table, selections, include_search=True):
    filtered = status_table
    if selections["category"] != ALL_CATEGORIES:
        filtered = filtered[filtered["category"] == selections["category"]]
    if selections["status"] != ALL_STATUSES:
        filtered = filtered[filtered["status"] == selections["status"]]
    if include_search and selections["search"]:
        filtered = filtered[
            filtered["product_name"].str.contains(
                selections["search"], case=False, na=False, regex=False
            )
        ]
    return filtered.reset_index(drop=True)


def aggregate_forecast(forecast, product_ids):
    selected = forecast[forecast["product_id"].isin(product_ids)]
    if selected.empty:
        return pd.DataFrame(columns=["forecast_date", "expected_units", "day_name"])
    totals = selected.groupby("forecast_date", as_index=False)["expected_units"].sum()
    totals["day_name"] = totals["forecast_date"].dt.day_name()
    return totals


def period_length_days(context):
    return int((context["end_date"] - context["start_date"]).days) + 1


def period_trend_message(context):
    return insights.generate_sales_insight(
        context["sales_in_scope"], context["end_date"], period_length_days(context)
    )


def daily_totals(sales):
    if sales.empty:
        return pd.DataFrame(columns=["sale_date", "units_sold"])
    return sales.groupby("sale_date", as_index=False)["units_sold"].sum()


def render_overview(context):
    sales_in_scope = context["sales_in_scope"]
    period_sales = context["period_sales"]
    status_scope = context["status_scope"]
    forecast = context["forecast"]
    reference_date = context["reference_date"]

    render_page_header(PRODUCT_TITLE, TAGLINE)

    counts = business_logic.status_counts(status_scope)
    period_units = int(period_sales["units_sold"].sum())
    scoped_forecast = aggregate_forecast(forecast, status_scope["product_id"])
    expected_week = int(round(scoped_forecast["expected_units"].sum()))

    render_kpi_row(
        [
            (
                "Total Products",
                f"{len(status_scope):,}",
                "Products in the catalogue",
                charts.DEEP_TEAL,
            ),
            (
                "In Stock",
                f"{business_logic.in_stock_count(status_scope):,}",
                "Products with units available",
                charts.STATUS_COLOURS[business_logic.HEALTHY],
            ),
            (
                "Low Stock",
                f"{business_logic.low_stock_count(status_scope):,}",
                "Close to or below expected demand",
                charts.STATUS_COLOURS[business_logic.ATTENTION],
            ),
        ]
    )
    st.write("")
    render_kpi_row(
        [
            (
                "Out of Stock",
                f"{counts[business_logic.OUT_OF_STOCK]:,}",
                "Products with no units left",
                charts.STATUS_COLOURS[business_logic.CRITICAL],
            ),
            (
                "Recent Sales",
                f"{period_units:,}",
                f"Units sold · {context['range_label'].lower()}",
                charts.SLATE_BLUE,
            ),
            (
                "Expected 7-Day Demand",
                f"{expected_week:,}",
                "Units likely needed this week",
                charts.SAND,
            ),
        ]
    )

    st.write("")
    health_column, insight_column = st.columns([1.15, 1], gap="large")
    with health_column:
        with st.container(border=True):
            render_panel_title("Inventory Health", "How stock compares with expected demand")
            st.plotly_chart(
                charts.inventory_health_donut(
                    business_logic.status_summary_frame(status_scope)
                ),
                use_container_width=True,
            )
            render_interpretation(insights.generate_inventory_insight(status_scope))
    with insight_column:
        with st.container(border=True):
            render_panel_title("💡 Business Insights", "Generated from the latest business data")
            for message in insights.generate_business_insights(
                sales_in_scope, status_scope, reference_date
            ):
                st.markdown(
                    f"<div class='insight-item'>💡 {message}</div>",
                    unsafe_allow_html=True,
                )

    st.write("")
    with st.container(border=True):
        render_panel_title("Sales Trend", f"Units sold · {context['range_label'].lower()}")
        granularity = st.radio(
            "View sales by",
            analytics.GRANULARITIES,
            horizontal=True,
            label_visibility="collapsed",
            key="overview_granularity",
        )
        st.plotly_chart(
            charts.sales_trend_line(
                analytics.sales_over_time(period_sales, granularity), granularity
            ),
            use_container_width=True,
        )
        render_interpretation(period_trend_message(context))

    st.write("")
    with st.container(border=True):
        render_panel_title(
            "🔮 Expected Demand, Next 7 Days",
            "Recent sales followed by the demand expected across the products in view",
        )
        history = daily_totals(
            analytics.filter_sales(
                sales_in_scope,
                start_date=reference_date - pd.Timedelta(days=44),
                end_date=reference_date,
            )
        )
        st.plotly_chart(
            charts.demand_forecast_line(history, scoped_forecast, "All Products", "units"),
            use_container_width=True,
        )

    st.write("")
    best_column, attention_column = st.columns([1.2, 1], gap="large")
    with best_column:
        with st.container(border=True):
            render_panel_title(
                "Best-Selling Products", f"Top sellers · {context['range_label'].lower()}"
            )
            leaders = analytics.top_products(period_sales, limit=8)
            if leaders.empty:
                st.info("No sales were recorded for this selection.")
            else:
                st.plotly_chart(
                    charts.top_products_bar(leaders, title=""), use_container_width=True
                )
    with attention_column:
        with st.container(border=True):
            render_panel_title("⚠️ Needs Attention", "Products to look at first")
            attention = business_logic.products_needing_attention(status_scope).head(4)
            if attention.empty:
                st.success("Every product currently holds enough stock for expected demand.")
            else:
                for _, row in attention.iterrows():
                    render_attention_card(row)


def render_sales(context):
    period_sales = context["period_sales"]
    render_page_header("Sales & Demand", "What customers have been buying")

    if period_sales.empty:
        st.info("No sales were recorded for this selection. Try widening the period or category.")
        return

    render_kpi_row(
        [
            (
                "Units Sold",
                f"{int(period_sales['units_sold'].sum()):,}",
                f"{context['range_label']}",
                charts.DEEP_TEAL,
            ),
            (
                "Average Per Day",
                f"{period_sales.groupby('sale_date')['units_sold'].sum().mean():,.0f}",
                "Across the selected period",
                charts.TEAL,
            ),
            (
                "Products Sold",
                f"{int((period_sales.groupby('product_id')['units_sold'].sum() > 0).sum()):,}",
                "Products with recorded sales",
                charts.SLATE_BLUE,
            ),
        ]
    )

    st.write("")
    with st.container(border=True):
        render_panel_title("Sales Trend")
        granularity = st.radio(
            "View sales by",
            analytics.GRANULARITIES,
            horizontal=True,
            label_visibility="collapsed",
            key="sales_granularity",
        )
        st.plotly_chart(
            charts.sales_trend_line(
                analytics.sales_over_time(period_sales, granularity), granularity
            ),
            use_container_width=True,
        )
        render_interpretation(period_trend_message(context))

    st.write("")
    category_column, weekday_column = st.columns(2, gap="large")
    with category_column:
        with st.container(border=True):
            category_totals = analytics.sales_by_category(period_sales)
            st.plotly_chart(charts.category_bar(category_totals), use_container_width=True)
            if len(category_totals) > 1:
                leader = category_totals.iloc[0]
                render_interpretation(
                    f"{leader['category']} contribute the larger share of units sold, at about "
                    f"{insights.format_percentage(leader['share'])} of the total."
                )
    with weekday_column:
        with st.container(border=True):
            st.plotly_chart(
                charts.weekday_pattern_bar(analytics.weekday_demand_pattern(period_sales)),
                use_container_width=True,
            )
            ratio = analytics.weekday_versus_weekend(period_sales)
            if ratio > 1.05:
                render_interpretation(
                    "Weekdays are consistently busier than weekends, which is worth keeping in "
                    "mind when planning deliveries and stock arrivals."
                )
            else:
                render_interpretation(
                    "Demand is spread fairly evenly across the days of the week."
                )

    st.write("")
    top_column, slow_column = st.columns(2, gap="large")
    with top_column:
        with st.container(border=True):
            st.plotly_chart(
                charts.top_products_bar(analytics.top_products(period_sales, limit=8)),
                use_container_width=True,
            )
    with slow_column:
        with st.container(border=True):
            st.plotly_chart(
                charts.slow_moving_bar(analytics.slow_moving_products(period_sales, limit=8)),
                use_container_width=True,
            )
            render_interpretation(
                "These products have relatively low recent sales and may require closer "
                "monitoring."
            )


def product_selector(status_view, key):
    names = sorted(status_view["product_name"].tolist())
    chosen_name = st.selectbox("Select a product", names, key=key)
    return status_view[status_view["product_name"] == chosen_name].iloc[0]


def render_product_summary_cards(product_row):
    unit = product_row["unit_of_measure"]
    render_kpi_row(
        [
            (
                "Current Stock",
                f"{int(product_row['current_stock']):,}",
                f"{unit} available now",
                charts.DEEP_TEAL,
            ),
            (
                "Recent Sales",
                f"{int(product_row['recent_units_sold']):,}",
                f"{unit} sold in the last 7 days",
                charts.SLATE_BLUE,
            ),
            (
                "Expected 7-Day Demand",
                f"{int(product_row['expected_demand']):,}",
                f"{unit} likely needed",
                charts.SAND,
            ),
            (
                "Inventory Status",
                f"{business_logic.STATUS_ICONS[product_row['status']]} {product_row['status']}",
                business_logic.format_days_of_cover(product_row["days_of_cover"]),
                charts.STATUS_COLOURS[product_row["status"]],
            ),
        ]
    )


def render_forecast(context):
    status_view = context["status_view"]
    sales = context["sales"]
    forecast = context["forecast"]

    render_page_header("🔮 7-Day Demand Forecast", "What customers may need next")

    if status_view.empty:
        st.info("No products match the current filters.")
        return

    product_row = product_selector(status_view, "forecast_product")
    st.write("")
    render_product_summary_cards(product_row)

    product_sales = sales[sales["product_id"] == product_row["product_id"]]
    product_forecast = forecasting.product_forecast(forecast, product_row["product_id"])
    recent_history = product_sales[
        product_sales["sale_date"] >= context["reference_date"] - pd.Timedelta(days=59)
    ]

    st.write("")
    with st.container(border=True):
        st.plotly_chart(
            charts.demand_forecast_line(
                recent_history,
                product_forecast,
                product_row["product_name"],
                product_row["unit_of_measure"],
            ),
            use_container_width=True,
        )
        render_interpretation(
            insights.generate_forecast_insight(
                product_row["product_name"],
                int(product_row["current_stock"]),
                int(product_row["expected_demand"]),
                product_row["unit_of_measure"],
            )
        )

    st.write("")
    daily_column, table_column = st.columns([1.35, 1], gap="large")
    with daily_column:
        with st.container(border=True):
            st.plotly_chart(
                charts.expected_demand_bar(product_forecast, product_row["unit_of_measure"]),
                use_container_width=True,
            )
    with table_column:
        with st.container(border=True):
            render_panel_title("Day By Day", "Expected demand for each of the next seven days")
            display_frame = product_forecast[["forecast_date", "day_name", "expected_units"]].copy()
            display_frame["forecast_date"] = display_frame["forecast_date"].dt.strftime("%d %b %Y")
            display_frame["expected_units"] = display_frame["expected_units"].round().astype(int)
            display_frame.columns = ["Date", "Day", "Expected Units"]
            st.dataframe(display_frame, use_container_width=True, hide_index=True)


def render_attention(context):
    status_view = context["status_view"]
    render_page_header("⚠️ Needs Attention", "Where inventory action matters most")

    if status_view.empty:
        st.info("No products match the current filters.")
        return

    counts = business_logic.status_counts(status_view)
    render_kpi_row(
        [
            (
                "Urgent",
                f"{counts[business_logic.OUT_OF_STOCK] + counts[business_logic.CRITICAL]:,}",
                "Out of stock or below expected demand",
                charts.STATUS_COLOURS[business_logic.CRITICAL],
            ),
            (
                "Attention",
                f"{counts[business_logic.ATTENTION]:,}",
                "Close to expected demand",
                charts.STATUS_COLOURS[business_logic.ATTENTION],
            ),
            (
                "Healthy",
                f"{counts[business_logic.HEALTHY]:,}",
                "Comfortably stocked",
                charts.STATUS_COLOURS[business_logic.HEALTHY],
            ),
        ]
    )

    st.write("")
    render_interpretation(insights.generate_reorder_insight(status_view))

    groups = [
        ("🔴 Urgent", [business_logic.OUT_OF_STOCK, business_logic.CRITICAL]),
        ("🟡 Attention", [business_logic.ATTENTION]),
        ("🟢 Healthy", [business_logic.HEALTHY]),
    ]
    for heading, statuses in groups:
        section = status_view[status_view["status"].isin(statuses)]
        st.markdown(f"<div class='section-heading'>{heading}</div>", unsafe_allow_html=True)
        if section.empty:
            st.markdown(
                "<div class='insight-item'>No products in this group.</div>",
                unsafe_allow_html=True,
            )
            continue
        columns = st.columns(2, gap="medium")
        for position, (_, row) in enumerate(section.iterrows()):
            with columns[position % 2]:
                render_attention_card(row)


def render_reorder(context):
    status_view = context["status_view"]
    render_page_header("🛒 Reorder Recommendations", "What deserves purchasing attention")

    if status_view.empty:
        st.info("No products match the current filters.")
        return

    render_interpretation(insights.generate_reorder_insight(status_view))
    st.write("")

    table = status_view.copy()
    table["Status"] = [
        f"{business_logic.STATUS_ICONS[status]} {status}" for status in table["status"]
    ]
    table["Days of Cover"] = [
        business_logic.format_days_of_cover(value) for value in table["days_of_cover"]
    ]
    display_frame = table[
        [
            "product_name",
            "category",
            "current_stock",
            "expected_demand",
            "Status",
            "suggested_action",
            "Days of Cover",
        ]
    ]
    display_frame.columns = [
        "Product",
        "Category",
        "Current Stock",
        "Expected Demand",
        "Status",
        "Suggested Action",
        "Days of Cover",
    ]
    st.dataframe(
        display_frame,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Current Stock": st.column_config.NumberColumn(format="%d"),
            "Expected Demand": st.column_config.NumberColumn(format="%d"),
        },
    )

    priority = business_logic.products_needing_attention(status_view)
    if not priority.empty:
        st.write("")
        with st.container(border=True):
            render_panel_title(
                "Stock Against Expected Demand",
                "Products where the two figures are closest together",
            )
            st.plotly_chart(
                charts.stock_versus_demand_bar(priority.head(8)), use_container_width=True
            )


def render_products(context):
    status_view = context["status_view"]
    sales = context["sales"]
    forecast = context["forecast"]

    render_page_header("🏆 Products", "A closer look at any product")

    if status_view.empty:
        st.info("No products match the current filters. Try clearing the search or filters.")
        return

    product_row = product_selector(status_view, "explorer_product")
    st.markdown(
        f"<div class='section-heading'>{product_row['product_name']}</div>"
        f"<div class='panel-note'>{product_row['category']}</div>",
        unsafe_allow_html=True,
    )
    render_product_summary_cards(product_row)

    product_sales = sales[sales["product_id"] == product_row["product_id"]]
    period_product_sales = analytics.filter_sales(
        product_sales, start_date=context["start_date"], end_date=context["end_date"]
    )
    product_forecast = forecasting.product_forecast(forecast, product_row["product_id"])

    st.write("")
    history_column, forecast_column = st.columns(2, gap="large")
    with history_column:
        with st.container(border=True):
            render_panel_title("Sales History", f"{context['range_label']}")
            st.plotly_chart(
                charts.sales_trend_line(
                    analytics.sales_over_time(period_product_sales, analytics.WEEKLY), "Weekly"
                ),
                use_container_width=True,
            )
    with forecast_column:
        with st.container(border=True):
            st.plotly_chart(
                charts.expected_demand_bar(product_forecast, product_row["unit_of_measure"]),
                use_container_width=True,
            )

    st.write("")
    stock_column, pattern_column = st.columns(2, gap="large")
    with stock_column:
        with st.container(border=True):
            st.plotly_chart(
                charts.stock_level_line(
                    period_product_sales,
                    product_row["product_name"],
                    product_row["unit_of_measure"],
                ),
                use_container_width=True,
            )
    with pattern_column:
        with st.container(border=True):
            st.plotly_chart(
                charts.weekday_pattern_bar(
                    analytics.weekday_demand_pattern(period_product_sales)
                ),
                use_container_width=True,
            )

    st.write("")
    with st.container(border=True):
        render_panel_title("💡 What this means")
        render_interpretation(
            insights.generate_product_insight(
                product_row, product_sales, context["reference_date"]
            )
        )


def render_story(context):
    render_page_header("📖 Business Story", "The current picture in plain language")
    story = insights.build_business_story(
        context["sales_in_scope"],
        context["status_scope"],
        aggregate_forecast(context["forecast"], context["status_scope"]["product_id"]),
        context["reference_date"],
    )
    for heading, body in story:
        st.markdown(
            f"<div class='story-card'>"
            f"<div class='story-heading'>{heading}</div>"
            f"<div class='story-body'>{body}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.write("")
    with st.container(border=True):
        render_panel_title("💡 Business Insights", "Observations drawn from the latest data")
        for message in insights.generate_business_insights(
            context["sales_in_scope"], context["status_scope"], context["reference_date"]
        ):
            st.markdown(f"<div class='insight-item'>💡 {message}</div>", unsafe_allow_html=True)


PAGE_RENDERERS = {
    PAGE_OVERVIEW: render_overview,
    PAGE_SALES: render_sales,
    PAGE_FORECAST: render_forecast,
    PAGE_ATTENTION: render_attention,
    PAGE_REORDER: render_reorder,
    PAGE_PRODUCTS: render_products,
    PAGE_STORY: render_story,
}


def build_context(products, sales, forecast, selections):
    reference_date = data_loader.latest_business_date(sales)
    start_date, end_date = resolve_date_window(
        sales, selections["range_label"], selections["custom_range"]
    )
    inventory = data_loader.current_inventory(products, sales)
    expected_demand = forecasting.expected_demand_by_product(forecast)
    recent_sales = analytics.recent_sales_by_product(sales, reference_date, 7)
    status_table = business_logic.build_inventory_status(
        inventory, expected_demand, recent_sales
    )
    status_view = apply_product_filters(status_table, selections)
    status_scope = apply_product_filters(status_table, selections, include_search=False)
    categories = None if selections["category"] == ALL_CATEGORIES else [selections["category"]]
    sales_in_scope = analytics.filter_sales(sales, categories=categories)
    period_sales = analytics.filter_sales(
        sales_in_scope, start_date=start_date, end_date=end_date
    )
    return {
        "products": products,
        "sales": sales,
        "sales_in_scope": sales_in_scope,
        "period_sales": period_sales,
        "forecast": forecast,
        "status_table": status_table,
        "status_view": status_view,
        "status_scope": status_scope,
        "reference_date": reference_date,
        "start_date": start_date,
        "end_date": end_date,
        "range_label": selections["range_label"],
        "selections": selections,
    }


def main():
    st.set_page_config(
        page_title=f"{COMPANY_NAME} · {PRODUCT_TITLE}",
        page_icon="🩺",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(STYLES, unsafe_allow_html=True)

    if not data_loader.business_data_is_available():
        render_setup_notice()
        return

    try:
        products, sales, generated_on = load_dataset()
        forecast = load_forecast(sales)
    except Exception:
        logger.exception("Business data could not be prepared")
        render_friendly_error()
        return

    selections = build_sidebar(products, sales, generated_on)

    try:
        context = build_context(products, sales, forecast, selections)
        PAGE_RENDERERS[selections["page"]](context)
    except Exception:
        logger.exception("Dashboard page could not be rendered")
        render_friendly_error()


if __name__ == "__main__":
    main()

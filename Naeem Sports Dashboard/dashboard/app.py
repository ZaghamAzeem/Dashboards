from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard import analytics, charts, data_loader, forecasting, insights, ui
from dashboard import business_logic as rules

PAGE_HOME = "🏠 Shop Home"
PAGE_SALES = "📊 Sales Story"
PAGE_FAVOURITES = "🏆 Customers' Favourites"
PAGE_STOCK = "📦 Stock Room"
PAGE_FORECAST = "🔮 What May Sell Next"
PAGE_SHOPPING = "🛒 Shopping List"

PAGES = [PAGE_HOME, PAGE_SALES, PAGE_FAVOURITES, PAGE_STOCK, PAGE_FORECAST, PAGE_SHOPPING]

CUSTOM_PERIOD = "Custom"
CHART_CONFIG = {"displayModeBar": False}
EMPTY_MESSAGE = "There are no sales in this selection. Try a longer time period or another sport."


def render_sidebar(shop):
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-brand">'
            '<div class="brand-name">🏆 Naeem Sports<br>Goods Shop</div>'
            '<div class="brand-tag">Shop Intelligence Dashboard</div>'
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sidebar-label">Explore</div>', unsafe_allow_html=True)
        page = st.radio("Pages", PAGES, label_visibility="collapsed")

        st.markdown('<div class="sidebar-label">Time Period</div>', unsafe_allow_html=True)
        period_options = list(analytics.PERIOD_CHOICES) + [CUSTOM_PERIOD]
        period_choice = st.selectbox(
            "Time period", period_options, index=1, label_visibility="collapsed"
        )

        latest_day = shop.latest_day
        earliest_day = shop.earliest_day

        if period_choice == CUSTOM_PERIOD:
            default_start = max(earliest_day, latest_day - pd.Timedelta(days=59))
            picked = st.date_input(
                "Custom dates",
                value=(default_start.date(), latest_day.date()),
                min_value=earliest_day.date(),
                max_value=latest_day.date(),
                label_visibility="collapsed",
            )
            if isinstance(picked, (tuple, list)) and len(picked) == 2:
                start, end = pd.Timestamp(picked[0]), pd.Timestamp(picked[1])
            else:
                start, end = default_start, latest_day
            period_label = f"{start:%d %b %Y} to {end:%d %b %Y}"
        else:
            days = analytics.PERIOD_CHOICES[period_choice]
            start = max(earliest_day, analytics.period_start(latest_day, days))
            end = latest_day
            period_label = period_choice

        st.markdown('<div class="sidebar-label">Sport</div>', unsafe_allow_html=True)
        sport = st.selectbox(
            "Sport",
            [analytics.ALL_SPORTS] + shop.sports,
            label_visibility="collapsed",
        )

        st.markdown('<div class="sidebar-label">Shop Data</div>', unsafe_allow_html=True)
        if st.button("🔄 Refresh Shop Data"):
            data_loader.refresh()
            st.rerun()

        st.caption(f"Last updated: {shop.loaded_at:%d %B %Y, %I:%M %p}")

    return {
        "page": page,
        "start": start,
        "end": end,
        "sport": sport,
        "period_label": period_label,
        "period_days": max((end - start).days + 1, 1),
    }


def build_context(shop, forecast, settings):
    latest_day = shop.latest_day
    expected_totals = forecasting.horizon_totals(forecast)
    recent_daily = analytics.recent_daily_average(shop.sales, latest_day)
    overview = rules.build_stock_overview(shop.products, expected_totals, recent_daily)

    shop_period_sales = analytics.slice_by_dates(shop.sales, settings["start"], settings["end"])
    sport_sales = analytics.slice_by_category(shop.sales, settings["sport"])
    period_sales = analytics.slice_by_dates(sport_sales, settings["start"], settings["end"])

    if settings["sport"] == analytics.ALL_SPORTS:
        sport_overview = overview
        sport_forecast = forecast
    else:
        sport_overview = overview.loc[overview["category"] == settings["sport"]].reset_index(
            drop=True
        )
        allowed = set(sport_overview["product_id"])
        sport_forecast = forecast.loc[forecast["product_id"].isin(allowed)]

    momentum_window = max(7, min(45, settings["period_days"] // 2))

    return {
        "shop": shop,
        "settings": settings,
        "latest_day": latest_day,
        "forecast": sport_forecast,
        "overview": sport_overview,
        "sport_sales": sport_sales,
        "period_sales": period_sales,
        "shop_period_sales": shop_period_sales,
        "momentum": analytics.overall_momentum(sport_sales, latest_day, momentum_window),
        "counts": rules.status_counts(sport_overview),
    }


def render_snapshot(context):
    period_sales = context["period_sales"]
    settings = context["settings"]
    overview = context["overview"]
    counts = context["counts"]

    summary = analytics.totals(period_sales)
    leaderboard = analytics.product_leaderboard(period_sales, top_n=1)
    attention = counts[rules.STATUS_OUT] + counts[rules.STATUS_RESTOCK] + counts[rules.STATUS_LOW]
    upcoming_units = float(overview["expected_demand"].sum())

    favourite_name = "Nothing sold yet"
    favourite_caption = "No sales in this selection"
    if not leaderboard.empty:
        favourite = leaderboard.iloc[0]
        favourite_name = favourite["product_name"]
        favourite_caption = f"{rules.format_units(favourite['units'])} units sold in this period"

    columns = st.columns(4, gap="medium")
    with columns[0]:
        st.markdown(
            ui.snapshot_card(
                "💰",
                "Sales",
                rules.format_currency(summary["revenue"]),
                f"{rules.format_units(summary['units'])} units sold · {settings['period_label']}",
                tone="sales",
            ),
            unsafe_allow_html=True,
        )
    with columns[1]:
        st.markdown(
            ui.snapshot_card(
                "🥇", "Customers' Favourite", favourite_name, favourite_caption, tone="favourite"
            ),
            unsafe_allow_html=True,
        )
    with columns[2]:
        st.markdown(
            ui.snapshot_card(
                "🚨",
                "Stock Alerts",
                attention,
                f"{counts[rules.STATUS_OUT]} out of stock · "
                f"{counts[rules.STATUS_RESTOCK]} need restocking",
                tone="alert",
            ),
            unsafe_allow_html=True,
        )
    with columns[3]:
        st.markdown(
            ui.snapshot_card(
                "🔮",
                "Upcoming Demand",
                rules.format_units(upcoming_units),
                "units customers are expected to buy over the next 7 days",
                tone="forecast",
            ),
            unsafe_allow_html=True,
        )


def render_momentum(context):
    momentum = context["momentum"]
    period_sales = context["period_sales"]

    headline = rules.sales_momentum_headline(momentum["change_pct"])
    detail = (
        f"Last {momentum['window']} days took "
        f"{rules.format_currency(momentum['recent_revenue'])} against "
        f"{rules.format_currency(momentum['previous_revenue'])} in the {momentum['window']} days "
        "before that."
    )
    st.markdown(
        ui.momentum_banner(
            headline,
            detail,
            rules.format_change(momentum["change_pct"]),
            momentum["change_pct"] >= 0,
        ),
        unsafe_allow_html=True,
    )

    daily = analytics.sales_by_grain(period_sales, "Daily")
    previous_average = 0.0
    if momentum["window"] > 0:
        previous_average = momentum["previous_revenue"] / momentum["window"]

    st.plotly_chart(
        charts.sales_momentum_chart(daily, previous_average),
        use_container_width=True,
        config=CHART_CONFIG,
    )
    st.markdown(
        ui.explain_note(
            "Each bar is one day of sales. The blue line smooths out the ups and downs so the "
            "overall direction is easy to see, and the dotted line shows what an average day "
            "looked like in the period before this one."
        ),
        unsafe_allow_html=True,
    )


def page_home(context):
    shop = context["shop"]
    settings = context["settings"]
    counts = context["counts"]
    overview = context["overview"]
    period_sales = context["period_sales"]

    st.markdown(
        ui.hero(
            "Sports Goods Shop",
            "Know what is selling. Know what is needed.",
            "Naeem Sports Goods Shop",
            [
                f"📅 {context['latest_day']:%A, %d %B %Y}",
                f"🛍️ {len(shop.products)} products on the shelf",
                f"🔎 Showing {settings['period_label']} · {settings['sport']}",
            ],
        ),
        unsafe_allow_html=True,
    )

    st.markdown(ui.section_head("📌", "Today's Shop Snapshot"), unsafe_allow_html=True)
    render_snapshot(context)

    if period_sales.empty:
        st.info(EMPTY_MESSAGE)
        return

    leaderboard = analytics.product_leaderboard(period_sales)
    performance = analytics.category_performance(context["shop_period_sales"])

    st.markdown(ui.section_head("📖", "Today's Story"), unsafe_allow_html=True)
    story = insights.build_todays_story(
        performance, context["momentum"], counts, overview, leaderboard, settings["sport"]
    )
    st.markdown(ui.story_panel(story), unsafe_allow_html=True)

    st.markdown(
        ui.section_head("📈", "Sales Momentum", "Are sales moving up or down?"),
        unsafe_allow_html=True,
    )
    render_momentum(context)

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(
            ui.section_head("🏆", "Customers' Favourites", "The best sellers this period"),
            unsafe_allow_html=True,
        )
        for _, product in leaderboard.head(5).iterrows():
            st.markdown(
                ui.rank_card(
                    int(product["rank"]),
                    product["product_name"],
                    product["category"],
                    product["units"],
                    f"units sold · {rules.format_currency(product['revenue'])}",
                ),
                unsafe_allow_html=True,
            )

    with right:
        st.markdown(
            ui.section_head("🚨", "Stock Alerts", "Products that need your attention"),
            unsafe_allow_html=True,
        )
        alerts = rules.products_needing_attention(overview).head(4)
        if alerts.empty:
            st.success("Every product has enough stock for the week ahead.")
        for _, product in alerts.iterrows():
            st.markdown(
                ui.alert_card(
                    product["product_name"],
                    product["category"],
                    product["status"],
                    product["current_stock"],
                    product["expected_demand"],
                    product["action"],
                ),
                unsafe_allow_html=True,
            )

    st.markdown(
        ui.section_head(
            "🔮", "What May Sell Next?", "Expected demand over the next seven days, by sport"
        ),
        unsafe_allow_html=True,
    )
    upcoming = (
        overview.groupby("category")["expected_demand"]
        .sum()
        .reset_index()
        .rename(columns={"expected_demand": "expected_units"})
    )
    st.plotly_chart(
        charts.upcoming_demand_chart(upcoming), use_container_width=True, config=CHART_CONFIG
    )

    st.markdown(ui.section_head("💡", "Smart Shop Insights"), unsafe_allow_html=True)
    smart = insights.build_smart_insights(
        performance,
        context["momentum"],
        leaderboard,
        analytics.rising_products(period_sales, context["latest_day"]),
        overview,
        counts,
        analytics.weekday_pattern(period_sales),
        analytics.seasonal_peak_by_category(context["shop"].sales),
        analytics.slow_movers(period_sales, context["latest_day"]),
        settings["sport"],
    )
    for row_start in range(0, len(smart), 3):
        columns = st.columns(3, gap="medium")
        for column, insight in zip(columns, smart[row_start : row_start + 3]):
            with column:
                st.markdown(
                    ui.insight_card(insight["icon"], insight["title"], insight["text"]),
                    unsafe_allow_html=True,
                )


def page_sales_story(context):
    period_sales = context["period_sales"]
    settings = context["settings"]

    st.markdown(
        ui.section_head(
            "📊", "Sales Story", f"How the shop performed across {settings['period_label'].lower()}"
        ),
        unsafe_allow_html=True,
    )

    if period_sales.empty:
        st.info(EMPTY_MESSAGE)
        return

    summary = analytics.totals(period_sales)
    columns = st.columns(4, gap="medium")
    figures = [
        ("Money Taken", rules.format_currency(summary["revenue"]), "across the selected period"),
        ("Units Sold", rules.format_units(summary["units"]), "individual items leaving the shop"),
        (
            "Average Day",
            rules.format_currency(summary["revenue"] / max(summary["active_days"], 1)),
            "typical sales on a trading day",
        ),
        (
            "Products Sold",
            rules.format_units(period_sales["product_id"].nunique()),
            "different items",
        ),
    ]
    for column, (label, value, caption) in zip(columns, figures):
        with column:
            st.markdown(ui.detail_metric(label, value, caption), unsafe_allow_html=True)

    st.markdown(ui.section_head("📈", "Sales Over Time"), unsafe_allow_html=True)
    grain = st.radio(
        "View sales by", analytics.GRAIN_CHOICES, horizontal=True, label_visibility="collapsed"
    )
    trend = analytics.sales_by_grain(period_sales, grain)
    st.plotly_chart(
        charts.sales_trend_chart(trend, grain), use_container_width=True, config=CHART_CONFIG
    )
    st.markdown(
        ui.explain_note(
            f"This shows the money taken by the shop, grouped {grain.lower()}. "
            "Rising ground means the shop is taking more; falling ground means it is taking less."
        ),
        unsafe_allow_html=True,
    )

    performance = analytics.category_performance(context["shop_period_sales"])
    leader = rules.category_leader(performance)

    st.markdown(
        ui.section_head(
            "🏅",
            "Sales By Sport",
            "Which sport matters most to the shop? Every sport is compared here.",
        ),
        unsafe_allow_html=True,
    )
    if leader:
        st.markdown(
            ui.momentum_banner(
                f"{leader['category']} is the strongest sport right now",
                f"{rules.format_currency(leader['revenue'])} taken from "
                f"{rules.format_units(leader['units'])} units sold.",
                f"{leader['share']:.0f}% of sales",
                True,
            ),
            unsafe_allow_html=True,
        )
    st.plotly_chart(
        charts.category_bar_chart(performance), use_container_width=True, config=CHART_CONFIG
    )

    for row_start in range(0, len(performance), 3):
        columns = st.columns(3, gap="medium")
        block = performance.iloc[row_start : row_start + 3]
        for column, (_, row) in zip(columns, block.iterrows()):
            with column:
                st.markdown(
                    ui.detail_metric(
                        row["category"],
                        rules.format_currency(row["revenue"]),
                        f"{rules.format_units(row['units'])} units · "
                        f"{row['share']:.1f}% of shop sales",
                    ),
                    unsafe_allow_html=True,
                )

    st.markdown(
        ui.section_head("📅", "When Do Customers Shop?", "Sales on each day of the week"),
        unsafe_allow_html=True,
    )
    pattern = analytics.weekday_pattern(period_sales)
    st.plotly_chart(charts.weekday_chart(pattern), use_container_width=True, config=CHART_CONFIG)
    weekday_line = insights.busiest_day_story(pattern)
    if weekday_line:
        st.markdown(ui.explain_note(weekday_line), unsafe_allow_html=True)

    st.markdown(
        ui.section_head(
            "🌦️",
            "Seasonal Demand",
            "Which sports become more popular at different times of the year?",
        ),
        unsafe_allow_html=True,
    )
    seasonality = analytics.monthly_seasonality(context["shop"].sales)
    st.plotly_chart(
        charts.seasonal_chart(seasonality), use_container_width=True, config=CHART_CONFIG
    )
    seasonal_line = insights.seasonal_story(
        analytics.seasonal_peak_by_category(context["shop"].sales)
    )
    if seasonal_line:
        st.markdown(
            ui.explain_note(
                f"{seasonal_line} This view uses the shop's full sales history so every month "
                "of the year can be compared fairly."
            ),
            unsafe_allow_html=True,
        )


def page_favourites(context):
    period_sales = context["period_sales"]
    latest_day = context["latest_day"]

    st.markdown(
        ui.section_head(
            "🏆", "Customers' Favourites", "The products customers are buying most right now"
        ),
        unsafe_allow_html=True,
    )

    if period_sales.empty:
        st.info(EMPTY_MESSAGE)
        return

    leaderboard = analytics.product_leaderboard(period_sales)
    podium = leaderboard.head(3)
    columns = st.columns(len(podium), gap="medium")
    for column, (_, product) in zip(columns, podium.iterrows()):
        with column:
            st.markdown(
                ui.podium_card(
                    int(product["rank"]),
                    product["product_name"],
                    product["category"],
                    product["units"],
                    product["revenue"],
                ),
                unsafe_allow_html=True,
            )

    st.markdown(ui.section_head("📋", "The Rest Of The Top Ten"), unsafe_allow_html=True)
    for _, product in leaderboard.iloc[3:10].iterrows():
        st.markdown(
            ui.rank_card(
                int(product["rank"]),
                product["product_name"],
                product["category"],
                product["units"],
                f"units sold · {rules.format_currency(product['revenue'])}",
            ),
            unsafe_allow_html=True,
        )

    st.markdown(
        ui.section_head(
            "🔥", "Products Gaining Attention", "Selling faster now than they were before"
        ),
        unsafe_allow_html=True,
    )
    rising = analytics.rising_products(context["sport_sales"], latest_day)
    if rising.empty:
        st.info("No product is showing a clear jump in sales at the moment.")
    else:
        st.plotly_chart(
            charts.momentum_comparison_chart(rising),
            use_container_width=True,
            config=CHART_CONFIG,
        )
        for _, product in rising.iterrows():
            st.markdown(
                ui.momentum_card(
                    product["product_name"],
                    product["category"],
                    product["previous"],
                    product["recent"],
                    rules.momentum_label(product["change_pct"]),
                    rules.format_change(product["change_pct"]),
                ),
                unsafe_allow_html=True,
            )

    st.markdown(
        ui.section_head("🐢", "Products Moving Slowly", "Quietest sellers over the last 90 days"),
        unsafe_allow_html=True,
    )
    movers = analytics.slow_movers(context["sport_sales"], latest_day)
    if movers.empty:
        st.info("Every product is selling steadily at the moment.")
    else:
        display = movers[["product_name", "category", "units", "revenue", "quiet_days"]].copy()
        display["revenue"] = display["revenue"].map(
            lambda value: rules.format_currency(value, compact=False)
        )
        display.columns = ["Product", "Sport", "Units Sold", "Money Taken", "Days Since Last Sale"]
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.markdown(
            ui.explain_note(
                "These products are selling more slowly and may need closer monitoring. "
                "A quiet product is not always a problem, but it is worth knowing which items "
                "are tying up space on the shelf."
            ),
            unsafe_allow_html=True,
        )


def page_stock_room(context):
    overview = context["overview"]
    counts = context["counts"]

    st.markdown(
        ui.section_head("📦", "Stock Room", "Which products have enough stock, and which do not?"),
        unsafe_allow_html=True,
    )

    columns = st.columns(4, gap="medium")
    for column, status in zip(columns, rules.STATUS_PRIORITY[::-1]):
        with column:
            st.markdown(ui.status_tile(status, counts[status]), unsafe_allow_html=True)

    st.plotly_chart(
        charts.stock_status_bar(counts), use_container_width=True, config=CHART_CONFIG
    )
    st.markdown(
        ui.explain_note(
            "Every product on the shelf sits in one of these four groups. The comparison is "
            "between what is in stock today and what customers are expected to buy over the "
            "next seven days."
        ),
        unsafe_allow_html=True,
    )

    st.markdown(ui.section_head("🔎", "Find A Product"), unsafe_allow_html=True)
    search_column, status_column = st.columns([3, 2], gap="medium")
    with search_column:
        query = st.text_input(
            "Search", placeholder="Type a product name, for example Cricket Bat"
        )
    with status_column:
        status_filter = st.selectbox("Show", ["All products"] + rules.STATUS_PRIORITY)

    table = overview.copy()
    if query.strip():
        table = table.loc[table["product_name"].str.contains(query.strip(), case=False, na=False)]
    if status_filter != "All products":
        table = table.loc[table["status"] == status_filter]

    if table.empty:
        st.info("No products match that search. Try a different name.")
    else:
        display = pd.DataFrame(
            {
                "Product": table["product_name"],
                "Sport": table["category"],
                "Stock": table["current_stock"],
                "Expected Demand": table["expected_demand"].round(0).astype(int),
                "Status": [
                    f"{rules.STATUS_BADGE[status]} {status}" for status in table["status"]
                ],
            }
        )
        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            height=min(430, 36 * len(display) + 44),
        )

    st.markdown(
        ui.section_head("🚨", "Stock Alerts", "Sorted by how urgent each product is"),
        unsafe_allow_html=True,
    )
    alerts = rules.products_needing_attention(overview)
    if alerts.empty:
        st.success("Nothing needs attention. Every product has enough stock for the week ahead.")
    for _, product in alerts.iterrows():
        st.markdown(
            ui.alert_card(
                product["product_name"],
                product["category"],
                product["status"],
                product["current_stock"],
                product["expected_demand"],
                product["action"],
            ),
            unsafe_allow_html=True,
        )


def page_forecast(context):
    shop = context["shop"]
    overview = context["overview"]
    forecast = context["forecast"]
    latest_day = context["latest_day"]

    st.markdown(
        ui.section_head(
            "🔮", "What May Sell Next?", "An estimate of what customers may buy over seven days"
        ),
        unsafe_allow_html=True,
    )

    if overview.empty:
        st.info("There are no products in this selection.")
        return

    names = overview.sort_values("product_name")["product_name"].tolist()
    default_name = overview.sort_values("expected_demand", ascending=False).iloc[0]["product_name"]
    chosen_name = st.selectbox(
        "Choose a product", names, index=names.index(default_name)
    )
    product = overview.loc[overview["product_name"] == chosen_name].iloc[0]

    momentum_table = analytics.product_momentum(context["sport_sales"], latest_day)
    momentum_row = momentum_table.loc[momentum_table["product_id"] == product["product_id"]]
    change_pct = float(momentum_row["change_pct"].iloc[0]) if not momentum_row.empty else 0.0
    recent_units = float(momentum_row["recent"].iloc[0]) if not momentum_row.empty else 0.0

    columns = st.columns(4, gap="medium")
    metrics = [
        ("Current Stock", rules.format_units(product["current_stock"]), "units on the shelf"),
        (
            "Recent Sales",
            rules.format_units(recent_units),
            "units sold in the last four weeks",
        ),
        (
            "Expected 7-Day Demand",
            rules.format_units(product["expected_demand"]),
            "units customers may ask for",
        ),
        (
            "Stock Situation",
            f"{rules.STATUS_BADGE[product['status']]} {product['status']}",
            rules.format_cover(product["cover_days"]),
        ),
    ]
    for column, (label, value, caption) in zip(columns, metrics):
        with column:
            st.markdown(ui.detail_metric(label, value, caption), unsafe_allow_html=True)

    st.markdown(
        ui.section_head("📊", "Last 30 Days And The Next 7 Days"), unsafe_allow_html=True
    )
    history = analytics.product_daily_history(
        shop.daily_sales, product["product_id"], 30, latest_day
    )
    product_forecast = forecasting.product_forecast(forecast, product["product_id"])
    st.plotly_chart(
        charts.history_and_forecast_chart(history, product_forecast),
        use_container_width=True,
        config=CHART_CONFIG,
    )

    st.markdown(ui.section_head("💬", "What Does This Mean?"), unsafe_allow_html=True)
    st.markdown(
        ui.explain_note(
            rules.describe_forecast(
                product["current_stock"], product["expected_demand"], change_pct
            )
        ),
        unsafe_allow_html=True,
    )

    with st.expander("See the full sales journey for this product"):
        journey = analytics.product_daily_history(
            shop.daily_sales, product["product_id"], 365, latest_day
        )
        st.plotly_chart(
            charts.product_history_chart(journey), use_container_width=True, config=CHART_CONFIG
        )
        st.markdown(
            ui.explain_note(
                rules.describe_product_recommendation(product["status"], change_pct)
            ),
            unsafe_allow_html=True,
        )

    st.markdown(
        ui.section_head("⚡", "Strongest Expected Demand", "The busiest sellers of the week ahead"),
        unsafe_allow_html=True,
    )
    busiest = overview.sort_values("expected_demand", ascending=False).head(5)
    for position, (_, row) in enumerate(busiest.iterrows(), start=1):
        st.markdown(
            ui.rank_card(
                position,
                row["product_name"],
                row["category"],
                row["expected_demand"],
                f"units expected · {rules.format_units(row['current_stock'])} in stock",
            ),
            unsafe_allow_html=True,
        )


def page_shopping_list(context):
    overview = context["overview"]

    st.markdown(
        ui.section_head(
            "🛒", "Shopping List", "Which products should you think about restocking?"
        ),
        unsafe_allow_html=True,
    )

    groups = rules.shopping_list(overview)
    high = groups[rules.PRIORITY_HIGH]
    watch = groups[rules.PRIORITY_WATCH]
    settled = groups[rules.PRIORITY_NONE]

    columns = st.columns(3, gap="medium")
    summary = [
        ("🔴 High Priority", len(high), "products to order soon"),
        ("🟡 Watch", len(watch), "products to keep an eye on"),
        ("🟢 No Action", len(settled), "products with comfortable stock"),
    ]
    for column, (label, value, caption) in zip(columns, summary):
        with column:
            st.markdown(ui.detail_metric(label, value, caption), unsafe_allow_html=True)

    st.markdown(ui.section_head("🔴", "High Priority"), unsafe_allow_html=True)
    if high.empty:
        st.success("Nothing needs an urgent order this week.")
    for _, product in high.iterrows():
        st.markdown(
            ui.buy_card(
                product["product_name"],
                product["category"],
                product["status"],
                product["current_stock"],
                product["expected_demand"],
                product["action"],
                rules.format_cover(product["cover_days"]),
            ),
            unsafe_allow_html=True,
        )

    st.markdown(ui.section_head("🟡", "Watch"), unsafe_allow_html=True)
    if watch.empty:
        st.info("No products are sitting close to the line at the moment.")
    for _, product in watch.iterrows():
        st.markdown(
            ui.buy_card(
                product["product_name"],
                product["category"],
                product["status"],
                product["current_stock"],
                product["expected_demand"],
                product["action"],
                rules.format_cover(product["cover_days"]),
            ),
            unsafe_allow_html=True,
        )

    with st.expander(f"🟢 No action needed ({len(settled)} products)"):
        for _, product in settled.iterrows():
            st.markdown(
                ui.buy_card(
                    product["product_name"],
                    product["category"],
                    product["status"],
                    product["current_stock"],
                    product["expected_demand"],
                    product["action"],
                    rules.format_cover(product["cover_days"]),
                ),
                unsafe_allow_html=True,
            )

    st.markdown(
        ui.explain_note(
            "This list compares what is on the shelf today with what customers are expected to "
            "buy over the next seven days. It highlights the products worth reviewing, and "
            "leaves the final order quantity to you, since supplier terms and delivery times "
            "are not part of this dashboard."
        ),
        unsafe_allow_html=True,
    )


PAGE_RENDERERS = {
    PAGE_HOME: page_home,
    PAGE_SALES: page_sales_story,
    PAGE_FAVOURITES: page_favourites,
    PAGE_STOCK: page_stock_room,
    PAGE_FORECAST: page_forecast,
    PAGE_SHOPPING: page_shopping_list,
}


def show_setup_message():
    st.markdown(ui.STYLES, unsafe_allow_html=True)
    st.markdown(
        ui.hero(
            "Sports Goods Shop",
            "We couldn't load the shop information. Please refresh the dashboard.",
            "Naeem Sports Goods Shop",
            ["The shop data is not ready yet"],
        ),
        unsafe_allow_html=True,
    )
    if st.button("🔄 Refresh Shop Data"):
        data_loader.refresh()
        st.rerun()


def main():
    st.set_page_config(
        page_title="Naeem Sports Goods Shop",
        page_icon="🏆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    try:
        shop = data_loader.load_shop_data()
    except Exception:
        show_setup_message()
        return

    st.markdown(ui.STYLES, unsafe_allow_html=True)
    settings = render_sidebar(shop)

    try:
        with st.spinner("Working out what may sell next..."):
            forecast = data_loader.load_expected_demand()
        context = build_context(shop, forecast, settings)
        PAGE_RENDERERS[settings["page"]](context)
    except Exception:
        st.warning("We couldn't prepare this view. Please refresh the dashboard and try again.")
        return

    st.markdown(
        ui.footer(
            f"Last updated {shop.loaded_at:%d %B %Y, %I:%M %p}",
            f"{settings['period_label']} · {settings['sport']}",
        ),
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

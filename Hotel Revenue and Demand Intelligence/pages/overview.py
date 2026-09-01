from __future__ import annotations

import streamlit as st

from src import analytics, business_insights, charts
from src.customer_analysis import customer_type_profile
from src.forecasting import demand_alert, overall_demand_level
from src.page_support import (
    current_context,
    forecast_for_current_filters,
    guard_empty,
    render_insights,
)
from src.ui import alert_banner, caption, kpi_card, page_header, recommendation_card, section
from src.utils import format_currency, format_money, format_number, format_percent


def render() -> None:
    context = current_context()
    page_header(
        "Hotel Overview",
        "How is the hotel performing?",
        f"Reporting period: {context.period_label}",
    )
    if not guard_empty(context):
        return

    kpis = context.kpis
    changes = context.changes

    section("Hotel Snapshot", "The six numbers that describe the period at a glance.")
    top = st.columns(3)
    with top[0]:
        kpi_card("Room revenue", format_currency(kpis["revenue"]), changes.get("revenue"))
    with top[1]:
        kpi_card("Rooms occupied", format_percent(kpis["occupancy_rate"]), changes.get("occupancy_rate"))
    with top[2]:
        kpi_card("Average room rate", format_money(kpis["adr"], 0), changes.get("adr"))

    bottom = st.columns(3)
    with bottom[0]:
        kpi_card("Earned per available room", format_money(kpis["revpar"], 0), changes.get("revpar"))
    with bottom[1]:
        kpi_card("Confirmed bookings", format_number(kpis["bookings"]), changes.get("bookings"))
    with bottom[2]:
        kpi_card("Cancelled bookings", format_percent(kpis["cancellation_rate"]),
                 changes.get("cancellation_rate"), lower_is_better=True)
    caption(
        "Earned per available room spreads room revenue across every room in the hotel, "
        "whether it was sold or not. Comparisons are against the period of equal length "
        "immediately before this one."
    )

    section("Today's Business Story", "What stands out in the period you are looking at.")
    render_insights(business_insights.business_story(context, limit=4), columns=2)

    section("Revenue and Demand", "Money earned each night, and how full the hotel was.")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(charts.revenue_trend(context.daily), use_container_width=True)
    with right:
        st.plotly_chart(charts.demand_trend(context.daily), use_container_width=True)

    section("Where the Money Comes From", "The room categories and guests behind the revenue.")
    left, right = st.columns([1.15, 1])
    with left:
        by_room = analytics.revenue_by_dimension(context.room_nights, "room_type")
        st.plotly_chart(
            charts.horizontal_bar(by_room, "room_type", "revenue", height=310),
            use_container_width=True,
        )
        caption("Room revenue by category over the selected period.")
    with right:
        profile = customer_type_profile(context.bookings, context.room_nights)
        if not profile.empty:
            st.plotly_chart(
                charts.category_donut(profile["customer_type"], profile["revenue"], height=310),
                use_container_width=True,
            )
            caption("Share of room revenue by guest type.")

    forecast_result = forecast_for_current_filters()
    section("What May Happen Next", "The expected picture for the next two weeks.")
    if forecast_result.get("available"):
        alert = demand_alert(forecast_result)
        alert_banner(alert["tone"], alert["title"], alert["text"])
        comparison = forecast_result["comparison"]
        forecast = forecast_result["forecast"]
        cards = st.columns(4)
        with cards[0]:
            kpi_card("Expected demand", overall_demand_level(forecast_result),
                     note=f"Against a typical "
                          f"{format_percent(comparison.get('typical_occupancy'))} for this hotel")
        with cards[1]:
            kpi_card("Expected occupancy", format_percent(comparison["expected_occupancy"]),
                     note=f"{format_percent(comparison['recent_occupancy'])} in the period just finished")
        with cards[2]:
            kpi_card("Expected room revenue", format_currency(comparison["expected_revenue"]),
                     comparison["revenue_change"])
        with cards[3]:
            busiest = forecast.loc[forecast["occupancy_rate"].idxmax()]
            kpi_card("Busiest night ahead", f"{busiest['weekday']} {busiest['stay_date']:%d %b}",
                     note=f"Expected {format_percent(busiest['occupancy_rate'])} occupancy")
        st.plotly_chart(
            charts.forecast_view(forecast_result["history"], forecast, forecast_result["capacity"],
                                 height=360),
            use_container_width=True,
        )
    else:
        caption("An outlook is not available for the current selection.")

    section("What Deserves Management Attention", "The three points worth acting on first.")
    performance = analytics.room_performance(
        context.bookings, context.room_nights, context.rooms, context.days
    )
    recommendations = business_insights.management_recommendations(
        context, performance, forecast_result
    )
    if recommendations:
        for item in recommendations[:3]:
            recommendation_card(item["category"], item["title"], item["body"],
                                item["action"], item["tone"])
    else:
        caption("No issues stand out for this period.")

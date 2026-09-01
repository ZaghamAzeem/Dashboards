from __future__ import annotations

import streamlit as st

from src import analytics, business_insights, charts
from src.page_support import current_context, guard_empty, render_insights
from src.ui import caption, kpi_card, page_header, section
from src.utils import format_currency, format_money, format_number, format_percent


def render() -> None:
    context = current_context()
    page_header(
        "Revenue Story",
        "How much money is the hotel making, and where does it come from?",
        f"Reporting period: {context.period_label}",
    )
    if not guard_empty(context):
        return

    kpis = context.kpis
    changes = context.changes

    section("Revenue Headlines")
    cards = st.columns(4)
    with cards[0]:
        kpi_card("Room revenue", format_currency(kpis["revenue"]), changes.get("revenue"))
    with cards[1]:
        kpi_card("Average room rate", format_money(kpis["adr"], 0), changes.get("adr"))
    with cards[2]:
        kpi_card("Earned per available room", format_money(kpis["revpar"], 0), changes.get("revpar"))
    with cards[3]:
        kpi_card("Average booking value", format_money(kpis["average_booking_value"], 0),
                 changes.get("average_booking_value"))

    section("Revenue Over Time", "Nightly room revenue and the underlying trend.")
    st.plotly_chart(charts.revenue_trend(context.daily, height=340), use_container_width=True)

    if not context.monthly.empty and len(context.monthly) > 1:
        section("Month by Month", "Revenue earned each month against how full the hotel was.")
        st.plotly_chart(charts.monthly_revenue(context.monthly), use_container_width=True)

    section("What Is Driving Revenue", "The same revenue split three ways.")
    columns = st.columns(3)
    breakdowns = (
        ("room_type", "By room category", columns[0]),
        ("booking_channel", "By booking source", columns[1]),
        ("customer_type", "By guest type", columns[2]),
    )
    for dimension, label, column in breakdowns:
        breakdown = analytics.revenue_by_dimension(context.room_nights, dimension)
        with column:
            st.markdown(f"**{label}**")
            if breakdown.empty:
                caption("Nothing to show for this selection.")
                continue
            st.plotly_chart(
                charts.horizontal_bar(breakdown, dimension, "revenue", height=290),
                use_container_width=True,
            )
            leader = breakdown.iloc[0]
            caption(
                f"{leader[dimension]} leads with {leader['revenue_share']:.0f}% of room revenue "
                f"at {format_money(leader['adr'], 0)} a night."
            )

    section("Rate Achieved by Category", "What each room category actually earns per night.")
    rate_table = analytics.revenue_by_dimension(context.room_nights, "room_type")
    if not rate_table.empty:
        display = rate_table.rename(columns={
            "room_type": "Room category",
            "revenue": "Room revenue",
            "room_nights": "Nights sold",
            "adr": "Average nightly rate",
            "revenue_share": "Share of revenue",
        })
        st.dataframe(
            display[["Room category", "Room revenue", "Nights sold",
                     "Average nightly rate", "Share of revenue"]],
            hide_index=True,
            use_container_width=True,
            column_config={
                "Room revenue": st.column_config.NumberColumn(format="$%d"),
                "Nights sold": st.column_config.NumberColumn(format="%d"),
                "Average nightly rate": st.column_config.NumberColumn(format="$%.0f"),
                "Share of revenue": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )

    section("Revenue Insights", "Read automatically from the figures above.")
    render_insights(business_insights.revenue_insights(context), columns=2)

    pressure = analytics.occupancy_pressure(context.daily)
    if pressure.get("peak_days"):
        section("Periods of Unusually Strong Demand")
        strong = context.daily.nlargest(5, "revenue")[
            ["stay_date", "rooms_sold", "occupancy_rate", "adr", "revenue"]
        ].copy()
        strong["stay_date"] = strong["stay_date"].dt.strftime("%A %d %B %Y")
        strong = strong.rename(columns={
            "stay_date": "Night",
            "rooms_sold": "Rooms sold",
            "occupancy_rate": "Occupancy",
            "adr": "Average rate",
            "revenue": "Room revenue",
        })
        st.dataframe(
            strong, hide_index=True, use_container_width=True,
            column_config={
                "Rooms sold": st.column_config.NumberColumn(format="%d"),
                "Occupancy": st.column_config.NumberColumn(format="%.1f%%"),
                "Average rate": st.column_config.NumberColumn(format="$%.0f"),
                "Room revenue": st.column_config.NumberColumn(format="$%d"),
            },
        )
        caption(
            f"{format_number(pressure['peak_days'])} nights in this period ran at 90% occupancy "
            f"or higher, averaging {format_percent(pressure['average'])} across the period overall."
        )

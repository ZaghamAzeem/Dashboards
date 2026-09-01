from __future__ import annotations

import streamlit as st

from src import analytics, business_insights, charts
from src.page_support import current_context, guard_empty, render_insights
from src.ui import caption, kpi_card, page_header, section
from src.utils import format_number, format_percent


def render() -> None:
    context = current_context()
    page_header(
        "Booking Trends",
        "What are guests booking, and when do they book it?",
        f"Reporting period: {context.period_label}",
    )
    if not guard_empty(context):
        return

    kpis = context.kpis
    changes = context.changes

    section("Booking Headlines")
    cards = st.columns(4)
    with cards[0]:
        kpi_card("Confirmed bookings", format_number(kpis["bookings"]), changes.get("bookings"))
    with cards[1]:
        kpi_card("Nights sold", format_number(kpis["rooms_sold"]))
    with cards[2]:
        kpi_card("Average stay", f"{kpis['average_length_of_stay']:.1f} nights",
                 changes.get("average_length_of_stay"))
    with cards[3]:
        kpi_card("Booked in advance", f"{kpis['average_lead_time']:.0f} days",
                 note="Average time between booking and arrival")

    section("Bookings Over Time", "Arrivals for each night, with cancellations shown alongside.")
    default_view = 0 if context.days <= 120 else 1
    view = st.radio(
        "Grouping", ["Daily", "Weekly", "Monthly"], index=default_view, horizontal=True,
        label_visibility="collapsed", key="booking_grouping",
    )
    frequency = {"Daily": "D", "Weekly": "W", "Monthly": "M"}[view]
    volume = analytics.booking_volume(context.bookings, frequency)
    if not volume.empty:
        date_format = "%b %Y" if frequency == "M" else "%d %b %Y"
        st.plotly_chart(
            charts.booking_volume(volume, date_format=date_format), use_container_width=True
        )
        caption("Bookings are counted against the night guests arrive.")

    section("What Guests Are Booking")
    columns = st.columns(3)
    for dimension, label, column in (
        ("room_type", "Room category", columns[0]),
        ("booking_channel", "Booking source", columns[1]),
        ("customer_type", "Guest type", columns[2]),
    ):
        breakdown = analytics.bookings_by_dimension(context.bookings, dimension)
        with column:
            st.markdown(f"**{label}**")
            if breakdown.empty:
                caption("Nothing to show for this selection.")
                continue
            st.plotly_chart(
                charts.horizontal_bar(breakdown, dimension, "bookings", value_prefix="",
                                      height=290, colour="#42566B"),
                use_container_width=True,
            )
            leader = breakdown.iloc[0]
            caption(
                f"{leader[dimension]} accounts for {format_number(leader['bookings'])} bookings "
                f"with an average stay of {leader['average_length_of_stay']:.1f} nights."
            )

    section("When Do Guests Book?", "How far ahead reservations are made, and on which days.")
    left, right = st.columns(2)
    with left:
        st.markdown("**How far ahead rooms are reserved**")
        lead = analytics.booking_lead_time_profile(context.bookings)
        if not lead.empty:
            st.plotly_chart(charts.lead_time_profile(lead), use_container_width=True)
            busiest = lead.loc[lead["bookings"].idxmax()]
            caption(
                f"{busiest['share']:.0f}% of confirmed bookings are made "
                f"{str(busiest['lead_time_group']).lower()}."
            )
    with right:
        st.markdown("**The days reservations are made**")
        weekday_bookings = analytics.booking_weekday_profile(context.bookings)
        if not weekday_bookings.empty:
            frame = weekday_bookings.rename(columns={"booking_weekday": "weekday"})
            st.plotly_chart(
                charts.weekday_pattern(frame, value="bookings", prefix="", height=300),
                use_container_width=True,
            )
            top = weekday_bookings.loc[weekday_bookings["bookings"].idxmax()]
            caption(f"{top['booking_weekday']} is the busiest day for taking reservations.")

    section("Best Days and Seasons", "Where demand sits across the week and across the year.")
    left, right = st.columns([1, 1])
    with left:
        st.markdown("**Occupancy by day of the week**")
        st.plotly_chart(
            charts.weekday_pattern(context.weekday, value="occupancy_rate", prefix="",
                                   suffix="%", height=300),
            use_container_width=True,
        )
        if not context.weekday.empty:
            best = context.weekday.dropna(subset=["occupancy_rate"])
            if not best.empty:
                peak = best.loc[best["occupancy_rate"].idxmax()]
                quiet = best.loc[best["occupancy_rate"].idxmin()]
                caption(
                    f"{peak['weekday']} is the fullest night at "
                    f"{format_percent(peak['occupancy_rate'])}, {quiet['weekday']} the quietest at "
                    f"{format_percent(quiet['occupancy_rate'])}."
                )
    with right:
        st.markdown("**Demand by season**")
        if not context.seasonal.empty:
            st.plotly_chart(
                charts.horizontal_bar(context.seasonal, "season", "occupancy_rate",
                                      value_prefix="", value_suffix="%", height=300,
                                      colour="#B08A47"),
                use_container_width=True,
            )
            top = context.seasonal.loc[context.seasonal["occupancy_rate"].idxmax()]
            caption(f"{top['season']} is the strongest season for room demand.")

    if len(context.daily) >= 60:
        section("Demand Across the Year", "Average occupancy for every combination of month and weekday.")
        st.plotly_chart(charts.seasonal_pattern(context.daily), use_container_width=True)
        caption("Darker squares mark the nights the hotel fills most reliably.")

    section("Booking Insights", "Read automatically from the booking record.")
    render_insights(business_insights.booking_insights(context), columns=2)

from __future__ import annotations

import streamlit as st

from src import analytics, business_insights, charts
from src.page_support import current_context, guard_empty, render_insights
from src.ui import caption, kpi_card, page_header, section
from src.utils import PALETTE, format_currency, format_number, format_percent

BREAKDOWNS = (
    ("booking_channel", "By booking source", "Where the reservation came from"),
    ("customer_type", "By guest type", "The kind of guest who booked"),
    ("room_type", "By room category", "The room that was reserved"),
    ("lead_time_group", "By how far ahead it was booked", "Time between booking and arrival"),
    ("season", "By season", "The time of year of the stay"),
)


def render() -> None:
    context = current_context()
    page_header(
        "Cancellations",
        "Why are bookings being cancelled, and what does it cost?",
        f"Reporting period: {context.period_label}",
    )
    if not guard_empty(context):
        return

    summary = analytics.cancellation_summary(context.bookings)

    section("The Cost of Cancellations")
    cards = st.columns(4)
    with cards[0]:
        kpi_card("Cancellation rate", format_percent(summary["cancellation_rate"]),
                 context.changes.get("cancellation_rate"), lower_is_better=True)
    with cards[1]:
        kpi_card("Cancelled bookings", format_number(summary["cancelled_bookings"]))
    with cards[2]:
        kpi_card("Room value returned to sale", format_currency(summary["lost_value"]))
    with cards[3]:
        kpi_card("Nights released", format_number(summary["lost_room_nights"]))
    caption(
        "Cancelled rooms are released back for sale, so this is the value the hotel had to earn "
        "again rather than money lost outright."
    )

    section("Where Cancellations Come From", "The same bookings viewed five ways.")
    for dimension, title, subtitle in BREAKDOWNS:
        breakdown = analytics.cancellation_breakdown(context.bookings, dimension)
        if len(breakdown) < 2:
            continue
        st.markdown(f"**{title}** &nbsp;<span style='color:{PALETTE['muted']};font-size:0.85rem;'>"
                    f"{subtitle}</span>", unsafe_allow_html=True)
        left, right = st.columns([1.35, 1])
        with left:
            st.plotly_chart(
                charts.cancellation_bars(breakdown, dimension, height=250),
                use_container_width=True,
            )
        with right:
            worst = breakdown.iloc[0]
            best = breakdown.iloc[-1]
            st.markdown(
                f"""
                <div class="gh-card" style="margin-top:6px;">
                    <div style="color:{PALETTE['body']};font-size:0.93rem;line-height:1.65;">
                        <strong>{worst[dimension]}</strong> cancels
                        {format_percent(worst['cancellation_rate'])} of
                        {format_number(worst['total'])} reservations, returning
                        {format_currency(worst['lost_value'])} of room value to sale.<br/><br/>
                        <strong>{best[dimension]}</strong> is the most dependable at
                        {format_percent(best['cancellation_rate'])}.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    promotion = context.bookings.groupby("promotion_used").agg(
        total=("booking_id", "count"),
        cancellations=("is_cancelled", "sum"),
        average_rate=("nightly_rate", "mean"),
    )
    if len(promotion) == 2:
        section("Promotional Bookings", "Whether discounted bookings behave differently.")
        promotion["cancellation_rate"] = promotion["cancellations"] / promotion["total"] * 100
        labels = {0: "Standard rate", 1: "Promotional rate"}
        columns = st.columns(2)
        for column, (key, row) in zip(columns, promotion.iterrows()):
            with column:
                kpi_card(labels.get(key, str(key)), format_percent(row["cancellation_rate"]),
                         note=f"{format_number(row['total'])} reservations at an average of "
                              f"${row['average_rate']:,.0f} a night")

    section("Cancellation Insights", "Read automatically from the booking record.")
    render_insights(business_insights.cancellation_insights(context), columns=2)

    section("Most Exposed Combinations", "Where high cancellation rates meet real volume.")
    frame = context.bookings.groupby(["booking_channel", "customer_type"]).agg(
        reservations=("booking_id", "count"),
        cancellations=("is_cancelled", "sum"),
        value_at_risk=("booking_value", "sum"),
    ).reset_index()
    frame = frame.loc[frame["reservations"] >= max(len(context.bookings) * 0.01, 25)]
    if not frame.empty:
        frame["cancellation_rate"] = frame["cancellations"] / frame["reservations"] * 100
        frame = frame.sort_values("cancellation_rate", ascending=False).head(8)
        display = frame.rename(columns={
            "booking_channel": "Booking source",
            "customer_type": "Guest type",
            "reservations": "Reservations",
            "cancellations": "Cancelled",
            "cancellation_rate": "Cancellation rate",
            "value_at_risk": "Room value booked",
        })
        st.dataframe(
            display[["Booking source", "Guest type", "Reservations", "Cancelled",
                     "Cancellation rate", "Room value booked"]],
            hide_index=True, use_container_width=True,
            column_config={
                "Reservations": st.column_config.NumberColumn(format="%d"),
                "Cancelled": st.column_config.NumberColumn(format="%d"),
                "Cancellation rate": st.column_config.NumberColumn(format="%.1f%%"),
                "Room value booked": st.column_config.NumberColumn(format="$%d"),
            },
        )
        caption("Only combinations with meaningful booking volume are shown.")

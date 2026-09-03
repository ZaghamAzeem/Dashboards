from __future__ import annotations

import pandas as pd
import streamlit as st

from src import analytics, business_insights
from src.customer_analysis import customer_type_profile, segment_guests, segment_summary
from src.page_support import current_context, forecast_for_current_filters, go_to, guard_empty
from src.ui import caption, page_header, question_card, section
from src.utils import format_currency, format_money, format_percent


def _performance_answer(context) -> str:
    change = context.changes.get("revenue")
    direction = ""
    if change is not None:
        direction = (
            f", {abs(change):.1f}% {'ahead of' if change > 0 else 'behind'} the previous period"
        )
    return (
        f"The hotel earned {format_currency(context.kpis['revenue'])} in room revenue"
        f"{direction}, with rooms {format_percent(context.kpis['occupancy_rate'])} full on average "
        f"at {format_money(context.kpis['adr'], 0)} a night."
    )


def _popular_rooms_answer(context, performance) -> str:
    if performance.empty:
        return "There is no room activity in this selection."
    busiest = performance.loc[performance["occupancy_rate"].idxmax()]
    most_booked = performance.loc[performance["confirmed_bookings"].idxmax()]
    if busiest["room_type"] == most_booked["room_type"]:
        return (
            f"{most_booked['room_type']} leads on both counts: "
            f"{most_booked['confirmed_bookings']:,} reservations, and the most reliable occupancy "
            f"in the hotel at {format_percent(busiest['occupancy_rate'])}."
        )
    return (
        f"{most_booked['room_type']} is booked most often with "
        f"{most_booked['confirmed_bookings']:,} reservations, while {busiest['room_type']} fills "
        f"the most reliably at {format_percent(busiest['occupancy_rate'])} occupancy."
    )


def _profitable_rooms_answer(context, performance) -> str:
    if performance.empty:
        return "There is no room activity in this selection."
    top_revenue = performance.loc[performance["revenue"].idxmax()]
    top_yield = performance.loc[performance["revpar"].idxmax()]
    if top_revenue["room_type"] == top_yield["room_type"]:
        return (
            f"{top_revenue['room_type']} both brings in the most money overall, at "
            f"{format_currency(top_revenue['revenue'])}, and earns the most from each room it has, "
            f"at {format_money(top_yield['revpar'], 0)} per available room a night."
        )
    return (
        f"{top_revenue['room_type']} brings in the most money overall at "
        f"{format_currency(top_revenue['revenue'])}, while {top_yield['room_type']} earns the most "
        f"from each room it has, at {format_money(top_yield['revpar'], 0)} per available room a night."
    )


def _valuable_guests_answer(context) -> str:
    profile = customer_type_profile(context.bookings, context.room_nights)
    guest_ids = set(context.bookings["guest_id"].unique())
    summary = segment_summary(
        segment_guests(context.guests.loc[context.guests["guest_id"].isin(guest_ids)])
    )
    if profile.empty:
        return "There are no completed stays in this selection."
    top = profile.iloc[0]
    answer = (
        f"{top['customer_type']} guests contribute the most revenue at "
        f"{format_currency(top['revenue'])}, {top['revenue_share']:.0f}% of the total."
    )
    high_value = summary.loc[summary["segment"].astype(str) == "High Value"] if not summary.empty else summary
    if not high_value.empty:
        row = high_value.iloc[0]
        answer += (
            f" A high value group of {row['guests']:,.0f} guests, {row['guest_share']:.0f}% of all "
            f"guests, produces {row['revenue_share']:.0f}% of guest spending."
        )
    return answer


def _cancellation_answer(context) -> str:
    breakdown = analytics.cancellation_breakdown(context.bookings, "booking_channel")
    summary = analytics.cancellation_summary(context.bookings)
    if breakdown.empty:
        return f"{format_percent(summary['cancellation_rate'])} of reservations were cancelled."
    worst = breakdown.iloc[0]
    best = breakdown.iloc[-1]
    return (
        f"{format_percent(summary['cancellation_rate'])} of reservations were cancelled. "
        f"{worst['booking_channel']} bookings are the least dependable at "
        f"{format_percent(worst['cancellation_rate'])}, against "
        f"{format_percent(best['cancellation_rate'])} for {best['booking_channel']}."
    )


def _demand_answer(context) -> str:
    parts = []
    if not context.seasonal.empty:
        best = context.seasonal.loc[context.seasonal["occupancy_rate"].idxmax()]
        parts.append(f"{best['season']} is the strongest season at "
                     f"{format_percent(best['occupancy_rate'])} occupancy")
    weekday = context.weekday.dropna(subset=["occupancy_rate"]) if not context.weekday.empty else context.weekday
    if not weekday.empty:
        peak = weekday.loc[weekday["occupancy_rate"].idxmax()]
        parts.append(f"{peak['weekday']} is the fullest night of the week at "
                     f"{format_percent(peak['occupancy_rate'])}")
    if not context.monthly.empty:
        complete = context.monthly.loc[context.monthly["days"] >= 28]
        if not complete.empty:
            month = complete.loc[complete["revenue"].idxmax()]
            parts.append(f"{month['month_label']} was the single strongest month")
    return ". ".join(parts) + "." if parts else "There is not enough activity to judge demand."


def _forecast_answer(result) -> str:
    if not result.get("available"):
        return "An outlook cannot be prepared from the records currently available."
    comparison = result["comparison"]
    forecast = result["forecast"]
    peak = forecast.loc[forecast["occupancy_rate"].idxmax()]
    return (
        f"Over the next {len(forecast)} nights the hotel is expected to run at "
        f"{format_percent(comparison['expected_occupancy'])} occupancy and earn "
        f"{format_currency(comparison['expected_revenue'])}, with the busiest night on "
        f"{peak['weekday']} {pd.Timestamp(peak['stay_date']):%d %B}."
    )


def _focus_answer(recommendations) -> str:
    if not recommendations:
        return "Nothing in this period stands out as needing attention."
    top = recommendations[0]
    counts = business_insights.priority_counts(recommendations)
    return (
        f"{top['title']}. There are {counts.get('priority', 0)} high priority points and "
        f"{counts.get('watch', 0)} to keep watching."
    )


def render() -> None:
    context = current_context()
    page_header(
        "Business Questions",
        "Ask a question, and go straight to the answer.",
        f"Answers cover {context.period_label}",
    )
    if not guard_empty(context):
        return

    performance = analytics.room_performance(
        context.bookings, context.room_nights, context.rooms, context.days
    )
    forecast_result = forecast_for_current_filters()
    recommendations = business_insights.management_recommendations(
        context, performance, forecast_result
    )

    entries = [
        ("How is the hotel performing?", _performance_answer(context),
         "Hotel Overview", "overview"),
        ("Which rooms are most popular?", _popular_rooms_answer(context, performance),
         "Room Performance", "rooms"),
        ("Which rooms make the most money?", _profitable_rooms_answer(context, performance),
         "Room Performance", "rooms"),
        ("Who are our most valuable guests?", _valuable_guests_answer(context),
         "Guest Intelligence", "guests"),
        ("Why are bookings being cancelled?", _cancellation_answer(context),
         "Cancellations", "cancellations"),
        ("When is demand strongest?", _demand_answer(context),
         "Booking Trends", "bookings"),
        ("What might happen next?", _forecast_answer(forecast_result),
         "Demand Forecast", "forecast"),
        ("What should management focus on?", _focus_answer(recommendations),
         "Recommendations", "recommendations"),
    ]

    section("Common Questions", "Each answer is worked out from the period selected on the left.")
    for start in range(0, len(entries), 2):
        for column, entry in zip(st.columns(2), entries[start:start + 2]):
            question, answer, destination, page_key = entry
            with column:
                question_card(question, answer, destination)
                if st.button(f"Open {destination}", key=f"question_{start}_{page_key}_{question[:12]}"):
                    go_to(page_key)
                st.write("")

    section("How Money Is Made Here")
    left, right = st.columns(2)
    with left:
        revenue_split = analytics.revenue_by_dimension(context.room_nights, "booking_channel")
        if not revenue_split.empty:
            leader = revenue_split.iloc[0]
            question_card(
                "Which booking source earns the most?",
                f"{leader['booking_channel']} delivers {format_currency(leader['revenue'])}, "
                f"{leader['revenue_share']:.0f}% of room revenue, at "
                f"{format_money(leader['adr'], 0)} a night.",
                "Revenue Story",
            )
            if st.button("Open Revenue Story", key="question_channel_revenue"):
                go_to("revenue")
    with right:
        lead = analytics.booking_lead_time_profile(context.bookings)
        if not lead.empty:
            top = lead.loc[lead["bookings"].idxmax()]
            question_card(
                "How far ahead do guests book?",
                f"{top['share']:.0f}% of confirmed bookings are made "
                f"{str(top['lead_time_group']).lower()}, and the average booking arrives "
                f"{context.kpis['average_lead_time']:.0f} days after it is made.",
                "Booking Trends",
            )
            if st.button("Open Booking Trends", key="question_lead_time"):
                go_to("bookings")

    caption(
        "Every answer on this page is calculated from the hotel's own records. Change the "
        "reporting period on the left and the answers change with it."
    )

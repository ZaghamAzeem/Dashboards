from __future__ import annotations

import streamlit as st

from src import analytics, business_insights
from src.page_support import current_context, forecast_for_current_filters, guard_empty
from src.ui import caption, kpi_card, page_header, recommendation_card, section
from src.utils import PALETTE

PRIORITY_LABELS = {
    "priority": ("High Priority", "Needs management attention now"),
    "watch": ("Watch", "Worth monitoring over the coming weeks"),
    "healthy": ("Healthy", "An opportunity rather than a problem"),
}


def render() -> None:
    context = current_context()
    page_header(
        "Management Recommendations",
        "What deserves your attention?",
        f"Based on hotel activity from {context.period_label}",
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

    if not recommendations:
        caption("Nothing in this period stands out as needing attention.")
        return

    counts = business_insights.priority_counts(recommendations)
    section("Attention Summary", "How the points below are weighted.")
    cards = st.columns(3)
    for column, key in zip(cards, ("priority", "watch", "healthy")):
        label, description = PRIORITY_LABELS[key]
        with column:
            kpi_card(label, str(counts.get(key, 0)), note=description)

    section("Points for Management", "Each point is drawn from the figures in this dashboard.")
    for item in recommendations:
        recommendation_card(item["category"], item["title"], item["body"],
                            item["action"], item["tone"])

    section("How to Read This Page")
    st.markdown(
        f"""
        <div class="gh-card">
            <div style="color:{PALETTE['body']};font-size:0.94rem;line-height:1.7;">
                Every point on this page is produced from the hotel's own records for the period
                selected in the panel on the left. Change the period or the focus filters and the
                recommendations are worked out again from the figures that apply.
                <br/><br/>
                <strong style="color:{PALETTE['attention']};">High Priority</strong> marks something
                costing money or capacity now.
                <strong style="color:{PALETTE['warning']};">Watch</strong> marks a pattern that is
                not urgent but is moving in the wrong direction.
                <strong style="color:{PALETTE['positive']};">Healthy</strong> marks strength worth
                building on.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

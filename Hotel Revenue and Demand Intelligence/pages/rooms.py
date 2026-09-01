from __future__ import annotations

import streamlit as st

from src import analytics, business_insights, charts
from src.page_support import current_context, guard_empty, render_insights
from src.ui import caption, page_header, section, status_badge
from src.utils import PALETTE, format_currency, format_money, format_percent

STATUS_ICONS = {
    "Strong Performer": "⭐",
    "Performing Well": "\U0001F44D",
    "Needs Attention": "\U0001F440",
}


def _performance_card(row) -> None:
    icon = STATUS_ICONS.get(row["status"], "")
    st.markdown(
        f"""
        <div class="gh-card" style="margin-bottom:14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;
                        flex-wrap:wrap;gap:10px;">
                <div>
                    <div style="font-size:1.18rem;font-weight:600;color:{PALETTE['ink']};">
                        {icon} {row['room_type']}</div>
                    <div style="font-size:0.84rem;color:{PALETTE['muted']};margin-top:3px;">
                        {int(row['rooms_available'])} rooms &middot; sleeps up to
                        {int(row['max_occupancy'])} &middot; published rate
                        {format_money(row['base_rate'], 0)}</div>
                </div>
                <div>{status_badge(row['status_tone'], row['status'])}</div>
            </div>
            <div style="display:flex;gap:26px;flex-wrap:wrap;margin-top:16px;padding-top:14px;
                        border-top:1px solid {PALETTE['border']};">
                {_metric_block('Occupancy', format_percent(row['occupancy_rate']))}
                {_metric_block('Average rate', format_money(row['adr'], 0))}
                {_metric_block('Earned per room', format_money(row['revpar'], 0))}
                {_metric_block('Room revenue', format_currency(row['revenue']))}
                {_metric_block('Average stay', f"{row['average_length_of_stay']:.1f} nights")}
                {_metric_block('Cancelled', format_percent(row['cancellation_rate']))}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _metric_block(label: str, value: str) -> str:
    return (
        f'<div><div style="font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;'
        f'color:{PALETTE["muted"]};font-weight:600;">{label}</div>'
        f'<div style="font-size:1.12rem;font-weight:600;color:{PALETTE["ink"]};margin-top:4px;">'
        f"{value}</div></div>"
    )


def render() -> None:
    context = current_context()
    page_header(
        "Room Performance",
        "Which rooms fill the hotel, and which ones earn the most?",
        f"Reporting period: {context.period_label}",
    )
    if not guard_empty(context):
        return

    performance = analytics.room_performance(
        context.bookings, context.room_nights, context.rooms, context.days
    )
    if performance.empty:
        caption("There is no room activity in this selection.")
        return

    section("Category Ranking", "Ordered by how well each category fills rooms and earns from them.")
    for _, row in performance.iterrows():
        _performance_card(row)
    caption(
        "Ranking weighs how much each category earns per available room, how reliably it fills, "
        "how close it gets to its published rate, and how often its bookings are cancelled."
    )

    section("How the Categories Compare")
    left, right = st.columns(2)
    with left:
        st.markdown("**Rooms occupied**")
        st.plotly_chart(
            charts.horizontal_bar(performance, "room_type", "occupancy_rate", value_prefix="",
                                  value_suffix="%", height=300, colour=PALETTE["ink"]),
            use_container_width=True,
        )
    with right:
        st.markdown("**Earned per available room each night**")
        st.plotly_chart(
            charts.horizontal_bar(performance, "room_type", "revpar", height=300,
                                  colour=PALETTE["brass"]),
            use_container_width=True,
        )
    caption(
        "A category can fill well and still earn less per room than a quieter, higher-priced "
        "category. Both views matter when deciding where to push demand."
    )

    section("Category Detail")
    display = performance[[
        "room_type", "rooms_available", "confirmed_bookings", "occupancy_rate",
        "adr", "revpar", "revenue", "revenue_share", "status",
    ]].rename(columns={
        "room_type": "Room category",
        "rooms_available": "Rooms",
        "confirmed_bookings": "Bookings",
        "occupancy_rate": "Occupancy",
        "adr": "Average rate",
        "revpar": "Earned per room",
        "revenue": "Room revenue",
        "revenue_share": "Share of revenue",
        "status": "Standing",
    })
    st.dataframe(
        display, hide_index=True, use_container_width=True,
        column_config={
            "Rooms": st.column_config.NumberColumn(format="%d"),
            "Bookings": st.column_config.NumberColumn(format="%d"),
            "Occupancy": st.column_config.NumberColumn(format="%.1f%%"),
            "Average rate": st.column_config.NumberColumn(format="$%.0f"),
            "Earned per room": st.column_config.NumberColumn(format="$%.0f"),
            "Room revenue": st.column_config.NumberColumn(format="$%d"),
            "Share of revenue": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

    section("Room Demand by Season", "Which categories carry each part of the year.")
    if not context.room_nights.empty:
        seasonal = context.room_nights.copy()
        seasonal["season"] = seasonal["stay_date"].dt.month.map(
            lambda month: "Winter" if month in (12, 1, 2) else "Spring" if month in (3, 4, 5)
            else "Summer" if month in (6, 7, 8) else "Autumn"
        )
        table = seasonal.pivot_table(
            index="season", columns="room_type", values="nightly_rate", aggfunc="size"
        ).fillna(0)
        order = [s for s in ["Spring", "Summer", "Autumn", "Winter"] if s in table.index]
        table = table.reindex(order)
        share = table.div(table.sum(axis=1), axis=0) * 100
        figure = charts.grouped_comparison(
            share.reset_index(), "season",
            {column: column for column in share.columns}, height=330, suffix="%",
        )
        figure.update_yaxes(ticksuffix="%", title="Share of nights sold")
        st.plotly_chart(figure, use_container_width=True)
        strongest = share.idxmax(axis=1)
        caption(
            "Share of nights sold by category in each season. "
            + "; ".join(f"{season}: {room} leads" for season, room in strongest.items())
            + "."
        )

    section("Room Insights", "Read automatically from category performance.")
    render_insights(business_insights.room_insights(context, performance), columns=2)

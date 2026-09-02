from __future__ import annotations

import streamlit as st

from src import business_insights, charts
from src.customer_analysis import (
    SEGMENT_TONES,
    customer_type_profile,
    guest_origin_profile,
    preferred_choices,
    repeat_guest_comparison,
    segment_guests,
    segment_summary,
)
from src.page_support import current_context, guard_empty, render_insights
from src.ui import caption, kpi_card, page_header, section, status_badge
from src.utils import PALETTE, format_currency, format_money, format_number, format_percent


def _segment_card(row) -> None:
    tone = SEGMENT_TONES.get(str(row["segment"]), "neutral")
    st.markdown(
        f"""
        <div class="gh-card" style="margin-bottom:14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
                <div style="font-size:1.12rem;font-weight:600;color:{PALETTE['ink']};">
                    {row['segment']}</div>
                {status_badge(tone, f"{row['guest_share']:.0f}% of guests")}
            </div>
            <div style="color:{PALETTE['body']};font-size:0.9rem;margin-top:8px;line-height:1.5;">
                {row['description']}</div>
            <div style="display:flex;gap:24px;flex-wrap:wrap;margin-top:14px;padding-top:12px;
                        border-top:1px solid {PALETTE['border']};">
                <div><div style="font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;
                     color:{PALETTE['muted']};font-weight:600;">Guests</div>
                     <div style="font-size:1.1rem;font-weight:600;color:{PALETTE['ink']};">
                     {format_number(row['guests'])}</div></div>
                <div><div style="font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;
                     color:{PALETTE['muted']};font-weight:600;">Average spend</div>
                     <div style="font-size:1.1rem;font-weight:600;color:{PALETTE['ink']};">
                     {format_money(row['average_spend'], 0)}</div></div>
                <div><div style="font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;
                     color:{PALETTE['muted']};font-weight:600;">Stays each</div>
                     <div style="font-size:1.1rem;font-weight:600;color:{PALETTE['ink']};">
                     {row['average_stays']:.1f}</div></div>
                <div><div style="font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;
                     color:{PALETTE['muted']};font-weight:600;">Nights per stay</div>
                     <div style="font-size:1.1rem;font-weight:600;color:{PALETTE['ink']};">
                     {row['average_length_of_stay']:.1f}</div></div>
                <div><div style="font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;
                     color:{PALETTE['muted']};font-weight:600;">Share of spending</div>
                     <div style="font-size:1.1rem;font-weight:600;color:{PALETTE['ink']};">
                     {row['revenue_share']:.0f}%</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    context = current_context()
    page_header(
        "Guest Intelligence",
        "Who stays at the hotel, and which guests are worth the most?",
        f"Reporting period: {context.period_label}",
    )
    if not guard_empty(context):
        return

    profile = customer_type_profile(context.bookings, context.room_nights)
    repeat = repeat_guest_comparison(context.bookings, context.room_nights)

    section("Guest Headlines")
    cards = st.columns(4)
    with cards[0]:
        kpi_card("Guests served", format_number(context.kpis["guests_served"]))
    with cards[1]:
        kpi_card("Average spend per stay", format_money(context.kpis["average_booking_value"], 0),
                 context.changes.get("average_booking_value"))
    with cards[2]:
        kpi_card("Average stay", f"{context.kpis['average_length_of_stay']:.1f} nights",
                 context.changes.get("average_length_of_stay"))
    with cards[3]:
        if not repeat.empty:
            returning = repeat.loc[repeat["guest_group"] == "Returning guests"]
            share = returning["revenue_share"].iat[0] if not returning.empty else 0.0
            kpi_card("From returning guests", format_percent(share),
                     note="Share of room revenue")

    section("Know Your Guests", "How each type of guest contributes.")
    left, right = st.columns([1.2, 1])
    with left:
        if not profile.empty:
            st.plotly_chart(
                charts.horizontal_bar(profile, "customer_type", "revenue", height=310),
                use_container_width=True,
            )
            caption("Room revenue by guest type over the selected period.")
    with right:
        if not profile.empty:
            st.plotly_chart(
                charts.category_donut(profile["customer_type"], profile["bookings"], height=310),
                use_container_width=True,
            )
            caption("Share of confirmed bookings by guest type.")

    if not profile.empty:
        display = profile[[
            "customer_type", "bookings", "guests", "revenue", "revenue_per_booking",
            "average_length_of_stay", "average_party_size", "average_lead_time",
            "cancellation_rate",
        ]].rename(columns={
            "customer_type": "Guest type",
            "bookings": "Bookings",
            "guests": "Guests",
            "revenue": "Room revenue",
            "revenue_per_booking": "Spend per stay",
            "average_length_of_stay": "Nights per stay",
            "average_party_size": "People per room",
            "average_lead_time": "Booked ahead (days)",
            "cancellation_rate": "Cancelled",
        })
        st.dataframe(
            display, hide_index=True, use_container_width=True,
            column_config={
                "Bookings": st.column_config.NumberColumn(format="%d"),
                "Guests": st.column_config.NumberColumn(format="%d"),
                "Room revenue": st.column_config.NumberColumn(format="$%d"),
                "Spend per stay": st.column_config.NumberColumn(format="$%.0f"),
                "Nights per stay": st.column_config.NumberColumn(format="%.1f"),
                "People per room": st.column_config.NumberColumn(format="%.1f"),
                "Booked ahead (days)": st.column_config.NumberColumn(format="%.0f"),
                "Cancelled": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )

    section("Returning Guests and First-Time Guests")
    if not repeat.empty:
        columns = st.columns(len(repeat))
        for column, (_, row) in zip(columns, repeat.iterrows()):
            with column:
                st.markdown(
                    f"""
                    <div class="gh-card">
                        <div style="font-size:1.1rem;font-weight:600;color:{PALETTE['ink']};">
                            {row['guest_group']}</div>
                        <div style="margin-top:12px;color:{PALETTE['body']};font-size:0.93rem;
                                    line-height:1.9;">
                            Bookings: <strong>{format_number(row['bookings'])}</strong><br/>
                            Worth per guest: <strong>{format_money(row['revenue_per_guest'], 0)}</strong><br/>
                            Spend per stay: <strong>{format_money(row['revenue_per_booking'], 0)}</strong><br/>
                            Stays per guest: <strong>{row['bookings_per_guest']:.1f}</strong><br/>
                            Cancelled: <strong>{format_percent(row['cancellation_rate'])}</strong><br/>
                            Share of revenue: <strong>{row['revenue_share']:.0f}%</strong>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        caption(
            "Returning guests book more than once, so their value builds over time even when "
            "each individual stay is shorter."
        )

    guest_ids = set(context.bookings["guest_id"].unique())
    segmented = segment_guests(context.guests.loc[context.guests["guest_id"].isin(guest_ids)])
    summary = segment_summary(segmented)

    section("Guest Groups", "Guests sorted by how much they return and how much they spend.")
    if summary.empty:
        caption("There are not enough completed stays in this selection to group guests.")
    else:
        left, right = st.columns([1.25, 1])
        with left:
            for _, row in summary.iterrows():
                _segment_card(row)
        with right:
            st.plotly_chart(charts.segment_bars(summary, height=330), use_container_width=True)
            caption(
                "Where the two bars differ, a group is contributing more or less spending than "
                "its size alone would suggest."
            )
            choices = preferred_choices(segmented)
            if not choices.empty:
                st.dataframe(
                    choices.rename(columns={
                        "segment": "Group",
                        "preferred_room_type": "Favoured room",
                        "preferred_booking_channel": "Favoured source",
                        "top_customer_type": "Mostly",
                        "guests": "Guests",
                    })[["Group", "Mostly", "Favoured room", "Favoured source"]],
                    hide_index=True, use_container_width=True,
                )

    origins = guest_origin_profile(context.bookings)
    if not origins.empty and len(origins) > 1:
        section("Where Guests Come From")
        left, right = st.columns([1.2, 1])
        with left:
            st.plotly_chart(
                charts.horizontal_bar(origins, "guest_region", "bookings", value_prefix="",
                                      height=290, colour=PALETTE["slate"]),
                use_container_width=True,
            )
        with right:
            leader = origins.iloc[0]
            st.markdown(
                f"""
                <div class="gh-card">
                    <div style="font-size:1.05rem;font-weight:600;color:{PALETTE['ink']};">
                        {leader['guest_region']} leads</div>
                    <div style="color:{PALETTE['body']};font-size:0.93rem;margin-top:10px;
                                line-height:1.6;">
                        {leader['share']:.0f}% of confirmed bookings come from this region,
                        worth {format_currency(leader['revenue'])} with an average stay of
                        {leader['average_length_of_stay']:.1f} nights.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    section("Guest Insights", "Read automatically from guest behaviour.")
    render_insights(business_insights.guest_insights(context), columns=2)

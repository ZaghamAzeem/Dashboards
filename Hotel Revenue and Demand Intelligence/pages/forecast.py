from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts
from src.forecasting import demand_alert, overall_demand_level
from src.page_support import current_context, forecast_for_current_filters, guard_empty
from src.ui import alert_banner, caption, kpi_card, page_header, section
from src.utils import PALETTE, format_currency, format_percent


def _outlook_message(forecast: pd.DataFrame, comparison: dict) -> str:
    weekend = forecast.loc[forecast["is_weekend"], "occupancy_rate"].mean()
    midweek = forecast.loc[~forecast["is_weekend"], "occupancy_rate"].mean()
    parts = []
    change = comparison.get("revenue_change")
    if change is None or abs(change) < 3:
        parts.append("Room revenue is expected to hold close to the level just recorded")
    elif change > 0:
        parts.append(f"Room revenue is expected to run about {abs(change):.0f}% higher than the period just finished")
    else:
        parts.append(f"Room revenue is expected to run about {abs(change):.0f}% below the period just finished")

    if pd.notna(weekend) and pd.notna(midweek):
        gap = weekend - midweek
        if gap >= 4:
            parts.append(f"with weekends noticeably stronger at {weekend:.0f}% occupancy against {midweek:.0f}% midweek")
        elif gap <= -4:
            parts.append(f"with midweek nights the busier of the two at {midweek:.0f}% occupancy against {weekend:.0f}% at weekends")
        else:
            parts.append("with demand spread evenly across the week")

    strongest = forecast.loc[forecast["revenue"].idxmax()]
    parts.append(
        f"The strongest single night looks like {strongest['weekday']} "
        f"{pd.Timestamp(strongest['stay_date']):%d %B}"
    )
    return ", ".join(parts[:2]) + ". " + parts[2] + "."


def render() -> None:
    context = current_context()
    page_header(
        "Demand Forecast",
        "What may happen next?",
        f"Outlook prepared from hotel activity up to {context.filters['date_range'][1]:%d %B %Y}",
    )
    if not guard_empty(context):
        return

    horizon = st.radio(
        "Outlook length", ["Next 7 nights", "Next 14 nights"], index=1,
        horizontal=True, label_visibility="collapsed", key="forecast_horizon",
    )
    nights = 7 if horizon.startswith("Next 7") else 14

    result = forecast_for_current_filters(nights)
    if not result.get("available"):
        caption("An outlook cannot be prepared from the records currently available.")
        return

    forecast = result["forecast"]
    comparison = result["comparison"]

    section("Demand Alert", "The headline for the days ahead.")
    alert = demand_alert(result)
    alert_banner(alert["tone"], alert["title"], alert["text"])

    section("Expected Position", f"The next {nights} nights at a glance.")
    cards = st.columns(4)
    peak = forecast.loc[forecast["occupancy_rate"].idxmax()]
    high_nights = int((forecast["demand_level"] == "High").sum())
    with cards[0]:
        kpi_card("Expected demand", overall_demand_level(result),
                 note=f"{high_nights} of {nights} nights busier than a typical night of the week")
    with cards[1]:
        kpi_card("Expected occupancy", format_percent(comparison["expected_occupancy"]),
                 note=f"{format_percent(comparison['recent_occupancy'])} in the period just finished")
    with cards[2]:
        kpi_card("Expected room revenue", format_currency(comparison["expected_revenue"]),
                 comparison["revenue_change"])
    with cards[3]:
        kpi_card("Busiest night ahead", f"{peak['weekday']} {peak['stay_date']:%d %b}",
                 note=f"Expected {format_percent(peak['occupancy_rate'])} occupancy")

    section("Past Demand and Expected Demand", "Recent nights on the left, the outlook on the right.")
    st.plotly_chart(
        charts.forecast_view(result["history"], forecast, result["capacity"], height=400),
        use_container_width=True,
    )
    caption(
        "The solid line is what the hotel actually achieved. The dotted line is what is expected, "
        "based on how demand has behaved on comparable nights."
    )

    section("Revenue Outlook", "Expected room revenue for each night ahead.")
    st.plotly_chart(charts.forecast_revenue_bars(forecast, height=310), use_container_width=True)
    caption(
        "Darker bars mark nights expected to be busier than a typical night of that weekday, "
        "lighter bars quieter ones."
    )
    st.markdown(
        f"""
        <div class="gh-story" style="border-left-color:{PALETTE['brass']};">
            <div class="gh-story-title" style="color:{PALETTE['brass']};">In plain terms</div>
            <div class="gh-story-text">{_outlook_message(forecast, comparison)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    section("Night by Night")
    display = forecast[["stay_date", "weekday", "demand_level", "occupancy_rate",
                        "rooms_sold", "adr", "revenue"]].copy()
    display["stay_date"] = display["stay_date"].dt.strftime("%d %b %Y")
    display = display.rename(columns={
        "stay_date": "Night",
        "weekday": "Day",
        "demand_level": "Expected demand",
        "occupancy_rate": "Expected occupancy",
        "rooms_sold": "Rooms expected to sell",
        "adr": "Expected average rate",
        "revenue": "Expected room revenue",
    })
    st.dataframe(
        display, hide_index=True, use_container_width=True,
        column_config={
            "Expected occupancy": st.column_config.NumberColumn(format="%.1f%%"),
            "Rooms expected to sell": st.column_config.NumberColumn(format="%.0f"),
            "Expected average rate": st.column_config.NumberColumn(format="$%.0f"),
            "Expected room revenue": st.column_config.NumberColumn(format="$%d"),
        },
    )

    quality = result.get("quality") or {}
    if quality.get("accuracy_percent"):
        section("How Reliable Is This Outlook?")
        left, right = st.columns([1, 1.4])
        with left:
            kpi_card("Recent accuracy", format_percent(quality["accuracy_percent"]),
                     note=f"Checked against the {quality['validation_days']} most recent nights")
        with right:
            improvement = quality["accuracy_percent"] - quality.get("baseline_accuracy_percent", 0)
            st.markdown(
                f"""
                <div class="gh-card">
                    <div style="color:{PALETTE['body']};font-size:0.93rem;line-height:1.65;">
                        The outlook was tested against nights the hotel has already traded. Room
                        numbers came within {quality['mean_absolute_error']:.1f} rooms of the
                        true figure on an average night, which is
                        {abs(improvement):.1f} points
                        {"better" if improvement >= 0 else "weaker"} than simply repeating what
                        happened on the same day a week earlier. Expect the first few nights to be
                        the most dependable.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if context.filters.get("customer_types") or context.filters.get("channels"):
        caption(
            "The outlook covers the whole hotel for the room categories selected. Guest type and "
            "booking source filters apply to the rest of the dashboard, not to this outlook."
        )

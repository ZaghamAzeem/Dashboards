from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

from src.data_loader import DataUnavailable, data_window, database_ready, load_bookings, load_rooms
from src.ui import friendly_error, inject_theme, page_header
from src.utils import HOTEL_NAME, HOTEL_TAGLINE

LOGGER = logging.getLogger("grand_horizon")

st.set_page_config(
    page_title=f"{HOTEL_NAME} | {HOTEL_TAGLINE}",
    page_icon="\U0001F3E8",
    layout="wide",
    initial_sidebar_state="expanded",
)

PERIOD_PRESETS = {
    "Last 30 days": 30,
    "Last 90 days": 90,
    "Last 6 months": 183,
    "Last 12 months": 365,
    "Full history": None,
    "Custom period": "custom",
}


def _build_filters() -> dict:
    window_start, window_end = data_window()
    bookings = load_bookings()
    rooms = load_rooms()

    st.sidebar.markdown("### Reporting period")
    preset = st.sidebar.selectbox(
        "Period", list(PERIOD_PRESETS.keys()), index=3, label_visibility="collapsed"
    )
    span = PERIOD_PRESETS[preset]

    if span == "custom":
        chosen = st.sidebar.date_input(
            "Choose dates",
            value=(max(window_start, (pd.Timestamp(window_end) - pd.Timedelta(days=89)).date()),
                   window_end),
            min_value=window_start,
            max_value=window_end,
        )
        if isinstance(chosen, (list, tuple)) and len(chosen) == 2:
            start, end = chosen
        else:
            start, end = window_start, window_end
    elif span is None:
        start, end = window_start, window_end
    else:
        start = max(window_start, (pd.Timestamp(window_end) - pd.Timedelta(days=span - 1)).date())
        end = window_end

    st.sidebar.markdown("### Focus")
    room_types = st.sidebar.multiselect(
        "Room category", sorted(rooms["room_type"].unique()), placeholder="All room categories"
    )
    customer_types = st.sidebar.multiselect(
        "Guest type", sorted(bookings["customer_type"].unique()), placeholder="All guest types"
    )
    channels = st.sidebar.multiselect(
        "Booking source", sorted(bookings["booking_channel"].unique()), placeholder="All sources"
    )

    st.sidebar.markdown(
        f"""
        <div style="margin-top:22px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.14);
                    font-size:0.78rem;color:#9FB3C4;line-height:1.5;">
            Hotel records available from<br/>
            <strong style="color:#E8EDF2;">{window_start:%d %B %Y}</strong> to
            <strong style="color:#E8EDF2;">{window_end:%d %B %Y}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return {
        "date_range": (start, end),
        "room_types": room_types,
        "customer_types": customer_types,
        "channels": channels,
        "preset": preset,
    }


def _navigation():
    from pages import (
        bookings as bookings_page,
        cancellations,
        forecast,
        guests,
        overview,
        questions,
        recommendations,
        revenue,
        rooms,
    )

    pages = {
        "overview": st.Page(overview.render, title="Hotel Overview", icon="\U0001F3E8",
                            url_path="overview", default=True),
        "revenue": st.Page(revenue.render, title="Revenue Story", icon="\U0001F4B0",
                           url_path="revenue"),
        "bookings": st.Page(bookings_page.render, title="Booking Trends", icon="\U0001F4C5",
                            url_path="bookings"),
        "rooms": st.Page(rooms.render, title="Room Performance", icon="\U0001F6CF",
                         url_path="rooms"),
        "guests": st.Page(guests.render, title="Guest Intelligence", icon="\U0001F465",
                          url_path="guests"),
        "cancellations": st.Page(cancellations.render, title="Cancellations", icon="❌",
                                 url_path="cancellations"),
        "forecast": st.Page(forecast.render, title="Demand Forecast", icon="\U0001F52E",
                            url_path="forecast"),
        "recommendations": st.Page(recommendations.render, title="Recommendations", icon="\U0001F4A1",
                                   url_path="recommendations"),
        "questions": st.Page(questions.render, title="Business Questions", icon="❓",
                             url_path="questions"),
    }
    st.session_state["pages"] = pages
    return st.navigation(list(pages.values()))


def main() -> None:
    inject_theme()

    if not database_ready():
        page_header(
            "Welcome to your hotel dashboard",
            "The hotel records have not been prepared yet.",
        )
        friendly_error(
            "Hotel performance data is not available yet. Once the hotel records have been "
            "prepared, this dashboard will show revenue, bookings, guests and the demand outlook."
        )
        return

    try:
        navigation = _navigation()
        st.session_state["filters"] = _build_filters()
        navigation.run()
    except DataUnavailable:
        friendly_error(
            "We could not read the hotel records right now. Please make sure the hotel data "
            "has been prepared, then refresh this page."
        )
    except Exception:
        LOGGER.exception("Unhandled error while rendering the dashboard")
        friendly_error(
            "We could not load this section right now. Please check that the hotel data has "
            "been prepared, then refresh the page. If it keeps happening, try widening the "
            "reporting period or clearing the focus filters."
        )


main()

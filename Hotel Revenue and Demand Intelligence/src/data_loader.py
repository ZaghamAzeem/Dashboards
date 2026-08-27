from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "hotel.db"

REQUIRED_TABLES = ("bookings", "rooms", "guests", "daily_metrics")

DATE_COLUMNS = {
    "bookings": ["booking_date", "check_in_date", "check_out_date"],
    "daily_metrics": ["stay_date"],
    "guests": ["first_stay_date", "last_stay_date"],
}


class DataUnavailable(Exception):
    pass


def database_ready() -> bool:
    if not DB_PATH.exists():
        return False
    try:
        with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as connection:
            found = pd.read_sql(
                "SELECT name FROM sqlite_master WHERE type='table'", connection
            )["name"].tolist()
        return all(table in found for table in REQUIRED_TABLES)
    except sqlite3.Error:
        return False


def _read_table(name: str) -> pd.DataFrame:
    if not DB_PATH.exists():
        raise DataUnavailable("The hotel dataset has not been generated yet.")
    try:
        with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as connection:
            frame = pd.read_sql(f"SELECT * FROM {name}", connection)
    except (sqlite3.Error, pd.errors.DatabaseError) as error:
        raise DataUnavailable("The hotel dataset could not be opened.") from error
    for column in DATE_COLUMNS.get(name, []):
        frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return frame


@st.cache_data(show_spinner=False)
def load_bookings() -> pd.DataFrame:
    bookings = _read_table("bookings")
    bookings["stay_month"] = bookings["check_in_date"].dt.to_period("M").dt.to_timestamp()
    bookings["stay_weekday"] = bookings["check_in_date"].dt.day_name()
    bookings["booking_weekday"] = bookings["booking_date"].dt.day_name()
    bookings["season"] = bookings["check_in_date"].dt.month.map(season_for_month)
    bookings["lead_time_group"] = pd.cut(
        bookings["lead_time_days"],
        bins=[-1, 3, 14, 45, 90, 400],
        labels=["Same week", "1-2 weeks ahead", "2-6 weeks ahead",
                "6-13 weeks ahead", "More than 3 months ahead"],
    )
    bookings["is_confirmed"] = bookings["is_cancelled"] == 0
    return bookings


@st.cache_data(show_spinner=False)
def load_rooms() -> pd.DataFrame:
    return _read_table("rooms")


@st.cache_data(show_spinner=False)
def load_guests() -> pd.DataFrame:
    return _read_table("guests")


@st.cache_data(show_spinner=False)
def load_daily_metrics() -> pd.DataFrame:
    metrics = _read_table("daily_metrics")
    metrics["weekday"] = metrics["stay_date"].dt.day_name()
    metrics["month"] = metrics["stay_date"].dt.to_period("M").dt.to_timestamp()
    metrics["season"] = metrics["stay_date"].dt.month.map(season_for_month)
    metrics["is_weekend"] = metrics["stay_date"].dt.weekday >= 4
    return metrics


@st.cache_data(show_spinner=False)
def load_room_nights() -> pd.DataFrame:
    bookings = load_bookings()
    confirmed = bookings.loc[bookings["is_confirmed"]].copy()
    expanded = confirmed.loc[confirmed.index.repeat(confirmed["number_of_nights"])].copy()
    offsets = expanded.groupby(level=0).cumcount()
    expanded["stay_date"] = expanded["check_in_date"] + pd.to_timedelta(offsets, unit="D")
    window_start, window_end = data_window()
    inside = (expanded["stay_date"] >= pd.Timestamp(window_start)) & (
        expanded["stay_date"] <= pd.Timestamp(window_end)
    )
    columns = ["stay_date", "room_type", "customer_type", "booking_channel",
               "nightly_rate", "number_of_guests", "repeat_guest", "promotion_used"]
    return expanded.loc[inside, columns].reset_index(drop=True)


@st.cache_data(show_spinner=False)
def data_window() -> tuple[date, date]:
    metrics = _read_table("daily_metrics")
    return metrics["stay_date"].min().date(), metrics["stay_date"].max().date()


def season_for_month(month: int) -> str:
    if month in (12, 1, 2):
        return "Winter"
    if month in (3, 4, 5):
        return "Spring"
    if month in (6, 7, 8):
        return "Summer"
    return "Autumn"


def room_capacity(rooms: pd.DataFrame, room_types: list[str] | None = None) -> int:
    if room_types:
        selected = rooms.loc[rooms["room_type"].isin(room_types)]
    else:
        selected = rooms
    return int(selected["rooms_available"].sum())


def apply_filters(frame: pd.DataFrame, filters: dict, date_column: str) -> pd.DataFrame:
    result = frame
    start, end = filters["date_range"]
    mask = (result[date_column] >= pd.Timestamp(start)) & (
        result[date_column] <= pd.Timestamp(end)
    )
    result = result.loc[mask]
    for column, key in (
        ("room_type", "room_types"),
        ("customer_type", "customer_types"),
        ("booking_channel", "channels"),
    ):
        selected = filters.get(key)
        if selected and column in result.columns:
            result = result.loc[result[column].isin(selected)]
    return result.copy()


def previous_period(filters: dict) -> tuple[pd.Timestamp, pd.Timestamp]:
    start, end = filters["date_range"]
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)
    span = (end - start).days + 1
    return start - pd.Timedelta(days=span), start - pd.Timedelta(days=1)

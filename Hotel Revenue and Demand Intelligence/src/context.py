from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src import analytics
from src.data_loader import (
    apply_filters,
    data_window,
    load_bookings,
    load_guests,
    load_room_nights,
    load_rooms,
    previous_period,
    room_capacity,
)


@dataclass
class AnalysisContext:
    filters: dict
    rooms: pd.DataFrame
    guests: pd.DataFrame
    bookings: pd.DataFrame
    room_nights: pd.DataFrame
    daily: pd.DataFrame
    capacity: int
    days: int
    kpis: dict
    previous_kpis: dict
    changes: dict
    monthly: pd.DataFrame = field(default_factory=pd.DataFrame)
    weekday: pd.DataFrame = field(default_factory=pd.DataFrame)
    seasonal: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def has_data(self) -> bool:
        return not self.bookings.empty and self.capacity > 0

    @property
    def period_label(self) -> str:
        start, end = self.filters["date_range"]
        return f"{pd.Timestamp(start):%d %b %Y} to {pd.Timestamp(end):%d %b %Y}"


def default_filters(days_back: int = 365) -> dict:
    window_start, window_end = data_window()
    start = max(window_start, (pd.Timestamp(window_end) - pd.Timedelta(days=days_back - 1)).date())
    return {
        "date_range": (start, window_end),
        "room_types": [],
        "customer_types": [],
        "channels": [],
    }


def build_context(filters: dict) -> AnalysisContext:
    rooms = load_rooms()
    guests = load_guests()
    bookings = apply_filters(load_bookings(), filters, "check_in_date")
    room_nights = apply_filters(load_room_nights(), filters, "stay_date")
    capacity = room_capacity(rooms, filters.get("room_types"))

    start, end = filters["date_range"]
    days = (pd.Timestamp(end) - pd.Timestamp(start)).days + 1
    daily = analytics.daily_performance(room_nights, capacity, start, end)

    kpis = analytics.compute_kpis(bookings, room_nights, capacity, days)

    previous_start, previous_end = previous_period(filters)
    window_start, _ = data_window()
    if previous_start.date() >= window_start:
        previous_filters = dict(filters)
        previous_filters["date_range"] = (previous_start.date(), previous_end.date())
        previous_bookings = apply_filters(load_bookings(), previous_filters, "check_in_date")
        previous_nights = apply_filters(load_room_nights(), previous_filters, "stay_date")
        previous_days = (previous_end - previous_start).days + 1
        previous_kpis = analytics.compute_kpis(
            previous_bookings, previous_nights, capacity, previous_days
        )
        changes = analytics.compare_kpis(kpis, previous_kpis)
    else:
        previous_kpis = {}
        changes = {}

    monthly = analytics.monthly_performance(daily)
    weekday = analytics.weekday_performance(daily)
    seasonal = analytics.seasonal_performance(daily)

    return AnalysisContext(
        filters=filters,
        rooms=rooms,
        guests=guests,
        bookings=bookings,
        room_nights=room_nights,
        daily=daily,
        capacity=capacity,
        days=days,
        kpis=kpis,
        previous_kpis=previous_kpis,
        changes=changes,
        monthly=monthly,
        weekday=weekday,
        seasonal=seasonal,
    )


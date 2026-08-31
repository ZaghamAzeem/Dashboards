from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from src.context import AnalysisContext, build_context, default_filters
from src.data_loader import load_daily_metrics, load_room_nights, load_rooms, room_capacity
from src.forecasting import forecast_demand
from src.ui import friendly_error, story_card


def current_filters() -> dict:
    filters = st.session_state.get("filters")
    if not filters:
        filters = default_filters()
        st.session_state["filters"] = filters
    return filters


@st.cache_data(show_spinner=False)
def _cached_context(date_range: tuple, room_types: tuple, customer_types: tuple,
                    channels: tuple) -> AnalysisContext:
    return build_context({
        "date_range": date_range,
        "room_types": list(room_types),
        "customer_types": list(customer_types),
        "channels": list(channels),
    })


def current_context() -> AnalysisContext:
    filters = current_filters()
    return _cached_context(
        tuple(filters["date_range"]),
        tuple(filters.get("room_types") or []),
        tuple(filters.get("customer_types") or []),
        tuple(filters.get("channels") or []),
    )


@st.cache_data(show_spinner=False)
def _forecast_series(room_types: tuple) -> tuple[pd.DataFrame, int]:
    metrics = load_daily_metrics()
    rooms = load_rooms()
    capacity = room_capacity(rooms, list(room_types))
    if not room_types:
        return metrics[["stay_date", "rooms_sold", "adr", "room_revenue", "occupancy_rate",
                        "is_promotion", "is_special_period"]].copy(), capacity

    nights = load_room_nights()
    nights = nights.loc[nights["room_type"].isin(list(room_types))]
    index = pd.DatetimeIndex(metrics["stay_date"])
    grouped = nights.groupby("stay_date").agg(
        rooms_sold=("nightly_rate", "size"), room_revenue=("nightly_rate", "sum")
    ).reindex(index, fill_value=0)
    series = grouped.reset_index(names="stay_date")
    series["adr"] = np.where(
        series["rooms_sold"] > 0, series["room_revenue"] / series["rooms_sold"].replace(0, np.nan), 0.0
    )
    series["adr"] = series["adr"].fillna(0.0)
    series["occupancy_rate"] = series["rooms_sold"] / capacity * 100 if capacity else 0.0
    series["is_promotion"] = metrics["is_promotion"].to_numpy()
    series["is_special_period"] = metrics["is_special_period"].to_numpy()
    return series, capacity


@st.cache_data(show_spinner=False)
def cached_forecast(room_types: tuple, horizon: int = 14) -> dict:
    series, capacity = _forecast_series(room_types)
    return forecast_demand(series, capacity, horizon)


def forecast_for_current_filters(horizon: int = 14) -> dict:
    filters = current_filters()
    return cached_forecast(tuple(filters.get("room_types") or []), horizon)


def render_insights(insights: list[dict], columns: int = 2, limit: int | None = None) -> None:
    items = insights[:limit] if limit else insights
    if not items:
        friendly_error("There is not enough activity in this period to draw conclusions from.")
        return
    if columns <= 1:
        for item in items:
            story_card(item["title"], item["text"], item["tone"])
        return
    for start in range(0, len(items), columns):
        row = items[start:start + columns]
        for column, item in zip(st.columns(columns), row):
            with column:
                story_card(item["title"], item["text"], item["tone"])


def guard_empty(context) -> bool:
    if context.has_data:
        return True
    friendly_error(
        "There are no hotel records for the period and filters currently selected. "
        "Widen the reporting period or clear the focus filters in the panel on the left."
    )
    return False


def go_to(page_key: str) -> None:
    pages = st.session_state.get("pages", {})
    target = pages.get(page_key)
    if target is not None:
        st.switch_page(target)

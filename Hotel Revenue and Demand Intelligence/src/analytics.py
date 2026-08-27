from __future__ import annotations

import numpy as np
import pandas as pd

WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SEASON_ORDER = ["Spring", "Summer", "Autumn", "Winter"]


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator in (0, None) or (isinstance(denominator, float) and np.isnan(denominator)):
        return 0.0
    return float(numerator) / float(denominator)


def compute_kpis(bookings: pd.DataFrame, room_nights: pd.DataFrame,
                 capacity: int, days: int) -> dict:
    confirmed = bookings.loc[bookings["is_confirmed"]] if len(bookings) else bookings
    rooms_sold = int(len(room_nights))
    revenue = float(room_nights["nightly_rate"].sum()) if rooms_sold else 0.0
    available = max(capacity * days, 0)
    return {
        "revenue": revenue,
        "rooms_sold": rooms_sold,
        "rooms_available": available,
        "occupancy_rate": _safe_divide(rooms_sold, available) * 100,
        "adr": _safe_divide(revenue, rooms_sold),
        "revpar": _safe_divide(revenue, available),
        "bookings": int(len(confirmed)),
        "total_requests": int(len(bookings)),
        "cancellation_rate": _safe_divide(int((bookings["is_cancelled"] == 1).sum()),
                                          len(bookings)) * 100 if len(bookings) else 0.0,
        "average_booking_value": _safe_divide(revenue, len(confirmed)),
        "average_length_of_stay": float(confirmed["number_of_nights"].mean()) if len(confirmed) else 0.0,
        "average_lead_time": float(confirmed["lead_time_days"].mean()) if len(confirmed) else 0.0,
        "guests_served": int(confirmed["guest_id"].nunique()) if len(confirmed) else 0,
        "days": days,
    }


def percent_change(current: float, previous: float):
    if previous is None or previous == 0 or np.isnan(previous):
        return None
    return (current - previous) / abs(previous) * 100


def compare_kpis(current: dict, previous: dict) -> dict:
    keys = ["revenue", "occupancy_rate", "adr", "revpar", "bookings",
            "cancellation_rate", "average_booking_value", "average_length_of_stay"]
    return {key: percent_change(current.get(key, 0.0), previous.get(key, 0.0)) for key in keys}


def revenue_by_dimension(room_nights: pd.DataFrame, dimension: str) -> pd.DataFrame:
    if room_nights.empty:
        return pd.DataFrame(columns=[dimension, "revenue", "room_nights", "adr", "revenue_share"])
    grouped = room_nights.groupby(dimension).agg(
        revenue=("nightly_rate", "sum"),
        room_nights=("nightly_rate", "size"),
    ).reset_index()
    grouped["adr"] = grouped["revenue"] / grouped["room_nights"]
    total = grouped["revenue"].sum()
    grouped["revenue_share"] = grouped["revenue"] / total * 100 if total else 0.0
    return grouped.sort_values("revenue", ascending=False).reset_index(drop=True)


def daily_performance(room_nights: pd.DataFrame, capacity: int,
                      start, end) -> pd.DataFrame:
    index = pd.date_range(start, end, freq="D")
    if room_nights.empty:
        frame = pd.DataFrame(index=index)
        frame["revenue"] = 0.0
        frame["rooms_sold"] = 0
    else:
        grouped = room_nights.groupby("stay_date").agg(
            revenue=("nightly_rate", "sum"),
            rooms_sold=("nightly_rate", "size"),
        )
        frame = grouped.reindex(index, fill_value=0)
    frame.index.name = "stay_date"
    frame = frame.reset_index()
    frame["occupancy_rate"] = frame["rooms_sold"] / capacity * 100 if capacity else 0.0
    frame["adr"] = np.where(frame["rooms_sold"] > 0,
                            frame["revenue"] / frame["rooms_sold"].replace(0, np.nan), 0.0)
    frame["adr"] = frame["adr"].fillna(0.0)
    frame["revpar"] = frame["revenue"] / capacity if capacity else 0.0
    frame["weekday"] = frame["stay_date"].dt.day_name()
    frame["month"] = frame["stay_date"].dt.to_period("M").dt.to_timestamp()
    return frame


def monthly_performance(daily: pd.DataFrame) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame(columns=["month", "revenue", "rooms_sold", "occupancy_rate", "adr", "days"])
    grouped = daily.groupby("month").agg(
        revenue=("revenue", "sum"),
        rooms_sold=("rooms_sold", "sum"),
        occupancy_rate=("occupancy_rate", "mean"),
        days=("stay_date", "size"),
    ).reset_index()
    grouped["adr"] = np.where(grouped["rooms_sold"] > 0,
                              grouped["revenue"] / grouped["rooms_sold"], 0.0)
    grouped["month_label"] = grouped["month"].dt.strftime("%b %Y")
    return grouped


def weekday_performance(daily: pd.DataFrame) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame(columns=["weekday", "revenue", "occupancy_rate", "adr"])
    grouped = daily.groupby("weekday").agg(
        revenue=("revenue", "mean"),
        rooms_sold=("rooms_sold", "mean"),
        occupancy_rate=("occupancy_rate", "mean"),
    ).reindex(WEEKDAY_ORDER).reset_index()
    grouped["adr"] = np.where(grouped["rooms_sold"] > 0,
                              grouped["revenue"] / grouped["rooms_sold"], 0.0)
    return grouped


def seasonal_performance(daily: pd.DataFrame) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame(columns=["season", "revenue", "occupancy_rate"])
    frame = daily.copy()
    frame["season"] = frame["stay_date"].dt.month.map(
        lambda m: "Winter" if m in (12, 1, 2) else "Spring" if m in (3, 4, 5)
        else "Summer" if m in (6, 7, 8) else "Autumn"
    )
    grouped = frame.groupby("season").agg(
        revenue=("revenue", "sum"),
        occupancy_rate=("occupancy_rate", "mean"),
        rooms_sold=("rooms_sold", "sum"),
    ).reindex(SEASON_ORDER).dropna(how="all").reset_index()
    grouped["adr"] = np.where(grouped["rooms_sold"] > 0,
                              grouped["revenue"] / grouped["rooms_sold"], 0.0)
    return grouped


def booking_volume(bookings: pd.DataFrame, freq: str = "D") -> pd.DataFrame:
    if bookings.empty:
        return pd.DataFrame(columns=["period", "bookings", "cancellations"])
    frame = bookings.copy()
    frame["period"] = frame["check_in_date"].dt.to_period(freq).dt.to_timestamp()
    grouped = frame.groupby("period").agg(
        bookings=("is_confirmed", "sum"),
        cancellations=("is_cancelled", "sum"),
    ).reset_index()
    grouped["bookings"] = grouped["bookings"].astype(int)
    return grouped


def bookings_by_dimension(bookings: pd.DataFrame, dimension: str) -> pd.DataFrame:
    if bookings.empty:
        return pd.DataFrame(columns=[dimension, "bookings", "cancellations", "cancellation_rate"])
    grouped = bookings.groupby(dimension, observed=True).agg(
        bookings=("is_confirmed", "sum"),
        cancellations=("is_cancelled", "sum"),
        total=("booking_id", "count"),
        average_length_of_stay=("number_of_nights", "mean"),
        average_lead_time=("lead_time_days", "mean"),
    ).reset_index()
    grouped["cancellation_rate"] = grouped["cancellations"] / grouped["total"] * 100
    grouped["bookings"] = grouped["bookings"].astype(int)
    return grouped.sort_values("bookings", ascending=False).reset_index(drop=True)


def booking_lead_time_profile(bookings: pd.DataFrame) -> pd.DataFrame:
    confirmed = bookings.loc[bookings["is_confirmed"]]
    if confirmed.empty:
        return pd.DataFrame(columns=["lead_time_group", "bookings", "share"])
    grouped = confirmed.groupby("lead_time_group", observed=True).size().reset_index(name="bookings")
    grouped["share"] = grouped["bookings"] / grouped["bookings"].sum() * 100
    return grouped


def booking_weekday_profile(bookings: pd.DataFrame) -> pd.DataFrame:
    confirmed = bookings.loc[bookings["is_confirmed"]]
    if confirmed.empty:
        return pd.DataFrame(columns=["booking_weekday", "bookings"])
    grouped = confirmed.groupby("booking_weekday").size().reindex(WEEKDAY_ORDER, fill_value=0)
    frame = grouped.reset_index()
    frame.columns = ["booking_weekday", "bookings"]
    frame["share"] = frame["bookings"] / frame["bookings"].sum() * 100
    return frame


def room_performance(bookings: pd.DataFrame, room_nights: pd.DataFrame,
                     rooms: pd.DataFrame, days: int) -> pd.DataFrame:
    if room_nights.empty or days <= 0:
        return pd.DataFrame()

    nights = room_nights.groupby("room_type").agg(
        room_nights_sold=("nightly_rate", "size"),
        revenue=("nightly_rate", "sum"),
    )
    booking_stats = bookings.groupby("room_type").agg(
        total_requests=("booking_id", "count"),
        cancellations=("is_cancelled", "sum"),
        confirmed_bookings=("is_confirmed", "sum"),
        average_length_of_stay=("number_of_nights", "mean"),
    )
    inventory = rooms.set_index("room_type")[["rooms_available", "base_rate", "max_occupancy"]]

    table = inventory.join(nights, how="inner").join(booking_stats, how="left").reset_index()
    table = table.dropna(subset=["room_nights_sold"])
    table["confirmed_bookings"] = table["confirmed_bookings"].fillna(0).astype(int)
    table["cancellations"] = table["cancellations"].fillna(0).astype(int)
    table["total_requests"] = table["total_requests"].fillna(0).astype(int)
    table["occupancy_rate"] = table["room_nights_sold"] / (table["rooms_available"] * days) * 100
    table["adr"] = table["revenue"] / table["room_nights_sold"]
    table["revpar"] = table["revenue"] / (table["rooms_available"] * days)
    table["cancellation_rate"] = np.where(
        table["total_requests"] > 0, table["cancellations"] / table["total_requests"] * 100, 0.0
    )
    table["revenue_share"] = table["revenue"] / table["revenue"].sum() * 100
    table["rate_realisation"] = table["adr"] / table["base_rate"] * 100

    hotel_occupancy = table["room_nights_sold"].sum() / (table["rooms_available"].sum() * days) * 100
    hotel_revpar = table["revenue"].sum() / (table["rooms_available"].sum() * days)
    hotel_cancellation = _safe_divide(table["cancellations"].sum(), table["total_requests"].sum()) * 100

    table["revpar_index"] = table["revpar"] / max(hotel_revpar, 1e-9) * 100
    table["occupancy_index"] = table["occupancy_rate"] / max(hotel_occupancy, 1e-9) * 100

    yield_score = (np.clip(table["revpar_index"] / 100, 0.60, 1.60) - 0.60) / 1.00
    occupancy_score = (np.clip(table["occupancy_index"] / 100, 0.70, 1.30) - 0.70) / 0.60
    rate_score = (np.clip(table["adr"] / table["base_rate"], 0.74, 1.04) - 0.74) / 0.30
    cancel_ratio = np.where(
        table["cancellation_rate"] > 0,
        hotel_cancellation / table["cancellation_rate"].replace(0, np.nan),
        1.3,
    )
    cancel_score = (np.clip(cancel_ratio, 0.7, 1.3) - 0.7) / 0.6

    table["performance_score"] = (
        0.35 * yield_score + 0.30 * occupancy_score + 0.20 * rate_score + 0.15 * cancel_score
    ).round(3)
    table["status"] = np.select(
        [table["performance_score"] >= 0.55, table["performance_score"] >= 0.40],
        ["Strong Performer", "Performing Well"],
        default="Needs Attention",
    )
    table["status_tone"] = np.select(
        [table["status"] == "Strong Performer", table["status"] == "Performing Well"],
        ["healthy", "neutral"],
        default="watch",
    )
    return table.sort_values("performance_score", ascending=False).reset_index(drop=True)


def cancellation_breakdown(bookings: pd.DataFrame, dimension: str,
                           minimum_volume: int = 40) -> pd.DataFrame:
    if bookings.empty:
        return pd.DataFrame(columns=[dimension, "total", "cancellations", "cancellation_rate"])
    grouped = bookings.groupby(dimension, observed=True).agg(
        total=("booking_id", "count"),
        cancellations=("is_cancelled", "sum"),
    ).reset_index()
    lost = (
        bookings.loc[bookings["is_cancelled"] == 1]
        .groupby(dimension, observed=True)["booking_value"]
        .sum()
    )
    grouped["lost_value"] = pd.to_numeric(
        grouped[dimension].astype(object).map(lost), errors="coerce"
    ).fillna(0.0)
    grouped = grouped.loc[grouped["total"] >= minimum_volume]
    grouped["cancellation_rate"] = grouped["cancellations"] / grouped["total"] * 100
    return grouped.sort_values("cancellation_rate", ascending=False).reset_index(drop=True)


def cancellation_summary(bookings: pd.DataFrame) -> dict:
    if bookings.empty:
        return {"cancellation_rate": 0.0, "cancelled_bookings": 0, "lost_value": 0.0,
                "lost_room_nights": 0}
    cancelled = bookings.loc[bookings["is_cancelled"] == 1]
    return {
        "cancellation_rate": len(cancelled) / len(bookings) * 100,
        "cancelled_bookings": int(len(cancelled)),
        "lost_value": float(cancelled["booking_value"].sum()),
        "lost_room_nights": int(cancelled["number_of_nights"].sum()),
    }


def occupancy_pressure(daily: pd.DataFrame) -> dict:
    if daily.empty:
        return {"peak_days": 0, "quiet_days": 0, "average": 0.0}
    return {
        "average": float(daily["occupancy_rate"].mean()),
        "peak_days": int((daily["occupancy_rate"] >= 90).sum()),
        "quiet_days": int((daily["occupancy_rate"] <= 55).sum()),
        "best_day": daily.loc[daily["occupancy_rate"].idxmax(), "stay_date"],
        "quietest_day": daily.loc[daily["occupancy_rate"].idxmin(), "stay_date"],
    }


def revenue_trend_direction(monthly: pd.DataFrame, window: int = 3) -> dict:
    complete = monthly.loc[monthly["days"] >= 28] if "days" in monthly.columns else monthly
    if len(complete) < window * 2:
        return {"direction": "steady", "change": None, "recent": None,
                "previous": None, "basis": "none"}

    indexed = complete.set_index("month")["revenue"]
    recent_months = complete.tail(window)["month"]
    prior_year_months = [month - pd.DateOffset(years=1) for month in recent_months]

    recent = float(indexed.loc[recent_months].mean())
    if all(month in indexed.index for month in prior_year_months):
        previous = float(indexed.loc[prior_year_months].mean())
        basis = "year_on_year"
    else:
        previous = float(complete.tail(window * 2).head(window)["revenue"].mean())
        basis = "sequential"
    change = percent_change(recent, previous)
    if change is None:
        direction = "steady"
    elif change >= 3:
        direction = "growing"
    elif change <= -3:
        direction = "softening"
    else:
        direction = "steady"
    return {"direction": direction, "change": change, "recent": recent,
            "previous": previous, "basis": basis, "window": window}

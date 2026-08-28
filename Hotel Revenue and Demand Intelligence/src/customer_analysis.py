from __future__ import annotations

import numpy as np
import pandas as pd

SEGMENT_ORDER = ["High Value", "Regular", "Occasional", "Low Engagement"]

SEGMENT_DESCRIPTIONS = {
    "High Value": "Guests who return and spend well above the typical guest.",
    "Regular": "Guests who have stayed more than once and book dependably.",
    "Occasional": "Guests who have stayed once and spent around or above the typical amount.",
    "Low Engagement": "Guests with a single low-value stay, often booked a long time ago.",
}

SEGMENT_TONES = {
    "High Value": "healthy",
    "Regular": "healthy",
    "Occasional": "neutral",
    "Low Engagement": "watch",
}


def segment_guests(guests: pd.DataFrame) -> pd.DataFrame:
    stayed = guests.loc[guests["total_stays"] > 0].copy()
    if stayed.empty:
        stayed["segment"] = pd.Series(dtype="object")
        return stayed

    spend_high = stayed["total_spend"].quantile(0.75)
    spend_mid = stayed["total_spend"].median()
    recent_cutoff = stayed["days_since_last_stay"].quantile(0.70)

    is_repeat = stayed["total_stays"] >= 2
    conditions = [
        is_repeat & (stayed["total_spend"] >= spend_high),
        is_repeat,
        stayed["total_spend"] >= spend_mid,
        stayed["days_since_last_stay"] >= recent_cutoff,
    ]
    choices = ["High Value", "Regular", "Occasional", "Low Engagement"]
    stayed["segment"] = np.select(conditions, choices, default="Low Engagement")
    stayed["segment"] = pd.Categorical(stayed["segment"], categories=SEGMENT_ORDER, ordered=True)
    return stayed


def segment_summary(segmented: pd.DataFrame) -> pd.DataFrame:
    if segmented.empty:
        return pd.DataFrame(columns=["segment", "guests", "total_spend", "average_spend"])
    summary = segmented.groupby("segment", observed=True).agg(
        guests=("guest_id", "count"),
        total_spend=("total_spend", "sum"),
        average_spend=("total_spend", "mean"),
        average_booking_value=("average_booking_value", "mean"),
        average_stays=("total_stays", "mean"),
        average_length_of_stay=("average_length_of_stay", "mean"),
        average_cancellation_rate=("cancellation_rate", "mean"),
    ).reset_index()
    summary["guest_share"] = summary["guests"] / summary["guests"].sum() * 100
    summary["revenue_share"] = summary["total_spend"] / summary["total_spend"].sum() * 100
    summary["description"] = summary["segment"].astype(str).map(SEGMENT_DESCRIPTIONS)
    summary["tone"] = summary["segment"].astype(str).map(SEGMENT_TONES)
    return summary


def customer_type_profile(bookings: pd.DataFrame, room_nights: pd.DataFrame) -> pd.DataFrame:
    if bookings.empty:
        return pd.DataFrame(columns=["customer_type", "bookings", "revenue"])
    booking_stats = bookings.groupby("customer_type").agg(
        total_requests=("booking_id", "count"),
        bookings=("is_confirmed", "sum"),
        cancellations=("is_cancelled", "sum"),
        average_length_of_stay=("number_of_nights", "mean"),
        average_lead_time=("lead_time_days", "mean"),
        average_party_size=("number_of_guests", "mean"),
    ).reset_index()
    booking_stats["bookings"] = booking_stats["bookings"].astype(int)
    staying_guests = (
        bookings.loc[bookings["is_confirmed"]].groupby("customer_type")["guest_id"].nunique()
    )
    booking_stats["guests"] = (
        booking_stats["customer_type"].map(staying_guests).fillna(0).astype(int)
    )
    booking_stats["cancellation_rate"] = (
        booking_stats["cancellations"] / booking_stats["total_requests"] * 100
    )

    if room_nights.empty:
        booking_stats["revenue"] = 0.0
        booking_stats["room_nights"] = 0
    else:
        revenue = room_nights.groupby("customer_type").agg(
            revenue=("nightly_rate", "sum"), room_nights=("nightly_rate", "size")
        )
        booking_stats = booking_stats.merge(
            revenue, left_on="customer_type", right_index=True, how="left"
        )
    booking_stats[["revenue", "room_nights"]] = booking_stats[["revenue", "room_nights"]].fillna(0)
    booking_stats["revenue_share"] = (
        booking_stats["revenue"] / booking_stats["revenue"].sum() * 100
        if booking_stats["revenue"].sum() else 0.0
    )
    booking_stats["revenue_per_booking"] = np.where(
        booking_stats["bookings"] > 0, booking_stats["revenue"] / booking_stats["bookings"], 0.0
    )
    booking_stats["adr"] = np.where(
        booking_stats["room_nights"] > 0,
        booking_stats["revenue"] / booking_stats["room_nights"], 0.0
    )
    return booking_stats.sort_values("revenue", ascending=False).reset_index(drop=True)


def repeat_guest_comparison(bookings: pd.DataFrame, room_nights: pd.DataFrame) -> pd.DataFrame:
    if bookings.empty:
        return pd.DataFrame(columns=["guest_group", "bookings", "revenue"])
    frame = bookings.copy()
    frame["guest_group"] = np.where(frame["repeat_guest"] == 1, "Returning guests", "First-time guests")
    stats = frame.groupby("guest_group").agg(
        total_requests=("booking_id", "count"),
        bookings=("is_confirmed", "sum"),
        cancellations=("is_cancelled", "sum"),
        average_length_of_stay=("number_of_nights", "mean"),
        average_lead_time=("lead_time_days", "mean"),
    ).reset_index()
    stats["bookings"] = stats["bookings"].astype(int)
    staying_guests = (
        frame.loc[frame["is_confirmed"]].groupby("guest_group")["guest_id"].nunique()
    )
    stats["guests"] = stats["guest_group"].map(staying_guests).fillna(0).astype(int)
    stats["cancellation_rate"] = stats["cancellations"] / stats["total_requests"] * 100

    if room_nights.empty:
        stats["revenue"] = 0.0
    else:
        nights = room_nights.copy()
        nights["guest_group"] = np.where(
            nights["repeat_guest"] == 1, "Returning guests", "First-time guests"
        )
        revenue = nights.groupby("guest_group")["nightly_rate"].sum()
        stats["revenue"] = stats["guest_group"].map(revenue).fillna(0.0)
    stats["revenue_per_booking"] = np.where(
        stats["bookings"] > 0, stats["revenue"] / stats["bookings"], 0.0
    )
    stats["revenue_per_guest"] = np.where(
        stats["guests"] > 0, stats["revenue"] / stats["guests"], 0.0
    )
    stats["bookings_per_guest"] = np.where(
        stats["guests"] > 0, stats["bookings"] / stats["guests"], 0.0
    )
    stats["revenue_share"] = (
        stats["revenue"] / stats["revenue"].sum() * 100 if stats["revenue"].sum() else 0.0
    )
    return stats


def guest_origin_profile(bookings: pd.DataFrame) -> pd.DataFrame:
    confirmed = bookings.loc[bookings["is_confirmed"]]
    if confirmed.empty:
        return pd.DataFrame(columns=["guest_region", "bookings", "share"])
    grouped = confirmed.groupby("guest_region").agg(
        bookings=("booking_id", "count"),
        revenue=("total_revenue", "sum"),
        average_length_of_stay=("number_of_nights", "mean"),
    ).reset_index()
    grouped["share"] = grouped["bookings"] / grouped["bookings"].sum() * 100
    return grouped.sort_values("bookings", ascending=False).reset_index(drop=True)


def preferred_choices(segmented: pd.DataFrame) -> pd.DataFrame:
    if segmented.empty:
        return pd.DataFrame(columns=["segment", "preferred_room_type", "preferred_booking_channel"])
    rows = []
    for segment, group in segmented.groupby("segment", observed=True):
        rows.append(
            {
                "segment": str(segment),
                "preferred_room_type": group["preferred_room_type"].mode().iat[0],
                "preferred_booking_channel": group["preferred_booking_channel"].mode().iat[0],
                "top_customer_type": group["customer_type"].mode().iat[0],
                "guests": int(len(group)),
            }
        )
    return pd.DataFrame(rows)

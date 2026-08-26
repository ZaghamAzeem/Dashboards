from __future__ import annotations

import math
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20260902
DATA_END = date(2026, 8, 31)
HISTORY_DAYS = 730
WARMUP_DAYS = 45
DATA_START = DATA_END - timedelta(days=HISTORY_DAYS - 1)
SIM_START = DATA_START - timedelta(days=WARMUP_DAYS)

HOTEL_NAME = "Grand Horizon Hotel"
DB_PATH = Path(__file__).resolve().parent / "hotel.db"

ROOM_TYPES = {
    "Standard Room": {
        "rooms": 48,
        "capacity": 2,
        "base_rate": 128.0,
        "avg_los": 2.2,
        "target_occupancy": 0.76,
        "description": "Comfortable double room with city view",
    },
    "Deluxe Room": {
        "rooms": 34,
        "capacity": 2,
        "base_rate": 178.0,
        "avg_los": 2.6,
        "target_occupancy": 0.79,
        "description": "Spacious room with premium bedding and lounge area",
    },
    "Executive Room": {
        "rooms": 18,
        "capacity": 2,
        "base_rate": 245.0,
        "avg_los": 2.4,
        "target_occupancy": 0.73,
        "description": "Business room with workspace and executive lounge access",
    },
    "Family Room": {
        "rooms": 14,
        "capacity": 4,
        "base_rate": 268.0,
        "avg_los": 3.4,
        "target_occupancy": 0.57,
        "description": "Two-bedroom layout designed for families",
    },
    "Suite": {
        "rooms": 6,
        "capacity": 3,
        "base_rate": 425.0,
        "avg_los": 3.0,
        "target_occupancy": 0.60,
        "description": "Top-floor suite with separate living room and terrace",
    },
}

CUSTOMER_TYPES = ["Business", "Leisure", "Couple", "Family", "Group"]

CUSTOMER_MIX = {
    "Standard Room": [0.34, 0.30, 0.15, 0.08, 0.13],
    "Deluxe Room": [0.29, 0.30, 0.26, 0.08, 0.07],
    "Executive Room": [0.58, 0.16, 0.16, 0.04, 0.06],
    "Family Room": [0.03, 0.18, 0.06, 0.61, 0.12],
    "Suite": [0.28, 0.22, 0.34, 0.10, 0.06],
}

WEEKDAY_PATTERN = {
    "Business": [1.36, 1.32, 1.26, 1.04, 0.54, 0.34, 0.74],
    "Leisure": [0.74, 0.70, 0.80, 1.00, 1.46, 1.56, 0.94],
    "Couple": [0.68, 0.64, 0.74, 0.94, 1.62, 1.52, 0.86],
    "Family": [0.78, 0.74, 0.84, 1.00, 1.48, 1.42, 0.94],
    "Group": [0.84, 0.90, 1.00, 1.12, 1.26, 1.18, 0.90],
}

MONTH_DEMAND = {
    1: 0.78, 2: 0.83, 3: 0.96, 4: 1.03, 5: 1.07, 6: 1.14,
    7: 1.23, 8: 1.18, 9: 1.06, 10: 1.00, 11: 0.89, 12: 0.97,
}

SPECIAL_PERIODS = [
    ("Harbour Lights Festival", (7, 10), (7, 19), 1.34, {"Leisure": 1.25, "Couple": 1.20}),
    ("Winter Gala Season", (12, 18), (12, 31), 1.30, {"Couple": 1.30, "Family": 1.20}),
    ("Spring Business Convention", (3, 16), (3, 22), 1.30, {"Business": 1.55, "Group": 1.35}),
    ("Autumn Food & Wine Week", (10, 8), (10, 14), 1.19, {"Couple": 1.30, "Leisure": 1.15}),
    ("City Marathon Weekend", (4, 24), (4, 27), 1.24, {"Group": 1.45, "Leisure": 1.20}),
]

PROMOTIONS = [
    ("Winter Escape Offer", (1, 8), (2, 20), 1.17, (0.14, 0.24)),
    ("Midweek Business Saver", (5, 5), (5, 25), 1.10, (0.09, 0.16)),
    ("Late Summer Getaway", (8, 20), (9, 10), 1.13, (0.11, 0.20)),
]

CHANNEL_MIX = {
    "Business": {"Corporate": 0.42, "Direct Website": 0.18, "Online Booking Platform": 0.18,
                 "Travel Agency": 0.10, "Phone": 0.10, "Walk-in": 0.02},
    "Leisure": {"Online Booking Platform": 0.40, "Direct Website": 0.26, "Travel Agency": 0.18,
                "Phone": 0.07, "Walk-in": 0.07, "Corporate": 0.02},
    "Couple": {"Online Booking Platform": 0.38, "Direct Website": 0.30, "Travel Agency": 0.16,
               "Phone": 0.07, "Walk-in": 0.08, "Corporate": 0.01},
    "Family": {"Online Booking Platform": 0.34, "Direct Website": 0.28, "Travel Agency": 0.24,
               "Phone": 0.08, "Walk-in": 0.05, "Corporate": 0.01},
    "Group": {"Travel Agency": 0.38, "Corporate": 0.22, "Phone": 0.16, "Direct Website": 0.14,
              "Online Booking Platform": 0.09, "Walk-in": 0.01},
}

CHANNEL_RATE_FACTOR = {
    "Direct Website": 1.00,
    "Walk-in": 1.07,
    "Travel Agency": 0.90,
    "Online Booking Platform": 0.92,
    "Corporate": 0.85,
    "Phone": 0.98,
}

CHANNEL_CANCEL_BASE = {
    "Direct Website": 0.070,
    "Walk-in": 0.010,
    "Travel Agency": 0.145,
    "Online Booking Platform": 0.245,
    "Corporate": 0.090,
    "Phone": 0.110,
}

CUSTOMER_CANCEL_FACTOR = {
    "Business": 0.88, "Leisure": 1.06, "Couple": 1.00, "Family": 1.12, "Group": 1.26,
}

LEAD_TIME_PARAMS = {
    "Business": (1.75, 0.95),
    "Leisure": (3.35, 0.85),
    "Couple": (3.20, 0.88),
    "Family": (3.60, 0.80),
    "Group": (4.05, 0.70),
}

LOS_WEIGHTS = {
    "Business": [0.30, 0.34, 0.20, 0.09, 0.04, 0.02, 0.01],
    "Leisure": [0.10, 0.22, 0.26, 0.18, 0.12, 0.07, 0.05],
    "Couple": [0.14, 0.30, 0.28, 0.15, 0.08, 0.03, 0.02],
    "Family": [0.05, 0.14, 0.24, 0.22, 0.16, 0.10, 0.09],
    "Group": [0.12, 0.28, 0.30, 0.16, 0.08, 0.04, 0.02],
}

REPEAT_PROPENSITY = {
    "Business": 0.40, "Leisure": 0.17, "Couple": 0.16, "Family": 0.21, "Group": 0.09,
}

REGION_MIX = {
    "Business": {"Domestic": 0.46, "Europe": 0.18, "North America": 0.14,
                 "Asia Pacific": 0.12, "Middle East": 0.07, "Other Regions": 0.03},
    "Leisure": {"Domestic": 0.34, "Europe": 0.22, "North America": 0.16,
                "Asia Pacific": 0.15, "Middle East": 0.08, "Other Regions": 0.05},
    "Couple": {"Domestic": 0.32, "Europe": 0.24, "North America": 0.17,
               "Asia Pacific": 0.14, "Middle East": 0.08, "Other Regions": 0.05},
    "Family": {"Domestic": 0.44, "Europe": 0.19, "North America": 0.13,
               "Asia Pacific": 0.12, "Middle East": 0.08, "Other Regions": 0.04},
    "Group": {"Domestic": 0.38, "Europe": 0.20, "North America": 0.14,
              "Asia Pacific": 0.16, "Middle East": 0.08, "Other Regions": 0.04},
}

TOTAL_ROOMS = sum(cfg["rooms"] for cfg in ROOM_TYPES.values())
DEMAND_CALIBRATION = 0.865


def _period_contains(day: date, start_md: tuple[int, int], end_md: tuple[int, int]) -> bool:
    start = date(day.year, *start_md)
    end = date(day.year, *end_md)
    if end < start:
        if day >= start:
            end = date(day.year + 1, *end_md)
        else:
            start = date(day.year - 1, *start_md)
    return start <= day <= end


def special_period_for(day: date):
    for name, start_md, end_md, lift, segment_lift in SPECIAL_PERIODS:
        if _period_contains(day, start_md, end_md):
            return name, lift, segment_lift
    return None, 1.0, {}


def promotion_for(day: date):
    for name, start_md, end_md, lift, discount_range in PROMOTIONS:
        if _period_contains(day, start_md, end_md):
            return name, lift, discount_range
    return None, 1.0, None


def demand_trend(day: date) -> float:
    elapsed = (day - SIM_START).days
    ramp = min(elapsed, 540)
    tail = max(elapsed - 540, 0)
    return (1.055 ** (ramp / 365.0)) * (1.015 ** (tail / 365.0))


def season_rate_factor(day: date) -> float:
    demand = MONTH_DEMAND[day.month]
    scaled = (demand - 0.78) / (1.23 - 0.78)
    smooth = 0.5 * (1 - math.cos(math.pi * min(max(scaled, 0.0), 1.0)))
    return 0.84 + 0.30 * smooth


def weekday_rate_factor(day: date) -> float:
    return [0.97, 0.96, 0.97, 1.00, 1.09, 1.10, 0.93][day.weekday()]


def build_calendar() -> pd.DataFrame:
    days = pd.date_range(SIM_START, DATA_END, freq="D")
    rows = []
    for ts in days:
        day = ts.date()
        event_name, event_lift, segment_lift = special_period_for(day)
        promo_name, promo_lift, discount_range = promotion_for(day)
        rows.append(
            {
                "day": day,
                "event_name": event_name,
                "event_lift": event_lift,
                "segment_lift": segment_lift,
                "promotion_name": promo_name,
                "promotion_lift": promo_lift,
                "discount_range": discount_range,
                "trend": demand_trend(day),
            }
        )
    return pd.DataFrame(rows)


def _cumulative(weights) -> np.ndarray:
    array = np.asarray(list(weights), dtype=float)
    return np.cumsum(array / array.sum())


CHANNEL_CHOICES = {
    ct: (list(mix.keys()), _cumulative(mix.values())) for ct, mix in CHANNEL_MIX.items()
}
REGION_CHOICES = {
    ct: (list(mix.keys()), _cumulative(mix.values())) for ct, mix in REGION_MIX.items()
}
LOS_CHOICES = {ct: _cumulative(weights) for ct, weights in LOS_WEIGHTS.items()}
REQUEST_CHOICES_NEW = _cumulative([0.52, 0.30, 0.13, 0.05])
REQUEST_CHOICES_REPEAT = _cumulative([0.38, 0.34, 0.19, 0.09])
GUEST_COUNT_CHOICES = {
    "Family": _cumulative([0.14, 0.34, 0.36, 0.16]),
    "Group": _cumulative([0.52, 0.32, 0.16]),
    "Other": _cumulative([0.34, 0.54, 0.12]),
}


def pick(rng, options, cumulative):
    return options[int(np.searchsorted(cumulative, rng.random()))]


def pick_index(rng, cumulative) -> int:
    return int(np.searchsorted(cumulative, rng.random()))


def sample_length_of_stay(rng, customer_type: str) -> int:
    nights = pick_index(rng, LOS_CHOICES[customer_type]) + 1
    if customer_type in ("Leisure", "Family") and rng.random() < 0.06:
        nights += int(rng.integers(1, 6))
    return nights


def sample_lead_time(rng, customer_type: str, channel: str) -> int:
    if channel == "Walk-in":
        return 0
    mu, sigma = LEAD_TIME_PARAMS[customer_type]
    if channel == "Corporate":
        mu -= 0.35
    elif channel == "Travel Agency":
        mu += 0.30
    elif channel == "Phone":
        mu -= 0.15
    lead = int(round(float(rng.lognormal(mu, sigma))))
    return int(np.clip(lead, 0, 330))


def sample_guest_count(rng, room_type: str, customer_type: str) -> int:
    capacity = ROOM_TYPES[room_type]["capacity"]
    if customer_type == "Business":
        guests = 1 if rng.random() < 0.82 else 2
    elif customer_type == "Couple":
        guests = 2
    elif customer_type == "Family":
        guests = pick_index(rng, GUEST_COUNT_CHOICES["Family"]) + 2
    elif customer_type == "Group":
        guests = pick_index(rng, GUEST_COUNT_CHOICES["Group"]) + 2
    else:
        guests = pick_index(rng, GUEST_COUNT_CHOICES["Other"]) + 1
    return int(min(guests, capacity + 1))


def cancellation_probability(rng, channel: str, customer_type: str, lead_time: int,
                             promotion_used: bool, demand_factor: float,
                             repeat_guest: bool) -> float:
    prob = CHANNEL_CANCEL_BASE[channel]
    prob *= CUSTOMER_CANCEL_FACTOR[customer_type]
    prob += 0.115 * min(lead_time / 110.0, 1.0)
    if promotion_used:
        prob *= 1.32
    if repeat_guest:
        prob *= 0.72
    prob *= 0.94 + 0.14 * min(max(demand_factor - 0.85, 0.0) / 0.55, 1.0)
    prob *= float(rng.normal(1.0, 0.05))
    return float(np.clip(prob, 0.005, 0.62))


def simulate_bookings(rng) -> pd.DataFrame:
    calendar = build_calendar()
    arrival_base = {
        name: cfg["rooms"] * cfg["target_occupancy"] / cfg["avg_los"] * DEMAND_CALIBRATION
        for name, cfg in ROOM_TYPES.items()
    }
    occupied = {name: {} for name in ROOM_TYPES}
    loyalty_pool: dict[str, list[str]] = {ct: [] for ct in CUSTOMER_TYPES}
    records = []
    guest_counter = 0

    for row in calendar.itertuples(index=False):
        day = row.day
        weekday = day.weekday()
        month_factor = MONTH_DEMAND[day.month]
        demand_factor = month_factor * row.event_lift * row.promotion_lift

        for room_type, cfg in ROOM_TYPES.items():
            mix = CUSTOMER_MIX[room_type]
            for customer_type, share in zip(CUSTOMER_TYPES, mix):
                segment_boost = row.segment_lift.get(customer_type, 1.0) if row.segment_lift else 1.0
                lam = (
                    arrival_base[room_type]
                    * share
                    * month_factor
                    * WEEKDAY_PATTERN[customer_type][weekday]
                    * row.event_lift
                    * segment_boost
                    * row.promotion_lift
                    * row.trend
                )
                arrivals = int(rng.poisson(max(lam, 0.0)))
                if arrivals == 0:
                    continue

                channels, channel_cum = CHANNEL_CHOICES[customer_type]
                regions, region_cum = REGION_CHOICES[customer_type]

                for _ in range(arrivals):
                    nights = sample_length_of_stay(rng, customer_type)
                    channel = pick(rng, channels, channel_cum)
                    lead_time = sample_lead_time(rng, customer_type, channel)

                    pool = loyalty_pool[customer_type]
                    repeat_guest = bool(pool) and rng.random() < REPEAT_PROPENSITY[customer_type]
                    if repeat_guest:
                        guest_id = pool[int(rng.integers(len(pool)))]
                    else:
                        guest_counter += 1
                        guest_id = f"GUEST-{guest_counter:05d}"

                    cancel_prob = cancellation_probability(
                        rng, channel, customer_type, lead_time,
                        row.promotion_name is not None, demand_factor, repeat_guest,
                    )
                    is_cancelled = bool(rng.random() < cancel_prob)

                    stay_days = [day + timedelta(days=i) for i in range(nights)]
                    if not is_cancelled:
                        capacity = cfg["rooms"]
                        if any(occupied[room_type].get(d, 0) >= capacity for d in stay_days):
                            continue
                        for d in stay_days:
                            occupied[room_type][d] = occupied[room_type].get(d, 0) + 1

                    fill_ratio = occupied[room_type].get(day, 0) / cfg["rooms"]
                    pressure = 0.95 + 0.18 * min(fill_ratio, 1.0)
                    los_factor = max(1.0 - 0.012 * (nights - 1), 0.93)
                    nightly = (
                        cfg["base_rate"]
                        * season_rate_factor(day)
                        * weekday_rate_factor(day)
                        * CHANNEL_RATE_FACTOR[channel]
                        * los_factor
                        * pressure
                        * (1.08 if row.event_name else 1.0)
                        * float(rng.normal(1.0, 0.045))
                    )

                    discount = 0.0
                    promotion_used = False
                    if row.discount_range is not None and rng.random() < 0.78:
                        discount = float(rng.uniform(*row.discount_range))
                        promotion_used = True
                    elif rng.random() < 0.07:
                        discount = float(rng.uniform(0.04, 0.10))
                    if repeat_guest:
                        discount = min(discount + 0.03, 0.35)

                    nightly_rate = round(max(nightly * (1.0 - discount), 35.0), 2)
                    booking_value = round(nightly_rate * nights, 2)

                    if not is_cancelled:
                        loyalty_pool[customer_type].append(guest_id)

                    special_requests = pick_index(
                        rng, REQUEST_CHOICES_REPEAT if repeat_guest else REQUEST_CHOICES_NEW
                    )

                    records.append(
                        {
                            "booking_date": day - timedelta(days=lead_time),
                            "check_in_date": day,
                            "check_out_date": day + timedelta(days=nights),
                            "room_type": room_type,
                            "customer_type": customer_type,
                            "booking_channel": channel,
                            "guest_id": guest_id,
                            "guest_region": pick(rng, regions, region_cum),
                            "number_of_guests": sample_guest_count(rng, room_type, customer_type),
                            "number_of_nights": nights,
                            "lead_time_days": lead_time,
                            "nightly_rate": nightly_rate,
                            "discount_percent": round(discount * 100, 1),
                            "booking_value": booking_value,
                            "total_revenue": 0.0 if is_cancelled else booking_value,
                            "is_cancelled": int(is_cancelled),
                            "promotion_used": int(promotion_used),
                            "repeat_guest": int(repeat_guest),
                            "special_requests": special_requests,
                            "stay_period": row.event_name or row.promotion_name or "Standard Period",
                        }
                    )

    bookings = pd.DataFrame(records)
    keep = (bookings["check_in_date"] >= DATA_START) | (
        (bookings["is_cancelled"] == 0) & (bookings["check_out_date"] > DATA_START)
    )
    bookings = bookings.loc[keep].copy()
    bookings = bookings.sort_values(["check_in_date", "room_type"]).reset_index(drop=True)
    bookings.insert(0, "booking_id", [f"BK-{i + 1:06d}" for i in range(len(bookings))])
    for column in ("booking_date", "check_in_date", "check_out_date"):
        bookings[column] = pd.to_datetime(bookings[column]).dt.strftime("%Y-%m-%d")
    return bookings


def explode_room_nights(bookings: pd.DataFrame) -> pd.DataFrame:
    confirmed = bookings.loc[bookings["is_cancelled"] == 0].copy()
    confirmed["check_in_date"] = pd.to_datetime(confirmed["check_in_date"])
    nights = confirmed.loc[confirmed.index.repeat(confirmed["number_of_nights"])].copy()
    offsets = nights.groupby(level=0).cumcount()
    nights["stay_date"] = nights["check_in_date"] + pd.to_timedelta(offsets, unit="D")
    window = (nights["stay_date"] >= pd.Timestamp(DATA_START)) & (
        nights["stay_date"] <= pd.Timestamp(DATA_END)
    )
    return nights.loc[window, ["stay_date", "room_type", "customer_type", "booking_channel",
                               "nightly_rate", "number_of_guests"]].reset_index(drop=True)


def build_daily_metrics(bookings: pd.DataFrame, room_nights: pd.DataFrame) -> pd.DataFrame:
    index = pd.date_range(DATA_START, DATA_END, freq="D")
    grouped = room_nights.groupby("stay_date").agg(
        rooms_sold=("nightly_rate", "size"),
        room_revenue=("nightly_rate", "sum"),
        guests_in_house=("number_of_guests", "sum"),
    )
    metrics = grouped.reindex(index, fill_value=0.0)
    metrics.index.name = "stay_date"

    confirmed = bookings.loc[bookings["is_cancelled"] == 0]
    arrivals = pd.to_datetime(confirmed["check_in_date"]).value_counts().reindex(index, fill_value=0)
    departures = pd.to_datetime(confirmed["check_out_date"]).value_counts().reindex(index, fill_value=0)
    cancellations = (
        pd.to_datetime(bookings.loc[bookings["is_cancelled"] == 1, "check_in_date"])
        .value_counts()
        .reindex(index, fill_value=0)
    )

    metrics["rooms_available"] = TOTAL_ROOMS
    metrics["arrivals"] = arrivals.values
    metrics["departures"] = departures.values
    metrics["cancelled_arrivals"] = cancellations.values
    metrics["occupancy_rate"] = (metrics["rooms_sold"] / TOTAL_ROOMS * 100).round(2)
    metrics["adr"] = np.where(
        metrics["rooms_sold"] > 0, metrics["room_revenue"] / metrics["rooms_sold"].replace(0, np.nan), 0.0
    )
    metrics["adr"] = metrics["adr"].fillna(0.0).round(2)
    metrics["revpar"] = (metrics["room_revenue"] / TOTAL_ROOMS).round(2)
    metrics["room_revenue"] = metrics["room_revenue"].round(2)

    period_names, promo_flags, event_flags = [], [], []
    for ts in index:
        day = ts.date()
        event_name, _, _ = special_period_for(day)
        promo_name, _, _ = promotion_for(day)
        period_names.append(event_name or promo_name or "Standard Period")
        promo_flags.append(int(promo_name is not None))
        event_flags.append(int(event_name is not None))
    metrics["period_name"] = period_names
    metrics["is_promotion"] = promo_flags
    metrics["is_special_period"] = event_flags

    metrics = metrics.reset_index()
    metrics["stay_date"] = metrics["stay_date"].dt.strftime("%Y-%m-%d")
    metrics["rooms_sold"] = metrics["rooms_sold"].astype(int)
    metrics["guests_in_house"] = metrics["guests_in_house"].astype(int)
    columns = ["stay_date", "rooms_available", "rooms_sold", "occupancy_rate", "room_revenue",
               "adr", "revpar", "arrivals", "departures", "cancelled_arrivals",
               "guests_in_house", "period_name", "is_promotion", "is_special_period"]
    return metrics[columns]


def build_guests(bookings: pd.DataFrame) -> pd.DataFrame:
    data = bookings.copy()
    data["check_in_date"] = pd.to_datetime(data["check_in_date"])
    confirmed = data.loc[data["is_cancelled"] == 0]

    stays = confirmed.groupby("guest_id").agg(
        total_stays=("booking_id", "count"),
        total_nights=("number_of_nights", "sum"),
        total_spend=("total_revenue", "sum"),
        average_length_of_stay=("number_of_nights", "mean"),
        first_stay_date=("check_in_date", "min"),
        last_stay_date=("check_in_date", "max"),
    )
    all_bookings = data.groupby("guest_id").agg(
        total_bookings=("booking_id", "count"),
        cancelled_bookings=("is_cancelled", "sum"),
    )

    guests = all_bookings.join(stays, how="left")
    guests["total_stays"] = guests["total_stays"].fillna(0).astype(int)
    guests["total_nights"] = guests["total_nights"].fillna(0).astype(int)
    guests["total_spend"] = guests["total_spend"].fillna(0.0).round(2)
    guests["average_length_of_stay"] = guests["average_length_of_stay"].fillna(0.0).round(2)
    guests["average_booking_value"] = np.where(
        guests["total_stays"] > 0, guests["total_spend"] / guests["total_stays"].replace(0, np.nan), 0.0
    )
    guests["average_booking_value"] = pd.Series(
        guests["average_booking_value"], index=guests.index
    ).fillna(0.0).round(2)
    guests["cancellation_rate"] = (
        guests["cancelled_bookings"] / guests["total_bookings"] * 100
    ).round(2)
    guests["repeat_guest"] = (guests["total_stays"] > 1).astype(int)

    modes = data.groupby("guest_id").agg(
        customer_type=("customer_type", lambda s: s.mode().iat[0]),
        preferred_room_type=("room_type", lambda s: s.mode().iat[0]),
        preferred_booking_channel=("booking_channel", lambda s: s.mode().iat[0]),
        guest_region=("guest_region", lambda s: s.mode().iat[0]),
    )
    guests = guests.join(modes)

    span_days = (guests["last_stay_date"] - guests["first_stay_date"]).dt.days.fillna(0)
    guests["booking_frequency_per_year"] = np.where(
        span_days > 0, guests["total_stays"] / (span_days / 365.0), guests["total_stays"].astype(float)
    ).round(2)
    reference = pd.Timestamp(DATA_END)
    guests["days_since_last_stay"] = (reference - guests["last_stay_date"]).dt.days
    guests["days_since_last_stay"] = guests["days_since_last_stay"].fillna(-1).astype(int)
    for column in ("first_stay_date", "last_stay_date"):
        guests[column] = guests[column].dt.strftime("%Y-%m-%d").fillna("")

    guests = guests.reset_index()
    columns = ["guest_id", "customer_type", "guest_region", "total_bookings", "total_stays",
               "cancelled_bookings", "cancellation_rate", "total_nights", "total_spend",
               "average_booking_value", "average_length_of_stay", "booking_frequency_per_year",
               "preferred_room_type", "preferred_booking_channel", "repeat_guest",
               "first_stay_date", "last_stay_date", "days_since_last_stay"]
    return guests[columns]


def build_rooms() -> pd.DataFrame:
    rows = []
    for name, cfg in ROOM_TYPES.items():
        rows.append(
            {
                "room_type": name,
                "rooms_available": cfg["rooms"],
                "max_occupancy": cfg["capacity"],
                "base_rate": cfg["base_rate"],
                "description": cfg["description"],
            }
        )
    return pd.DataFrame(rows)


def write_database(bookings: pd.DataFrame, rooms: pd.DataFrame, guests: pd.DataFrame,
                   daily_metrics: pd.DataFrame) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    with sqlite3.connect(DB_PATH) as connection:
        bookings.to_sql("bookings", connection, index=False)
        rooms.to_sql("rooms", connection, index=False)
        guests.to_sql("guests", connection, index=False)
        daily_metrics.to_sql("daily_metrics", connection, index=False)
        cursor = connection.cursor()
        cursor.execute("CREATE INDEX idx_bookings_check_in ON bookings(check_in_date)")
        cursor.execute("CREATE INDEX idx_bookings_room_type ON bookings(room_type)")
        cursor.execute("CREATE INDEX idx_daily_metrics_date ON daily_metrics(stay_date)")
        cursor.execute("CREATE INDEX idx_guests_id ON guests(guest_id)")
        connection.commit()


def validation_report(bookings: pd.DataFrame, guests: pd.DataFrame,
                      daily_metrics: pd.DataFrame) -> list[str]:
    confirmed = bookings.loc[bookings["is_cancelled"] == 0]
    lines = [
        f"Hotel                : {HOTEL_NAME} ({TOTAL_ROOMS} rooms)",
        f"Reporting window     : {DATA_START} to {DATA_END} ({len(daily_metrics)} days)",
        f"Bookings             : {len(bookings):,} ({len(confirmed):,} confirmed)",
        f"Guests               : {len(guests):,} ({int(guests['repeat_guest'].sum()):,} repeat)",
        f"Cancellation rate    : {bookings['is_cancelled'].mean() * 100:.1f}%",
        f"Total room revenue   : ${confirmed['total_revenue'].sum():,.0f}",
        f"Average occupancy    : {daily_metrics['occupancy_rate'].mean():.1f}%",
        f"Peak occupancy       : {daily_metrics['occupancy_rate'].max():.1f}%",
        f"Lowest occupancy     : {daily_metrics['occupancy_rate'].min():.1f}%",
        f"Average daily rate   : ${daily_metrics.loc[daily_metrics['rooms_sold'] > 0, 'adr'].mean():.2f}",
        f"Average RevPAR       : ${daily_metrics['revpar'].mean():.2f}",
        f"Average stay length  : {confirmed['number_of_nights'].mean():.2f} nights",
        f"Duplicate booking ids: {int(bookings['booking_id'].duplicated().sum())}",
        f"Duplicate guest ids  : {int(guests['guest_id'].duplicated().sum())}",
        f"Missing values       : {int(bookings.isna().sum().sum() + guests.isna().sum().sum() + daily_metrics.isna().sum().sum())}",
        f"Negative revenue rows: {int((bookings['total_revenue'] < 0).sum())}",
    ]
    room_share = confirmed["room_type"].value_counts(normalize=True) * 100
    lines.append("Room type share      : " + ", ".join(f"{k} {v:.1f}%" for k, v in room_share.items()))
    channel_cancel = bookings.groupby("booking_channel")["is_cancelled"].mean().sort_values() * 100
    lines.append("Cancellation by channel: " + ", ".join(f"{k} {v:.1f}%" for k, v in channel_cancel.items()))
    return lines


def generate() -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(SEED)
    bookings = simulate_bookings(rng)
    room_nights = explode_room_nights(bookings)
    daily_metrics = build_daily_metrics(bookings, room_nights)
    guests = build_guests(bookings)
    rooms = build_rooms()
    write_database(bookings, rooms, guests, daily_metrics)
    return {
        "bookings": bookings,
        "rooms": rooms,
        "guests": guests,
        "daily_metrics": daily_metrics,
    }


def main() -> None:
    tables = generate()
    print(f"Synthetic hotel dataset written to {DB_PATH}")
    print("-" * 72)
    for line in validation_report(tables["bookings"], tables["guests"], tables["daily_metrics"]):
        print(line)
    print("-" * 72)
    for name, frame in tables.items():
        print(f"{name:<15} {len(frame):>8,} rows  x  {len(frame.columns)} columns")


if __name__ == "__main__":
    main()

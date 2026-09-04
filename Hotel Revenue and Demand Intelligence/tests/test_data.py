import sqlite3

import pandas as pd

from src.data_loader import DB_PATH, REQUIRED_TABLES

BOOKING_COLUMNS = {
    "booking_id", "booking_date", "check_in_date", "check_out_date", "room_type",
    "customer_type", "booking_channel", "guest_id", "guest_region", "number_of_guests",
    "number_of_nights", "lead_time_days", "nightly_rate", "discount_percent",
    "booking_value", "total_revenue", "is_cancelled", "promotion_used", "repeat_guest",
    "special_requests", "stay_period",
}

GUEST_COLUMNS = {
    "guest_id", "customer_type", "total_bookings", "total_stays", "total_spend",
    "average_booking_value", "average_length_of_stay", "preferred_room_type",
    "preferred_booking_channel", "cancellation_rate", "repeat_guest",
}

DAILY_COLUMNS = {
    "stay_date", "rooms_available", "rooms_sold", "occupancy_rate", "room_revenue",
    "adr", "revpar", "arrivals", "departures", "guests_in_house",
}


def test_database_file_exists():
    assert DB_PATH.exists(), f"expected the hotel dataset at {DB_PATH}"


def test_required_tables_present():
    with sqlite3.connect(DB_PATH) as connection:
        names = pd.read_sql(
            "SELECT name FROM sqlite_master WHERE type='table'", connection
        )["name"].tolist()
    for table in REQUIRED_TABLES:
        assert table in names


def test_expected_columns_present(bookings, guests, daily_metrics):
    assert BOOKING_COLUMNS.issubset(set(bookings.columns))
    assert GUEST_COLUMNS.issubset(set(guests.columns))
    assert DAILY_COLUMNS.issubset(set(daily_metrics.columns))


def test_tables_are_populated(bookings, guests, daily_metrics, rooms):
    assert len(bookings) > 1000
    assert len(guests) > 100
    assert len(daily_metrics) >= 365
    assert len(rooms) >= 3


def test_identifiers_are_unique(bookings, guests):
    assert not bookings["booking_id"].duplicated().any()
    assert not guests["guest_id"].duplicated().any()


def test_no_missing_values(bookings, guests, daily_metrics):
    assert bookings.isna().sum().sum() == 0
    assert guests.drop(columns=["first_stay_date", "last_stay_date"]).isna().sum().sum() == 0
    assert daily_metrics.isna().sum().sum() == 0


def test_revenue_is_never_negative(bookings, guests, daily_metrics):
    assert (bookings["total_revenue"] >= 0).all()
    assert (bookings["booking_value"] >= 0).all()
    assert (bookings["nightly_rate"] > 0).all()
    assert (guests["total_spend"] >= 0).all()
    assert (daily_metrics["room_revenue"] >= 0).all()


def test_cancelled_bookings_earn_nothing(bookings):
    cancelled = bookings.loc[bookings["is_cancelled"] == 1]
    assert (cancelled["total_revenue"] == 0).all()
    confirmed = bookings.loc[bookings["is_cancelled"] == 0]
    assert (confirmed["total_revenue"] > 0).all()


def test_dates_are_valid(bookings):
    assert (bookings["check_out_date"] > bookings["check_in_date"]).all()
    assert (bookings["booking_date"] <= bookings["check_in_date"]).all()
    nights = (bookings["check_out_date"] - bookings["check_in_date"]).dt.days
    assert (nights == bookings["number_of_nights"]).all()
    assert (bookings["number_of_nights"] > 0).all()


def test_lead_time_matches_dates(bookings):
    computed = (bookings["check_in_date"] - bookings["booking_date"]).dt.days
    assert (computed == bookings["lead_time_days"]).all()
    assert (bookings["lead_time_days"] >= 0).all()


def test_daily_metrics_stay_within_capacity(daily_metrics, hotel_capacity):
    assert (daily_metrics["rooms_available"] == hotel_capacity).all()
    assert (daily_metrics["rooms_sold"] <= hotel_capacity).all()
    assert (daily_metrics["rooms_sold"] >= 0).all()
    assert daily_metrics["occupancy_rate"].between(0, 100).all()


def test_daily_metrics_cover_a_continuous_period(daily_metrics):
    dates = daily_metrics["stay_date"].sort_values()
    gaps = dates.diff().dropna().dt.days.unique()
    assert set(gaps) == {1}


def test_room_inventory_is_sensible(rooms):
    assert (rooms["rooms_available"] > 0).all()
    assert (rooms["base_rate"] > 0).all()
    assert (rooms["max_occupancy"] >= 1).all()
    assert not rooms["room_type"].duplicated().any()


def test_room_nights_reconcile_with_daily_metrics(room_nights, daily_metrics):
    rebuilt = room_nights.groupby("stay_date").size()
    reference = daily_metrics.set_index("stay_date")["rooms_sold"]
    aligned = rebuilt.reindex(reference.index, fill_value=0)
    assert (aligned == reference).all()


def test_revenue_reconciles_between_tables(room_nights, daily_metrics):
    rebuilt = room_nights.groupby("stay_date")["nightly_rate"].sum()
    reference = daily_metrics.set_index("stay_date")["room_revenue"]
    aligned = rebuilt.reindex(reference.index, fill_value=0.0)
    assert ((aligned - reference).abs() < 0.5).all()


def test_categorical_values_are_from_a_known_set(bookings, rooms):
    assert set(bookings["room_type"]).issubset(set(rooms["room_type"]))
    assert set(bookings["is_cancelled"]).issubset({0, 1})
    assert set(bookings["repeat_guest"]).issubset({0, 1})
    assert set(bookings["promotion_used"]).issubset({0, 1})
    assert bookings["discount_percent"].between(0, 60).all()


def test_distributions_are_realistic(bookings, daily_metrics):
    cancellation_rate = bookings["is_cancelled"].mean()
    assert 0.05 < cancellation_rate < 0.40
    assert 55 < daily_metrics["occupancy_rate"].mean() < 95
    assert bookings["number_of_nights"].mean() < 8
    channel_rates = bookings.groupby("booking_channel")["is_cancelled"].mean()
    assert channel_rates.max() > channel_rates.min()


def test_guest_totals_agree_with_bookings(bookings, guests):
    confirmed = bookings.loc[bookings["is_cancelled"] == 0]
    assert abs(confirmed["total_revenue"].sum() - guests["total_spend"].sum()) < 1.0
    assert guests["total_bookings"].sum() == len(bookings)
    assert guests["cancellation_rate"].between(0, 100).all()

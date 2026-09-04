import pytest

from src import analytics
from src.customer_analysis import (
    SEGMENT_ORDER,
    customer_type_profile,
    repeat_guest_comparison,
    segment_guests,
    segment_summary,
)


@pytest.fixture(scope="module")
def window(daily_metrics):
    return daily_metrics["stay_date"].min(), daily_metrics["stay_date"].max()


@pytest.fixture(scope="module")
def kpis(bookings, room_nights, hotel_capacity, daily_metrics):
    return analytics.compute_kpis(bookings, room_nights, hotel_capacity, len(daily_metrics))


def test_kpis_are_within_valid_bounds(kpis):
    assert kpis["revenue"] > 0
    assert 0 <= kpis["occupancy_rate"] <= 100
    assert 0 <= kpis["cancellation_rate"] <= 100
    assert kpis["adr"] > 0
    assert kpis["revpar"] >= 0
    assert kpis["revpar"] <= kpis["adr"]
    assert kpis["bookings"] <= kpis["total_requests"]
    assert kpis["average_length_of_stay"] > 0


def test_kpis_are_internally_consistent(kpis):
    assert kpis["adr"] == pytest.approx(kpis["revenue"] / kpis["rooms_sold"], rel=1e-6)
    assert kpis["revpar"] == pytest.approx(kpis["revenue"] / kpis["rooms_available"], rel=1e-6)
    assert kpis["occupancy_rate"] == pytest.approx(
        kpis["rooms_sold"] / kpis["rooms_available"] * 100, rel=1e-6
    )


def test_kpis_handle_an_empty_selection(bookings, room_nights, hotel_capacity):
    empty_bookings = bookings.iloc[0:0]
    empty_nights = room_nights.iloc[0:0]
    result = analytics.compute_kpis(empty_bookings, empty_nights, hotel_capacity, 30)
    assert result["revenue"] == 0
    assert result["occupancy_rate"] == 0
    assert result["cancellation_rate"] == 0
    assert result["adr"] == 0


def test_percent_change_handles_a_zero_baseline():
    assert analytics.percent_change(120, 100) == pytest.approx(20)
    assert analytics.percent_change(80, 100) == pytest.approx(-20)
    assert analytics.percent_change(50, 0) is None


def test_revenue_by_dimension_shares_add_up(room_nights):
    for dimension in ("room_type", "booking_channel", "customer_type"):
        breakdown = analytics.revenue_by_dimension(room_nights, dimension)
        assert not breakdown.empty
        assert breakdown["revenue_share"].sum() == pytest.approx(100, abs=0.01)
        assert (breakdown["revenue"] >= 0).all()
        assert (breakdown["adr"] > 0).all()
        assert breakdown["revenue"].is_monotonic_decreasing


def test_daily_performance_covers_every_night(room_nights, hotel_capacity, window):
    start, end = window
    daily = analytics.daily_performance(room_nights, hotel_capacity, start, end)
    assert len(daily) == (end - start).days + 1
    assert daily["occupancy_rate"].between(0, 100).all()
    assert (daily["revenue"] >= 0).all()
    assert (daily["adr"] >= 0).all()


def test_monthly_and_weekday_views(room_nights, hotel_capacity, window):
    start, end = window
    daily = analytics.daily_performance(room_nights, hotel_capacity, start, end)
    monthly = analytics.monthly_performance(daily)
    assert monthly["revenue"].sum() == pytest.approx(daily["revenue"].sum(), rel=1e-6)
    assert (monthly["days"] > 0).all()

    weekday = analytics.weekday_performance(daily)
    assert list(weekday["weekday"]) == analytics.WEEKDAY_ORDER
    assert weekday["occupancy_rate"].between(0, 100).all()


def test_room_performance_is_bounded_and_ranked(bookings, room_nights, rooms, daily_metrics):
    performance = analytics.room_performance(
        bookings, room_nights, rooms, len(daily_metrics)
    )
    assert len(performance) == len(rooms)
    assert performance["occupancy_rate"].between(0, 100).all()
    assert performance["cancellation_rate"].between(0, 100).all()
    assert (performance["revpar"] >= 0).all()
    assert (performance["revpar"] <= performance["adr"]).all()
    assert performance["revenue_share"].sum() == pytest.approx(100, abs=0.01)
    assert performance["performance_score"].is_monotonic_decreasing
    assert set(performance["status"]).issubset(
        {"Strong Performer", "Performing Well", "Needs Attention"}
    )


def test_room_performance_handles_no_activity(bookings, room_nights, rooms):
    empty = analytics.room_performance(
        bookings.iloc[0:0], room_nights.iloc[0:0], rooms, 30
    )
    assert empty.empty


def test_cancellation_breakdown_is_bounded(bookings):
    for dimension in ("booking_channel", "customer_type", "room_type", "lead_time_group"):
        breakdown = analytics.cancellation_breakdown(bookings, dimension)
        assert not breakdown.empty
        assert breakdown["cancellation_rate"].between(0, 100).all()
        assert (breakdown["cancellations"] <= breakdown["total"]).all()
        assert (breakdown["lost_value"] >= 0).all()
        assert breakdown["cancellation_rate"].is_monotonic_decreasing


def test_cancellation_summary_matches_the_record(bookings):
    summary = analytics.cancellation_summary(bookings)
    cancelled = bookings.loc[bookings["is_cancelled"] == 1]
    assert summary["cancelled_bookings"] == len(cancelled)
    assert 0 <= summary["cancellation_rate"] <= 100
    assert summary["lost_value"] >= 0


def test_booking_volume_totals_match(bookings):
    volume = analytics.booking_volume(bookings, "M")
    assert volume["bookings"].sum() == int(bookings["is_confirmed"].sum())
    assert volume["cancellations"].sum() == int(bookings["is_cancelled"].sum())


def test_lead_time_profile_shares_add_up(bookings):
    profile = analytics.booking_lead_time_profile(bookings)
    assert profile["share"].sum() == pytest.approx(100, abs=0.01)


def test_guest_segments_cover_every_staying_guest(guests):
    segmented = segment_guests(guests)
    stayed = guests.loc[guests["total_stays"] > 0]
    assert len(segmented) == len(stayed)
    assert set(segmented["segment"].astype(str)).issubset(set(SEGMENT_ORDER))

    summary = segment_summary(segmented)
    assert summary["guests"].sum() == len(stayed)
    assert summary["guest_share"].sum() == pytest.approx(100, abs=0.01)
    assert summary["revenue_share"].sum() == pytest.approx(100, abs=0.01)
    assert (summary["average_spend"] > 0).all()


def test_customer_profile_is_consistent(bookings, room_nights):
    profile = customer_type_profile(bookings, room_nights)
    assert profile["bookings"].sum() == int(bookings["is_confirmed"].sum())
    assert profile["revenue_share"].sum() == pytest.approx(100, abs=0.01)
    assert (profile["guests"] <= profile["bookings"]).all()
    assert profile["cancellation_rate"].between(0, 100).all()


def test_repeat_guest_comparison_splits_all_bookings(bookings, room_nights):
    comparison = repeat_guest_comparison(bookings, room_nights)
    assert len(comparison) == 2
    assert comparison["total_requests"].sum() == len(bookings)
    assert comparison["revenue"].sum() == pytest.approx(room_nights["nightly_rate"].sum(), rel=1e-6)
    assert (comparison["revenue_per_guest"] > 0).all()


def test_revenue_trend_direction_reports_a_basis(room_nights, hotel_capacity, window):
    start, end = window
    daily = analytics.daily_performance(room_nights, hotel_capacity, start, end)
    trend = analytics.revenue_trend_direction(analytics.monthly_performance(daily))
    assert trend["direction"] in {"growing", "softening", "steady"}
    assert trend["basis"] in {"year_on_year", "sequential", "none"}
    if trend["change"] is not None:
        assert trend["recent"] > 0
        assert trend["previous"] > 0

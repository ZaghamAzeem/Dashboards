from __future__ import annotations

import pandas as pd
import pytest

from dashboard import analytics


def test_totals_match_the_underlying_rows(sample_sales):
    summary = analytics.totals(sample_sales)
    assert summary["revenue"] == pytest.approx(sample_sales["revenue"].sum())
    assert summary["units"] == sample_sales["units_sold"].sum()
    assert summary["active_days"] == sample_sales["sale_date"].nunique()


def test_totals_handle_an_empty_selection(sample_sales):
    empty = sample_sales.iloc[0:0]
    assert analytics.totals(empty) == {
        "revenue": 0.0,
        "units": 0,
        "orders": 0,
        "active_days": 0,
    }


def test_slice_by_dates_keeps_only_the_window(sample_sales, latest_day):
    start = analytics.period_start(latest_day, 7)
    window = analytics.slice_by_dates(sample_sales, start, latest_day)
    assert window["sale_date"].min() >= start
    assert window["sale_date"].max() == latest_day
    assert window["sale_date"].nunique() == 7


def test_slice_by_category_filters_one_sport(sample_sales):
    cricket = analytics.slice_by_category(sample_sales, "Cricket")
    assert set(cricket["category"]) == {"Cricket"}
    everything = analytics.slice_by_category(sample_sales, analytics.ALL_SPORTS)
    assert len(everything) == len(sample_sales)


def test_category_shares_add_up_to_one_hundred(sample_sales):
    performance = analytics.category_performance(sample_sales)
    assert performance["share"].sum() == pytest.approx(100.0)
    assert performance["revenue"].is_monotonic_decreasing


def test_category_totals_match_the_raw_sales(sample_sales):
    performance = analytics.category_performance(sample_sales)
    expected = sample_sales.groupby("category")["units_sold"].sum()
    for _, row in performance.iterrows():
        assert row["units"] == expected[row["category"]]


def test_product_leaderboard_is_ranked_by_units(sample_sales):
    leaderboard = analytics.product_leaderboard(sample_sales)
    assert list(leaderboard["rank"]) == list(range(1, len(leaderboard) + 1))
    assert leaderboard["units"].is_monotonic_decreasing
    assert leaderboard.iloc[0]["product_name"] == "Hard Ball Cricket Bat"


def test_product_leaderboard_can_be_trimmed(sample_sales):
    assert len(analytics.product_leaderboard(sample_sales, top_n=2)) == 2


def test_sales_by_grain_preserves_the_total(sample_sales):
    total = sample_sales["revenue"].sum()
    for grain in analytics.GRAIN_CHOICES:
        grouped = analytics.sales_by_grain(sample_sales, grain)
        assert grouped["revenue"].sum() == pytest.approx(total)
        assert not grouped.empty


def test_sales_by_grain_reduces_the_number_of_points(sample_sales):
    daily = analytics.sales_by_grain(sample_sales, "Daily")
    weekly = analytics.sales_by_grain(sample_sales, "Weekly")
    monthly = analytics.sales_by_grain(sample_sales, "Monthly")
    assert len(daily) > len(weekly) > len(monthly)


def test_weekday_pattern_covers_every_day_in_order(sample_sales):
    pattern = analytics.weekday_pattern(sample_sales)
    assert list(pattern["weekday"]) == analytics.WEEKDAY_ORDER
    assert pattern["average_revenue"].idxmax() in (5, 6)


def test_monthly_seasonality_uses_a_daily_average(sample_sales):
    seasonality = analytics.monthly_seasonality(sample_sales)
    assert not seasonality.empty
    assert (seasonality["average_units"] >= 0).all()
    assert set(seasonality["category"]).issubset(set(sample_sales["category"]))


def test_product_momentum_compares_two_equal_windows(sample_products, latest_day):
    calendar = pd.date_range(end=latest_day, periods=56, freq="D")
    rows = []
    for position, day in enumerate(calendar):
        units = 10 if position >= 28 else 5
        rows.append(
            {
                "transaction_id": position,
                "sale_date": day,
                "product_id": "P1",
                "product_name": "Hard Ball Cricket Bat",
                "category": "Cricket",
                "units_sold": units,
                "unit_price": 8000.0,
                "discount_pct": 0.0,
                "revenue": units * 8000.0,
            }
        )
    momentum = analytics.product_momentum(pd.DataFrame(rows), latest_day, window=28)
    row = momentum.iloc[0]
    assert row["recent"] == 280
    assert row["previous"] == 140
    assert row["change_pct"] == pytest.approx(100.0)


def test_rising_products_ignores_quiet_items(sample_sales, latest_day):
    rising = analytics.rising_products(sample_sales, latest_day, minimum_recent=15)
    assert (rising["recent"] >= 15).all()
    assert (rising["change_pct"] > 10).all()


def test_slow_movers_returns_the_quietest_products(sample_sales, latest_day):
    movers = analytics.slow_movers(sample_sales, latest_day, window=90, bottom_n=2)
    assert len(movers) == 2
    assert movers.iloc[0]["product_name"] == "Tennis Net"
    assert movers["units"].is_monotonic_increasing


def test_overall_momentum_reports_both_windows(sample_sales, latest_day):
    momentum = analytics.overall_momentum(sample_sales, latest_day, window=14)
    assert momentum["window"] == 14
    assert momentum["recent_revenue"] > 0
    assert momentum["previous_revenue"] > 0
    assert momentum["recent_start"] > momentum["previous_end"]


def test_recent_daily_average_is_per_day(sample_sales, latest_day):
    averages = analytics.recent_daily_average(sample_sales, latest_day, window=28)
    window = analytics.slice_by_dates(
        sample_sales, analytics.period_start(latest_day, 28), latest_day
    )
    expected = window.loc[window["product_id"] == "P2", "units_sold"].sum() / 28
    assert averages["P2"] == pytest.approx(expected)


def test_product_daily_history_fills_quiet_days(sample_daily_sales, latest_day):
    history = analytics.product_daily_history(sample_daily_sales, "P3", 30, latest_day)
    assert len(history) == 30
    assert (history["units"] >= 0).all()
    assert (history["units"] == 0).any()


def test_empty_inputs_return_empty_frames(sample_sales, latest_day):
    empty = sample_sales.iloc[0:0]
    assert analytics.category_performance(empty).empty
    assert analytics.product_leaderboard(empty).empty
    assert analytics.sales_by_grain(empty, "Daily").empty
    assert analytics.weekday_pattern(empty).empty
    assert analytics.monthly_seasonality(empty).empty
    assert analytics.slow_movers(empty, latest_day).empty

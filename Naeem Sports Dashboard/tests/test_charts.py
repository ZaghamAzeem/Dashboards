from __future__ import annotations

import json

import pandas as pd
import pytest

from dashboard import analytics, charts, forecasting
from dashboard import business_logic as rules


def rendered(figure):
    return json.loads(figure.to_json())


@pytest.fixture
def performance(sample_sales):
    return analytics.category_performance(sample_sales)


@pytest.fixture
def counts(sample_products):
    expected = pd.Series({"P1": 30.0, "P2": 12.0, "P3": 6.0})
    return rules.status_counts(rules.build_stock_overview(sample_products, expected))


def test_every_sport_has_its_own_colour():
    palette = {charts.category_color(sport) for sport in charts.CATEGORY_COLORS}
    assert len(palette) == len(charts.CATEGORY_COLORS)
    assert charts.category_color("Unknown Sport") == charts.MUTED


def test_sales_momentum_chart_draws_bars_and_a_trend_line(sample_sales):
    daily = analytics.sales_by_grain(sample_sales, "Daily")
    figure = charts.sales_momentum_chart(daily, previous_daily_average=1000.0)
    payload = rendered(figure)
    assert [trace["type"] for trace in payload["data"]] == ["bar", "scatter"]
    assert payload["layout"]["shapes"]


@pytest.mark.parametrize("grain", analytics.GRAIN_CHOICES)
def test_sales_trend_chart_renders_for_every_grain(sample_sales, grain):
    figure = charts.sales_trend_chart(analytics.sales_by_grain(sample_sales, grain), grain)
    assert rendered(figure)["data"]


def test_category_chart_labels_each_share(sample_sales, performance):
    payload = rendered(charts.category_bar_chart(performance))
    assert len(payload["data"][0]["y"]) == len(performance)
    assert all(label.endswith("%") for label in payload["data"][0]["text"])


def test_weekday_chart_highlights_the_busiest_day(sample_sales):
    pattern = analytics.weekday_pattern(sample_sales)
    payload = rendered(charts.weekday_chart(pattern))
    colors = payload["data"][0]["marker"]["color"]
    assert colors.count(charts.ACCENT) == 1


def test_status_bar_draws_one_band_per_populated_status(counts):
    payload = rendered(charts.stock_status_bar(counts))
    populated = sum(1 for value in counts.values() if value > 0)
    assert len(payload["data"]) == populated


def test_history_and_forecast_chart_separates_past_from_future(
    sample_daily_sales, sample_products, latest_day
):
    forecast = forecasting.forecast_all_products(sample_daily_sales, sample_products)
    history = analytics.product_daily_history(sample_daily_sales, "P1", 30, latest_day)
    figure = charts.history_and_forecast_chart(
        history, forecasting.product_forecast(forecast, "P1")
    )
    payload = rendered(figure)
    assert [trace["name"] for trace in payload["data"]] == ["Last 30 days", "Next 7 days"]
    assert payload["layout"]["shapes"]
    assert payload["layout"]["annotations"][0]["text"] == "Today"


def test_product_history_chart_adds_a_smoothed_line(sample_daily_sales, latest_day):
    history = analytics.product_daily_history(sample_daily_sales, "P1", 180, latest_day)
    payload = rendered(charts.product_history_chart(history))
    assert len(payload["data"]) == 2


def test_charts_survive_an_empty_selection(sample_sales, counts, latest_day):
    empty = sample_sales.iloc[0:0]
    figures = [
        charts.sales_momentum_chart(analytics.sales_by_grain(empty, "Daily"), 0.0),
        charts.sales_trend_chart(analytics.sales_by_grain(empty, "Daily"), "Daily"),
        charts.category_bar_chart(analytics.category_performance(empty)),
        charts.weekday_chart(analytics.weekday_pattern(empty)),
        charts.seasonal_chart(analytics.monthly_seasonality(empty)),
        charts.stock_status_bar({status: 0 for status in rules.STATUS_PRIORITY}),
        charts.momentum_comparison_chart(analytics.rising_products(empty, latest_day)),
        charts.upcoming_demand_chart(pd.DataFrame(columns=["category", "expected_units"])),
    ]
    for figure in figures:
        assert rendered(figure)["data"] == []

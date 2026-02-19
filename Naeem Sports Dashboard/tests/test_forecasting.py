from __future__ import annotations

import numpy as np
import pytest

from dashboard import forecasting


@pytest.fixture(scope="module")
def horizon():
    return forecasting.FORECAST_HORIZON


def test_feature_frame_builds_lags_and_averages(sample_daily_sales):
    features = forecasting.build_feature_frame(sample_daily_sales)
    for lag in forecasting.LAG_DAYS:
        assert f"lag_{lag}" in features
    for window in forecasting.ROLLING_WINDOWS:
        assert f"average_{window}" in features
    assert {"weekday", "month", "is_weekend"}.issubset(features.columns)


def test_lag_features_look_back_at_the_same_product(sample_daily_sales):
    features = forecasting.build_feature_frame(sample_daily_sales)
    single = features.loc[features["product_id"] == "P1"].sort_values("date").reset_index(drop=True)
    assert single.loc[5, "lag_1"] == single.loc[4, "units"]
    assert single.loc[10, "lag_7"] == single.loc[3, "units"]


def test_forecast_covers_seven_days_for_every_product(
    sample_daily_sales, sample_products, horizon
):
    forecast = forecasting.forecast_all_products(sample_daily_sales, sample_products)
    counts = forecast.groupby("product_id")["date"].nunique()
    assert set(counts.index) == set(sample_products["product_id"])
    assert (counts == horizon).all()


def test_forecast_values_are_safe_numbers(sample_daily_sales, sample_products):
    forecast = forecasting.forecast_all_products(sample_daily_sales, sample_products)
    values = forecast["expected_units"].to_numpy()
    assert np.isfinite(values).all()
    assert (values >= 0).all()


def test_forecast_starts_the_day_after_the_history(sample_daily_sales, sample_products):
    forecast = forecasting.forecast_all_products(sample_daily_sales, sample_products)
    last_history_day = sample_daily_sales["date"].max()
    assert forecast["date"].min() == last_history_day + np.timedelta64(1, "D")


def test_forecast_stays_close_to_observed_demand(sample_daily_sales, sample_products):
    forecast = forecasting.forecast_all_products(sample_daily_sales, sample_products)
    for product_id, block in forecast.groupby("product_id"):
        history = sample_daily_sales.loc[sample_daily_sales["product_id"] == product_id, "units"]
        ceiling = max(history.max() * 3, 5)
        assert block["expected_units"].max() <= ceiling


def test_forecast_is_not_a_flat_line(sample_daily_sales, sample_products):
    forecast = forecasting.forecast_all_products(sample_daily_sales, sample_products)
    busiest = forecast.loc[forecast["product_id"] == "P1", "expected_units"]
    assert busiest.nunique() > 1


def test_short_history_falls_back_without_crashing(short_daily_sales, sample_products, horizon):
    forecast = forecasting.forecast_all_products(short_daily_sales, sample_products)
    counts = forecast.groupby("product_id")["date"].nunique()
    assert (counts == horizon).all()
    assert (forecast["expected_units"] >= 0).all()
    assert np.isfinite(forecast["expected_units"]).all()


def test_naive_forecast_reflects_the_weekly_rhythm(sample_daily_sales, horizon):
    forecast = forecasting.naive_forecast(sample_daily_sales)
    busiest = forecast.loc[forecast["product_id"] == "P1"]
    assert len(busiest) == horizon
    assert busiest["expected_units"].nunique() > 1
    assert (forecast["expected_units"] >= 0).all()


def test_horizon_totals_sum_each_product(sample_daily_sales, sample_products):
    forecast = forecasting.forecast_all_products(sample_daily_sales, sample_products)
    totals = forecasting.horizon_totals(forecast)
    for product_id, block in forecast.groupby("product_id"):
        assert totals[product_id] == pytest.approx(block["expected_units"].sum())


def test_product_forecast_returns_an_ordered_series(sample_daily_sales, sample_products, horizon):
    forecast = forecasting.forecast_all_products(sample_daily_sales, sample_products)
    single = forecasting.product_forecast(forecast, "P2")
    assert len(single) == horizon
    assert single["date"].is_monotonic_increasing
    assert list(single.columns) == ["date", "expected_units"]


def test_empty_history_returns_an_empty_forecast(sample_daily_sales, sample_products):
    forecast = forecasting.forecast_all_products(sample_daily_sales.iloc[0:0], sample_products)
    assert forecast.empty

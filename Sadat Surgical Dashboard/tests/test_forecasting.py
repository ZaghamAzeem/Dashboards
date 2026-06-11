import numpy as np
import pandas as pd
import pytest

from dashboard import forecasting


@pytest.fixture(scope="module")
def sample_forecast(sample_sales):
    return forecasting.build_weekly_forecast(sample_sales)


def test_forecast_covers_seven_days_for_every_product(sample_forecast, sample_sales):
    counts = sample_forecast.groupby("product_id")["forecast_date"].nunique()
    assert set(counts.index) == set(sample_sales["product_id"])
    assert (counts == forecasting.FORECAST_HORIZON_DAYS).all()


def test_forecast_starts_the_day_after_the_last_sale(sample_forecast, sample_sales):
    last_history_date = sample_sales["sale_date"].max()
    for _, group in sample_forecast.groupby("product_id"):
        dates = group["forecast_date"].tolist()
        assert dates[0] == last_history_date + pd.Timedelta(days=1)
        assert dates == sorted(dates)
        assert len(set(dates)) == forecasting.FORECAST_HORIZON_DAYS


def test_forecast_values_are_numeric_and_non_negative(sample_forecast):
    values = sample_forecast["expected_units"]
    assert pd.api.types.is_numeric_dtype(values)
    assert np.isfinite(values).all()
    assert (values >= 0).all()


def test_forecast_varies_across_the_week(sample_forecast):
    for _, group in sample_forecast.groupby("product_id"):
        assert group["expected_units"].nunique() > 1


def test_forecast_reflects_quieter_weekends(sample_forecast):
    weekend = sample_forecast[sample_forecast["day_name"].isin(["Saturday", "Sunday"])]
    weekdays = sample_forecast[~sample_forecast["day_name"].isin(["Saturday", "Sunday"])]
    assert weekend["expected_units"].mean() < weekdays["expected_units"].mean()


def test_forecast_is_reproducible(sample_sales, sample_forecast):
    repeated = forecasting.build_weekly_forecast(sample_sales)
    pd.testing.assert_frame_equal(sample_forecast, repeated)


def test_forecast_scale_matches_recent_demand(sample_forecast, sample_sales):
    recent_daily_average = (
        sample_sales[sample_sales["sale_date"] > sample_sales["sale_date"].max()
                     - pd.Timedelta(days=28)]
        .groupby("product_id")["units_sold"]
        .mean()
    )
    forecast_daily_average = sample_forecast.groupby("product_id")["expected_units"].mean()
    for product_id, expected in forecast_daily_average.items():
        assert 0.4 * recent_daily_average[product_id] < expected
        assert expected < 2.5 * recent_daily_average[product_id]


def test_expected_demand_totals_are_whole_units(sample_forecast):
    totals = forecasting.expected_demand_by_product(sample_forecast)
    assert list(totals.columns) == ["product_id", "expected_demand"]
    assert pd.api.types.is_integer_dtype(totals["expected_demand"])
    assert (totals["expected_demand"] >= 0).all()


def test_product_forecast_returns_a_single_product(sample_forecast):
    product_id = sample_forecast["product_id"].iloc[0]
    selected = forecasting.product_forecast(sample_forecast, product_id)
    assert set(selected["product_id"]) == {product_id}
    assert len(selected) == forecasting.FORECAST_HORIZON_DAYS


def test_short_history_falls_back_to_recent_average():
    calendar = pd.date_range(end=pd.Timestamp("2025-06-30"), periods=10, freq="D")
    short_history = pd.DataFrame(
        {
            "sale_date": calendar,
            "product_id": "SI-901",
            "product_name": "Short History Item",
            "category": "Surgical Instruments",
            "unit_of_measure": "pieces",
            "units_sold": [4] * 10,
            "on_promotion": 0,
            "stock_on_hand": 50,
        }
    )
    predictions = forecasting.forecast_from_history(
        short_history, None, {"SI-901": 0}, {"Surgical Instruments": 0}, 7
    )
    assert len(predictions) == 7
    assert (predictions["expected_units"] == 4).all()

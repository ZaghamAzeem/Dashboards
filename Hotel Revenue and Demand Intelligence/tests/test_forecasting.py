import numpy as np
import pandas as pd
import pytest

from src.forecasting import (
    DEFAULT_HORIZON,
    demand_alert,
    forecast_demand,
    overall_demand_level,
)


@pytest.fixture(scope="module")
def result(daily_metrics, hotel_capacity):
    return forecast_demand(daily_metrics, hotel_capacity, DEFAULT_HORIZON)


def test_forecast_is_produced(result):
    assert result["available"] is True
    assert result["method"] == "learned_pattern"
    assert not result["forecast"].empty


def test_forecast_horizon_is_respected(daily_metrics, hotel_capacity):
    for horizon in (7, 10, 14):
        outcome = forecast_demand(daily_metrics, hotel_capacity, horizon)
        assert len(outcome["forecast"]) == horizon
        assert outcome["horizon"] == horizon


def test_forecast_starts_the_day_after_the_records_end(result, daily_metrics):
    expected = daily_metrics["stay_date"].max() + pd.Timedelta(days=1)
    assert result["forecast"]["stay_date"].iloc[0] == expected
    gaps = result["forecast"]["stay_date"].diff().dropna().dt.days.unique()
    assert set(gaps) == {1}


def test_forecast_values_are_never_negative(result):
    forecast = result["forecast"]
    for column in ("rooms_sold", "adr", "revenue", "occupancy_rate", "revpar"):
        assert (forecast[column] >= 0).all()


def test_forecast_respects_hotel_capacity(result, hotel_capacity):
    forecast = result["forecast"]
    assert (forecast["rooms_sold"] <= hotel_capacity).all()
    assert forecast["occupancy_rate"].between(0, 100).all()


def test_forecast_revenue_is_consistent(result):
    forecast = result["forecast"]
    computed = forecast["rooms_sold"] * forecast["adr"]
    assert np.allclose(computed, forecast["revenue"], atol=0.01)


def test_forecast_values_are_plausible(result, daily_metrics):
    forecast = result["forecast"]
    historical_mean = daily_metrics["rooms_sold"].mean()
    assert 0.4 * historical_mean < forecast["rooms_sold"].mean() < 1.6 * historical_mean
    historical_rate = daily_metrics.loc[daily_metrics["adr"] > 0, "adr"].mean()
    assert 0.5 * historical_rate < forecast["adr"].mean() < 1.6 * historical_rate


def test_forecast_labels_every_night(result):
    forecast = result["forecast"]
    assert set(forecast["demand_level"]).issubset({"High", "Moderate", "Low"})
    assert forecast["weekday"].notna().all()


def test_forecast_quality_is_measured(result):
    quality = result["quality"]
    assert quality["validation_days"] > 0
    assert quality["mean_absolute_error"] >= 0
    assert 0 < quality["accuracy_percent"] <= 100
    assert quality["accuracy_percent"] >= quality["baseline_accuracy_percent"] - 5


def test_comparison_figures_are_reported(result):
    comparison = result["comparison"]
    for key in ("recent_revenue", "expected_revenue", "recent_occupancy",
                "expected_occupancy", "typical_occupancy"):
        assert comparison[key] >= 0
    assert 0 <= comparison["expected_occupancy"] <= 100


def test_short_history_falls_back_gracefully(daily_metrics, hotel_capacity):
    short = daily_metrics.head(60)
    outcome = forecast_demand(short, hotel_capacity, 7)
    assert outcome["available"] is True
    assert outcome["method"] == "recent_pattern"
    assert len(outcome["forecast"]) == 7
    assert (outcome["forecast"]["rooms_sold"] >= 0).all()
    assert outcome["quality"] == {}


def test_missing_data_is_handled(daily_metrics):
    assert forecast_demand(daily_metrics.iloc[0:0], 120, 7)["available"] is False
    assert forecast_demand(None, 120, 7)["available"] is False
    assert forecast_demand(daily_metrics, 0, 7)["available"] is False


def test_zero_demand_history_is_handled(daily_metrics, hotel_capacity):
    quiet = daily_metrics.copy()
    quiet[["rooms_sold", "room_revenue", "adr", "occupancy_rate", "revpar"]] = 0
    outcome = forecast_demand(quiet, hotel_capacity, 7)
    assert outcome["available"] is True
    assert (outcome["forecast"]["rooms_sold"] >= 0).all()
    assert (outcome["forecast"]["revenue"] >= 0).all()


def test_alert_matches_the_outlook(result):
    alert = demand_alert(result)
    assert alert["tone"] in {"healthy", "watch", "priority", "neutral"}
    assert alert["title"]
    assert alert["text"]
    assert overall_demand_level(result) in {"High", "Moderate", "Low"}


def test_alert_handles_a_missing_outlook():
    alert = demand_alert({"available": False})
    assert alert["tone"] == "neutral"
    assert "unavailable" in alert["title"].lower()


def test_forecast_is_reproducible(daily_metrics, hotel_capacity):
    first = forecast_demand(daily_metrics, hotel_capacity, 7)["forecast"]
    second = forecast_demand(daily_metrics, hotel_capacity, 7)["forecast"]
    assert np.allclose(first["rooms_sold"], second["rooms_sold"])

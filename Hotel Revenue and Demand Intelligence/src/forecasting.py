from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

DEFAULT_HORIZON = 14
MINIMUM_HISTORY_DAYS = 120
WARMUP_DAYS = 35
VALIDATION_DAYS = 28
LAG_OFFSETS = (0, 1, 2, 3, 6, 13, 27)
ROLLING_WINDOWS = (7, 14, 28)
SEASONAL_OFFSET = 364


def _calendar_frame(dates: pd.DatetimeIndex, reference: pd.DataFrame) -> pd.DataFrame:
    frame = pd.DataFrame({"stay_date": dates})
    frame["day_of_week"] = frame["stay_date"].dt.weekday
    frame["month"] = frame["stay_date"].dt.month
    frame["day_of_month"] = frame["stay_date"].dt.day
    day_of_year = frame["stay_date"].dt.dayofyear
    frame["season_sin"] = np.sin(2 * np.pi * day_of_year / 365.25)
    frame["season_cos"] = np.cos(2 * np.pi * day_of_year / 365.25)
    frame["is_weekend"] = (frame["day_of_week"] >= 4).astype(int)

    flags = reference.set_index("stay_date")[["is_promotion", "is_special_period"]]
    direct = flags.reindex(frame["stay_date"])
    prior_year = flags.reindex(frame["stay_date"] - pd.Timedelta(days=SEASONAL_OFFSET))
    prior_year.index = frame["stay_date"]
    for column in ("is_promotion", "is_special_period"):
        values = direct[column].to_numpy()
        backup = prior_year[column].to_numpy()
        frame[column] = np.where(np.isnan(values), np.nan_to_num(backup), values)
    return frame


def _origin_features(values: np.ndarray, origin: int) -> dict:
    features = {}
    for offset in LAG_OFFSETS:
        index = origin - offset
        features[f"lag_{offset}"] = values[index] if index >= 0 else np.nan
    for window in ROLLING_WINDOWS:
        start = max(origin - window + 1, 0)
        window_values = values[start:origin + 1]
        features[f"mean_{window}"] = float(np.mean(window_values)) if len(window_values) else np.nan
    recent = values[max(origin - 6, 0):origin + 1]
    features["std_7"] = float(np.std(recent)) if len(recent) > 1 else 0.0
    short = values[max(origin - 6, 0):origin + 1]
    longer = values[max(origin - 27, 0):origin + 1]
    features["momentum"] = (
        float(np.mean(short) - np.mean(longer)) if len(short) and len(longer) else 0.0
    )
    return features


def _calendar_rows(calendar: pd.DataFrame) -> list[dict]:
    return calendar.drop(columns=["stay_date"]).to_dict("records")


def _build_training_matrix(values: np.ndarray, calendar: pd.DataFrame,
                           horizon: int, last_target_index: int) -> tuple[pd.DataFrame, np.ndarray]:
    rows, targets = [], []
    total = len(values)
    calendar_rows = _calendar_rows(calendar)
    for origin in range(WARMUP_DAYS, total):
        origin_features = _origin_features(values, origin)
        for step in range(1, horizon + 1):
            target_index = origin + step
            if target_index > last_target_index or target_index >= total:
                continue
            row = dict(origin_features)
            row["horizon"] = step
            row.update(calendar_rows[target_index])
            seasonal_index = target_index - SEASONAL_OFFSET
            row["seasonal_reference"] = values[seasonal_index] if seasonal_index >= 0 else np.nan
            rows.append(row)
            targets.append(values[target_index])
    return pd.DataFrame(rows), np.asarray(targets, dtype=float)


def _build_prediction_matrix(values: np.ndarray, future_calendar: pd.DataFrame,
                             horizon: int) -> pd.DataFrame:
    origin = len(values) - 1
    origin_features = _origin_features(values, origin)
    future_rows = _calendar_rows(future_calendar)
    rows = []
    for step in range(1, horizon + 1):
        row = dict(origin_features)
        row["horizon"] = step
        row.update(future_rows[step - 1])
        seasonal_index = origin + step - SEASONAL_OFFSET
        row["seasonal_reference"] = values[seasonal_index] if 0 <= seasonal_index < len(values) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def _fit_model(features: pd.DataFrame, targets: np.ndarray) -> HistGradientBoostingRegressor:
    model = HistGradientBoostingRegressor(
        max_iter=220,
        learning_rate=0.06,
        max_depth=6,
        min_samples_leaf=25,
        l2_regularization=0.5,
        random_state=7,
    )
    model.fit(features, targets)
    return model


def _validate(values: np.ndarray, calendar: pd.DataFrame, horizon: int) -> dict:
    total = len(values)
    train_limit = total - 1 - VALIDATION_DAYS
    if train_limit <= WARMUP_DAYS + horizon:
        return {}
    features, targets = _build_training_matrix(values, calendar, horizon, train_limit)
    if features.empty:
        return {}
    model = _fit_model(features, targets)

    calendar_rows = _calendar_rows(calendar)
    predictions, actuals, baseline = [], [], []
    for origin in (train_limit, train_limit + horizon):
        if origin + horizon >= total:
            continue
        origin_features = _origin_features(values, origin)
        rows = []
        for step in range(1, horizon + 1):
            row = dict(origin_features)
            row["horizon"] = step
            row.update(calendar_rows[origin + step])
            seasonal_index = origin + step - SEASONAL_OFFSET
            row["seasonal_reference"] = values[seasonal_index] if seasonal_index >= 0 else np.nan
            rows.append(row)
            actuals.append(values[origin + step])
            baseline.append(values[origin + step - 7])
        predictions.extend(model.predict(pd.DataFrame(rows)[features.columns]))

    if not actuals:
        return {}
    predictions = np.clip(np.asarray(predictions), 0, None)
    actuals = np.asarray(actuals, dtype=float)
    baseline = np.asarray(baseline, dtype=float)
    measurable = actuals > 0
    quality = {
        "mean_absolute_error": float(mean_absolute_error(actuals, predictions)),
        "validation_days": int(len(actuals)),
    }
    if measurable.any():
        reference = actuals[measurable]
        quality["accuracy_percent"] = float(
            100 - np.mean(np.abs(predictions[measurable] - reference) / reference) * 100
        )
        quality["baseline_accuracy_percent"] = float(
            100 - np.mean(np.abs(baseline[measurable] - reference) / reference) * 100
        )
    return quality


def _fallback_forecast(daily: pd.DataFrame, horizon: int) -> pd.DataFrame:
    recent = daily.tail(28)
    weekday_rooms = recent.groupby(recent["stay_date"].dt.weekday)["rooms_sold"].mean()
    weekday_adr = recent.groupby(recent["stay_date"].dt.weekday)["adr"].mean()
    overall_rooms = float(recent["rooms_sold"].mean()) if len(recent) else 0.0
    overall_adr = float(recent.loc[recent["adr"] > 0, "adr"].mean()) if len(recent) else 0.0
    start = daily["stay_date"].max() + pd.Timedelta(days=1)
    dates = pd.date_range(start, periods=horizon, freq="D")
    rooms = [float(weekday_rooms.get(date.weekday(), overall_rooms)) for date in dates]
    rates = [float(weekday_adr.get(date.weekday(), overall_adr)) for date in dates]
    return pd.DataFrame({"stay_date": dates, "rooms_sold": rooms, "adr": rates})


def _demand_levels(forecast: pd.DataFrame, daily: pd.DataFrame) -> pd.Series:
    levels = []
    for row in forecast.itertuples(index=False):
        weekday = row.stay_date.weekday()
        comparable = daily.loc[daily["stay_date"].dt.weekday == weekday, "rooms_sold"]
        if len(comparable) < 8:
            comparable = daily["rooms_sold"]
        if comparable.empty:
            levels.append("Moderate")
            continue
        high = comparable.quantile(0.68)
        low = comparable.quantile(0.32)
        if row.rooms_sold >= high:
            levels.append("High")
        elif row.rooms_sold <= low:
            levels.append("Low")
        else:
            levels.append("Moderate")
    return pd.Series(levels, index=forecast.index)


def forecast_demand(daily_metrics: pd.DataFrame, capacity: int,
                    horizon: int = DEFAULT_HORIZON) -> dict:
    if daily_metrics is None or daily_metrics.empty or capacity <= 0:
        return {"available": False, "reason": "no_data"}

    daily = daily_metrics.sort_values("stay_date").reset_index(drop=True)
    horizon = max(int(horizon), 1)

    if len(daily) < MINIMUM_HISTORY_DAYS:
        forecast = _fallback_forecast(daily, horizon)
        method = "recent_pattern"
        quality = {}
    else:
        history_calendar = _calendar_frame(pd.DatetimeIndex(daily["stay_date"]), daily)
        future_dates = pd.date_range(
            daily["stay_date"].max() + pd.Timedelta(days=1), periods=horizon, freq="D"
        )
        future_calendar = _calendar_frame(future_dates, daily)

        forecast = pd.DataFrame({"stay_date": future_dates})
        quality = {}
        for target in ("rooms_sold", "adr"):
            values = daily[target].to_numpy(dtype=float)
            features, targets = _build_training_matrix(
                values, history_calendar, horizon, len(values) - 1
            )
            if features.empty:
                forecast = _fallback_forecast(daily, horizon)
                break
            model = _fit_model(features, targets)
            prediction_matrix = _build_prediction_matrix(
                values, future_calendar, horizon
            )[features.columns]
            forecast[target] = np.clip(model.predict(prediction_matrix), 0, None)
            if target == "rooms_sold":
                quality = _validate(values, history_calendar, horizon)
        method = "learned_pattern"

    forecast["rooms_sold"] = np.clip(forecast["rooms_sold"], 0, capacity).round(1)
    forecast["adr"] = np.clip(forecast["adr"], 0, None).round(2)
    forecast["occupancy_rate"] = (forecast["rooms_sold"] / capacity * 100).round(1)
    forecast["revenue"] = (forecast["rooms_sold"] * forecast["adr"]).round(2)
    forecast["revpar"] = (forecast["revenue"] / capacity).round(2)
    forecast["weekday"] = forecast["stay_date"].dt.day_name()
    forecast["is_weekend"] = forecast["stay_date"].dt.weekday >= 4
    forecast["demand_level"] = _demand_levels(forecast, daily)

    recent_window = daily.tail(horizon)
    comparison = {
        "recent_revenue": float(recent_window["room_revenue"].sum()),
        "expected_revenue": float(forecast["revenue"].sum()),
        "recent_occupancy": float(recent_window["occupancy_rate"].mean()),
        "expected_occupancy": float(forecast["occupancy_rate"].mean()),
        "recent_rooms_sold": float(recent_window["rooms_sold"].mean()),
        "expected_rooms_sold": float(forecast["rooms_sold"].mean()),
    }
    comparison["revenue_change"] = (
        (comparison["expected_revenue"] - comparison["recent_revenue"])
        / comparison["recent_revenue"] * 100
        if comparison["recent_revenue"] else None
    )
    comparison["occupancy_change"] = (
        comparison["expected_occupancy"] - comparison["recent_occupancy"]
    )
    comparison["typical_occupancy"] = float(daily["occupancy_rate"].mean())

    return {
        "available": True,
        "forecast": forecast,
        "history": daily.tail(90)[["stay_date", "rooms_sold", "occupancy_rate", "room_revenue", "adr"]],
        "comparison": comparison,
        "quality": quality,
        "method": method,
        "horizon": horizon,
        "capacity": capacity,
    }


def overall_demand_level(forecast_result: dict) -> str:
    if not forecast_result.get("available"):
        return "Moderate"
    comparison = forecast_result["comparison"]
    expected = comparison["expected_occupancy"]
    typical = comparison.get("typical_occupancy", expected)
    if expected >= typical + 5:
        return "High"
    if expected <= typical - 5:
        return "Low"
    return "Moderate"


def demand_alert(forecast_result: dict) -> dict:
    if not forecast_result.get("available"):
        return {
            "tone": "neutral",
            "title": "Demand outlook unavailable",
            "text": "There is not enough recent activity to prepare an outlook.",
        }
    forecast = forecast_result["forecast"]
    comparison = forecast_result["comparison"]
    peak = float(forecast["occupancy_rate"].max())
    average = float(forecast["occupancy_rate"].mean())
    change = comparison["occupancy_change"]
    busiest = forecast.loc[forecast["occupancy_rate"].idxmax()]

    if peak >= 92:
        return {
            "tone": "priority",
            "title": "Potential capacity pressure",
            "text": (
                f"Rooms are expected to be close to full on {busiest['weekday']}, "
                f"{busiest['stay_date']:%d %b}, at around {peak:.0f}% occupancy. "
                "Availability should be protected for the highest-value bookings."
            ),
        }
    if peak >= 85 or average >= 82:
        return {
            "tone": "watch",
            "title": "High demand expected",
            "text": (
                f"Occupancy is expected to average {average:.0f}% over the coming period, "
                f"peaking near {peak:.0f}%. Rates and availability are worth reviewing daily."
            ),
        }
    if change is not None and change >= 3:
        return {
            "tone": "watch",
            "title": "Demand may increase",
            "text": (
                f"Occupancy is expected to run about {change:.0f} points above the recent period, "
                f"averaging {average:.0f}%. Staffing and room readiness should be planned for it."
            ),
        }
    return {
        "tone": "healthy",
        "title": "Demand looks healthy",
        "text": (
            f"Occupancy is expected to average {average:.0f}% over the coming period, "
            "broadly in line with recent trading. No immediate action is required."
        ),
    }

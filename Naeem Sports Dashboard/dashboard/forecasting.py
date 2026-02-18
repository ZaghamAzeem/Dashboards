from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

FORECAST_HORIZON = 7
LAG_DAYS = (1, 2, 3, 7, 14)
ROLLING_WINDOWS = (7, 14, 28)
MIN_TRAINING_ROWS = 400
MIN_PRODUCT_HISTORY = 45

FEATURE_COLUMNS = (
    [f"lag_{lag}" for lag in LAG_DAYS]
    + [f"average_{window}" for window in ROLLING_WINDOWS]
    + ["weekday", "month", "is_weekend", "unit_price", "product_code", "category_code"]
)


def _encode(values, categories):
    lookup = {value: index for index, value in enumerate(categories)}
    return values.map(lookup).astype("float64")


def build_feature_frame(daily_sales):
    frame = daily_sales.sort_values(["product_id", "date"]).copy()
    grouped = frame.groupby("product_id")["units"]

    for lag in LAG_DAYS:
        frame[f"lag_{lag}"] = grouped.shift(lag)

    frame["previous_units"] = grouped.shift(1)
    for window in ROLLING_WINDOWS:
        frame[f"average_{window}"] = frame.groupby("product_id")["previous_units"].transform(
            lambda series, span=window: series.rolling(span, min_periods=max(3, span // 3)).mean()
        )

    frame["weekday"] = frame["date"].dt.dayofweek
    frame["month"] = frame["date"].dt.month
    frame["is_weekend"] = frame["weekday"].isin([5, 6]).astype(int)
    return frame.drop(columns=["previous_units"])


def train_demand_model(features, random_state=7):
    usable = features.dropna(subset=FEATURE_COLUMNS)
    if len(usable) < MIN_TRAINING_ROWS:
        return None

    design = usable[FEATURE_COLUMNS].to_numpy(dtype="float64")
    target = np.log1p(usable["units"].to_numpy(dtype="float64"))

    model = HistGradientBoostingRegressor(
        max_iter=260,
        learning_rate=0.07,
        max_depth=7,
        min_samples_leaf=25,
        l2_regularization=0.4,
        random_state=random_state,
    )
    model.fit(design, target)
    return model


def _history_matrix(daily_sales):
    matrix = daily_sales.pivot_table(
        index="date", columns="product_id", values="units", aggfunc="sum"
    )
    return matrix.fillna(0.0).sort_index()


def _safety_ceiling(history):
    upper = history.quantile(0.98) * 2.5
    recent = history.tail(28).mean() * 3.5 + 5.0
    return np.maximum(upper, recent)


def _seasonal_profile(history, lookback=120):
    recent = history.tail(lookback)
    overall = recent.mean()
    profile = {}
    for weekday in range(7):
        same_weekday = recent.loc[recent.index.dayofweek == weekday]
        profile[weekday] = overall if same_weekday.empty else same_weekday.mean()
    return profile, overall


def naive_forecast(daily_sales, horizon=FORECAST_HORIZON):
    history = _history_matrix(daily_sales)
    if history.empty:
        return pd.DataFrame(columns=["date", "product_id", "expected_units"])

    profile, overall = _seasonal_profile(history)
    last_date = history.index.max()
    records = []
    for step in range(1, horizon + 1):
        target_date = last_date + pd.Timedelta(days=step)
        weekday_average = profile.get(target_date.dayofweek, overall)
        blended = (weekday_average * 0.6 + overall * 0.4).clip(lower=0.0)
        for product_id, value in blended.items():
            records.append(
                {"date": target_date, "product_id": product_id, "expected_units": float(value)}
            )
    return pd.DataFrame(records)


def forecast_all_products(daily_sales, products, horizon=FORECAST_HORIZON):
    if daily_sales.empty:
        return pd.DataFrame(columns=["date", "product_id", "expected_units"])

    history = _history_matrix(daily_sales)
    product_ids = list(history.columns)
    catalog = products.set_index("product_id").reindex(product_ids)

    sport_categories = sorted(catalog["category"].dropna().unique())
    product_code = pd.Series(np.arange(len(product_ids), dtype="float64"), index=product_ids)
    category_code = _encode(catalog["category"], sport_categories)
    unit_price = catalog["unit_price"].astype("float64")

    feature_frame = build_feature_frame(daily_sales)
    feature_frame["product_code"] = feature_frame["product_id"].map(product_code)
    feature_frame["category_code"] = feature_frame["product_id"].map(category_code)
    feature_frame["unit_price"] = feature_frame["product_id"].map(unit_price)

    model = train_demand_model(feature_frame)
    if model is None:
        return naive_forecast(daily_sales, horizon)

    ceiling = _safety_ceiling(history)
    observed_days = (history > 0).sum()
    fallback = naive_forecast(daily_sales, horizon).set_index(["date", "product_id"])

    working = history.copy()
    records = []
    for _ in range(horizon):
        target_date = working.index.max() + pd.Timedelta(days=1)

        block = pd.DataFrame(index=product_ids)
        for lag in LAG_DAYS:
            block[f"lag_{lag}"] = working.iloc[-lag].reindex(product_ids).to_numpy()
        for window in ROLLING_WINDOWS:
            block[f"average_{window}"] = working.tail(window).mean().reindex(product_ids).to_numpy()
        block["weekday"] = target_date.dayofweek
        block["month"] = target_date.month
        block["is_weekend"] = int(target_date.dayofweek in (5, 6))
        block["unit_price"] = unit_price.to_numpy()
        block["product_code"] = product_code.to_numpy()
        block["category_code"] = category_code.to_numpy()

        predicted = np.expm1(model.predict(block[FEATURE_COLUMNS].to_numpy(dtype="float64")))
        predicted = np.clip(predicted, 0.0, None)
        predicted = np.minimum(predicted, ceiling.reindex(product_ids).to_numpy())
        predicted = np.nan_to_num(predicted, nan=0.0, posinf=0.0, neginf=0.0)

        for position, product_id in enumerate(product_ids):
            if observed_days.get(product_id, 0) < MIN_PRODUCT_HISTORY:
                key = (target_date, product_id)
                if key in fallback.index:
                    predicted[position] = float(fallback.loc[key, "expected_units"])

        working.loc[target_date] = predicted
        for position, product_id in enumerate(product_ids):
            records.append(
                {
                    "date": target_date,
                    "product_id": product_id,
                    "expected_units": float(predicted[position]),
                }
            )

    return pd.DataFrame(records)


def horizon_totals(forecast):
    if forecast.empty:
        return pd.Series(dtype=float)
    return forecast.groupby("product_id")["expected_units"].sum()


def product_forecast(forecast, product_id):
    selection = forecast.loc[forecast["product_id"] == product_id]
    return selection[["date", "expected_units"]].sort_values("date").reset_index(drop=True)

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

FORECAST_HORIZON_DAYS = 7
LAG_DAYS = (1, 7, 14)
ROLLING_WINDOWS = (7, 28)
MINIMUM_HISTORY_DAYS = max(max(LAG_DAYS), max(ROLLING_WINDOWS))
RANDOM_STATE = 42

FEATURE_COLUMNS = [
    "lag_1",
    "lag_7",
    "lag_14",
    "rolling_mean_7",
    "rolling_mean_28",
    "day_of_week",
    "month",
    "on_promotion",
    "product_code",
    "category_code",
]


def build_reference_codes(sales):
    product_codes = {
        product_id: code
        for code, product_id in enumerate(sorted(sales["product_id"].unique()))
    }
    category_codes = {
        category: code for code, category in enumerate(sorted(sales["category"].unique()))
    }
    return product_codes, category_codes


def add_history_features(product_sales):
    featured = product_sales.sort_values("sale_date").copy()
    for lag in LAG_DAYS:
        featured[f"lag_{lag}"] = featured["units_sold"].shift(lag)
    previous_days = featured["units_sold"].shift(1)
    for window in ROLLING_WINDOWS:
        featured[f"rolling_mean_{window}"] = previous_days.rolling(window).mean()
    return featured


def build_supervised_frame(sales, product_codes, category_codes):
    prepared = [
        add_history_features(group)
        for _, group in sales.groupby("product_id", sort=True)
    ]
    frame = pd.concat(prepared, ignore_index=True)
    frame["day_of_week"] = frame["sale_date"].dt.dayofweek
    frame["month"] = frame["sale_date"].dt.month
    frame["product_code"] = frame["product_id"].map(product_codes)
    frame["category_code"] = frame["category"].map(category_codes)
    return frame.dropna(subset=FEATURE_COLUMNS).reset_index(drop=True)


def train_demand_model(sales):
    product_codes, category_codes = build_reference_codes(sales)
    training_frame = build_supervised_frame(sales, product_codes, category_codes)
    model = RandomForestRegressor(
        n_estimators=140,
        min_samples_leaf=2,
        max_features=0.7,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(training_frame[FEATURE_COLUMNS], training_frame["units_sold"])
    return model, product_codes, category_codes


def rolling_average(history, window):
    if not history:
        return 0.0
    return float(np.mean(history[-window:]))


def lagged_value(history, lag):
    if len(history) < lag:
        return rolling_average(history, len(history))
    return float(history[-lag])


def build_feature_row(history, target_date, product_code, category_code):
    return [
        lagged_value(history, 1),
        lagged_value(history, 7),
        lagged_value(history, 14),
        rolling_average(history, 7),
        rolling_average(history, 28),
        target_date.dayofweek,
        target_date.month,
        0,
        product_code,
        category_code,
    ]


def build_product_states(sales):
    states = []
    for product_id, group in sales.groupby("product_id", sort=True):
        ordered = group.sort_values("sale_date")
        states.append(
            {
                "product_id": product_id,
                "product_name": ordered["product_name"].iloc[0],
                "category": ordered["category"].iloc[0],
                "unit_of_measure": ordered["unit_of_measure"].iloc[0],
                "history": ordered["units_sold"].astype(float).tolist(),
                "last_date": ordered["sale_date"].max(),
            }
        )
    return states


def predict_expected_units(model, states, feature_rows):
    expected = np.array(
        [rolling_average(state["history"], len(state["history"])) for state in states],
        dtype=float,
    )
    has_enough_history = np.array(
        [len(state["history"]) >= MINIMUM_HISTORY_DAYS for state in states]
    )
    if model is not None and has_enough_history.any():
        modelled = pd.DataFrame(
            np.array(feature_rows)[has_enough_history], columns=FEATURE_COLUMNS
        )
        expected[has_enough_history] = model.predict(modelled)
    return np.round(np.clip(expected, 0.0, None), 2)


def forecast_from_history(sales, model, product_codes, category_codes, horizon):
    states = build_product_states(sales)
    records = []
    for step in range(1, horizon + 1):
        target_dates = [state["last_date"] + pd.Timedelta(days=step) for state in states]
        feature_rows = [
            build_feature_row(
                state["history"],
                target_date,
                product_codes[state["product_id"]],
                category_codes[state["category"]],
            )
            for state, target_date in zip(states, target_dates)
        ]
        predictions = predict_expected_units(model, states, feature_rows)
        for state, target_date, expected_units in zip(states, target_dates, predictions):
            state["history"].append(float(expected_units))
            records.append(
                {
                    "product_id": state["product_id"],
                    "product_name": state["product_name"],
                    "category": state["category"],
                    "unit_of_measure": state["unit_of_measure"],
                    "forecast_date": target_date,
                    "expected_units": float(expected_units),
                }
            )
    forecast = pd.DataFrame(records)
    forecast["day_name"] = forecast["forecast_date"].dt.day_name()
    return forecast.sort_values(["product_id", "forecast_date"]).reset_index(drop=True)


def build_weekly_forecast(sales, horizon=FORECAST_HORIZON_DAYS):
    model, product_codes, category_codes = train_demand_model(sales)
    return forecast_from_history(sales, model, product_codes, category_codes, horizon)


def expected_demand_by_product(forecast):
    if forecast.empty:
        return pd.DataFrame(columns=["product_id", "expected_demand"])
    totals = forecast.groupby("product_id", as_index=False)["expected_units"].sum()
    totals["expected_demand"] = totals["expected_units"].round().astype(int)
    return totals[["product_id", "expected_demand"]]


def product_forecast(forecast, product_id):
    selected = forecast[forecast["product_id"] == product_id]
    return selected.sort_values("forecast_date").reset_index(drop=True)


def total_expected_demand(forecast):
    if forecast.empty:
        return 0
    return int(round(forecast["expected_units"].sum()))

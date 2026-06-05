import numpy as np
import pandas as pd

DAILY = "Daily"
WEEKLY = "Weekly"
MONTHLY = "Monthly"
GRANULARITIES = [DAILY, WEEKLY, MONTHLY]

WEEKDAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

TREND_RISING = "rising"
TREND_STABLE = "stable"
TREND_DECLINING = "declining"

TREND_SENSITIVITY = 0.05
VARIABILITY_SENSITIVITY = 0.40
COMPARISON_WINDOW_DAYS = 28


def filter_sales(sales, start_date=None, end_date=None, categories=None, product_ids=None):
    filtered = sales
    if start_date is not None:
        filtered = filtered[filtered["sale_date"] >= pd.Timestamp(start_date)]
    if end_date is not None:
        filtered = filtered[filtered["sale_date"] <= pd.Timestamp(end_date)]
    if categories:
        filtered = filtered[filtered["category"].isin(categories)]
    if product_ids:
        filtered = filtered[filtered["product_id"].isin(product_ids)]
    return filtered.copy()


def period_start_date(period_label, granularity):
    if granularity == WEEKLY:
        return period_label - pd.Timedelta(days=6)
    return period_label


def period_end_date(period_label, granularity):
    if granularity == MONTHLY:
        return period_label + pd.offsets.MonthEnd(0)
    return period_label


def trim_incomplete_periods(grouped, sales, granularity):
    if granularity == DAILY or len(grouped) <= 1:
        return grouped.reset_index(drop=True)
    first_label = grouped["period"].iloc[0]
    if len(grouped) > 2 and sales["sale_date"].min() > period_start_date(
        first_label, granularity
    ):
        grouped = grouped.iloc[1:]
    last_label = grouped["period"].iloc[-1]
    if len(grouped) > 1 and sales["sale_date"].max() < period_end_date(
        last_label, granularity
    ):
        grouped = grouped.iloc[:-1]
    return grouped.reset_index(drop=True)


def sales_over_time(sales, granularity=DAILY):
    if sales.empty:
        return pd.DataFrame(columns=["period", "units_sold"])
    frequency = {DAILY: "D", WEEKLY: "W-MON", MONTHLY: "MS"}[granularity]
    grouped = (
        sales.groupby(pd.Grouper(key="sale_date", freq=frequency))["units_sold"]
        .sum()
        .reset_index()
    )
    grouped.columns = ["period", "units_sold"]
    return trim_incomplete_periods(grouped, sales, granularity)


def sales_by_category(sales):
    if sales.empty:
        return pd.DataFrame(columns=["category", "units_sold", "share"])
    grouped = sales.groupby("category", as_index=False)["units_sold"].sum()
    total = grouped["units_sold"].sum()
    grouped["share"] = grouped["units_sold"] / total if total else 0.0
    return grouped.sort_values("units_sold", ascending=False).reset_index(drop=True)


def product_sales_summary(sales):
    if sales.empty:
        return pd.DataFrame(
            columns=["product_id", "product_name", "category", "unit_of_measure", "units_sold"]
        )
    grouping = ["product_id", "product_name", "category", "unit_of_measure"]
    summary = sales.groupby(grouping, as_index=False)["units_sold"].sum()
    return summary.sort_values("units_sold", ascending=False).reset_index(drop=True)


def top_products(sales, limit=10):
    return product_sales_summary(sales).head(limit).reset_index(drop=True)


def slow_moving_products(sales, limit=5):
    summary = product_sales_summary(sales)
    return summary.sort_values("units_sold").head(limit).reset_index(drop=True)


def weekday_demand_pattern(sales):
    if sales.empty:
        return pd.DataFrame(columns=["weekday", "average_units"])
    daily_totals = sales.groupby("sale_date", as_index=False)["units_sold"].sum()
    daily_totals["weekday"] = daily_totals["sale_date"].dt.day_name()
    pattern = daily_totals.groupby("weekday", as_index=False)["units_sold"].mean()
    pattern.columns = ["weekday", "average_units"]
    pattern["weekday"] = pd.Categorical(pattern["weekday"], categories=WEEKDAY_ORDER, ordered=True)
    return pattern.sort_values("weekday").reset_index(drop=True)


def window_bounds(reference_date, days):
    end_date = pd.Timestamp(reference_date)
    return end_date - pd.Timedelta(days=days - 1), end_date


def units_sold_in_window(sales, reference_date, days):
    start_date, end_date = window_bounds(reference_date, days)
    window = sales[(sales["sale_date"] >= start_date) & (sales["sale_date"] <= end_date)]
    return int(window["units_sold"].sum())


def recent_sales_by_product(sales, reference_date, days):
    start_date, end_date = window_bounds(reference_date, days)
    window = sales[(sales["sale_date"] >= start_date) & (sales["sale_date"] <= end_date)]
    recent = window.groupby("product_id", as_index=False)["units_sold"].sum()
    return recent.rename(columns={"units_sold": "recent_units_sold"})


def average_daily_sales(sales, reference_date, days):
    return units_sold_in_window(sales, reference_date, days) / float(days)


def sales_trend(sales, reference_date=None, window_days=COMPARISON_WINDOW_DAYS):
    empty_result = {
        "direction": TREND_STABLE,
        "change_ratio": 0.0,
        "is_variable": False,
        "recent_units": 0,
        "previous_units": 0,
    }
    if sales.empty:
        return empty_result
    reference = pd.Timestamp(reference_date) if reference_date else sales["sale_date"].max()
    recent_start, recent_end = window_bounds(reference, window_days)
    previous_start, previous_end = window_bounds(recent_start - pd.Timedelta(days=1), window_days)
    recent = sales[(sales["sale_date"] >= recent_start) & (sales["sale_date"] <= recent_end)]
    previous = sales[(sales["sale_date"] >= previous_start) & (sales["sale_date"] <= previous_end)]
    if recent.empty or previous.empty:
        return empty_result
    recent_units = int(recent["units_sold"].sum())
    previous_units = int(previous["units_sold"].sum())
    change_ratio = (recent_units - previous_units) / previous_units if previous_units else 0.0
    daily_recent = recent.groupby("sale_date")["units_sold"].sum()
    mean_daily = daily_recent.mean()
    variability = daily_recent.std() / mean_daily if mean_daily else 0.0
    if change_ratio > TREND_SENSITIVITY:
        direction = TREND_RISING
    elif change_ratio < -TREND_SENSITIVITY:
        direction = TREND_DECLINING
    else:
        direction = TREND_STABLE
    return {
        "direction": direction,
        "change_ratio": float(change_ratio),
        "is_variable": bool(variability > VARIABILITY_SENSITIVITY),
        "recent_units": recent_units,
        "previous_units": previous_units,
    }


def promotion_response(sales):
    if sales.empty or sales["on_promotion"].nunique() < 2:
        return pd.DataFrame(columns=["product_id", "product_name", "uplift_ratio"])
    grouped = sales.groupby(["product_id", "product_name", "on_promotion"])["units_sold"].mean()
    pivoted = grouped.unstack("on_promotion")
    if 0 not in pivoted.columns or 1 not in pivoted.columns:
        return pd.DataFrame(columns=["product_id", "product_name", "uplift_ratio"])
    pivoted = pivoted.dropna()
    pivoted = pivoted[pivoted[0] > 0]
    response = pivoted.reset_index()
    response["uplift_ratio"] = response[1] / response[0]
    response = response[["product_id", "product_name", "uplift_ratio"]]
    return response.sort_values("uplift_ratio", ascending=False).reset_index(drop=True)


def stockout_days(sales, reference_date, days):
    start_date, end_date = window_bounds(reference_date, days)
    window = sales[(sales["sale_date"] >= start_date) & (sales["sale_date"] <= end_date)]
    empty_days = window[window["stock_on_hand"] == 0]
    counts = empty_days.groupby("product_id", as_index=False).size()
    return counts.rename(columns={"size": "days_without_stock"})


def sales_share_of_total(sales, category):
    totals = sales_by_category(sales)
    if totals.empty:
        return 0.0
    matched = totals[totals["category"] == category]
    return float(matched["share"].iloc[0]) if len(matched) else 0.0


def demand_concentration(sales, top_count=5):
    summary = product_sales_summary(sales)
    total = summary["units_sold"].sum()
    if not total:
        return 0.0
    return float(summary.head(top_count)["units_sold"].sum() / total)


def weekday_versus_weekend(sales):
    pattern = weekday_demand_pattern(sales)
    if pattern.empty:
        return 0.0
    weekdays = pattern[~pattern["weekday"].isin(["Saturday", "Sunday"])]["average_units"]
    weekend = pattern[pattern["weekday"].isin(["Saturday", "Sunday"])]["average_units"]
    if weekend.empty or np.isclose(weekend.mean(), 0.0):
        return 0.0
    return float(weekdays.mean() / weekend.mean())

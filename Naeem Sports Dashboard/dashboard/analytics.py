from __future__ import annotations

import numpy as np
import pandas as pd

PERIOD_CHOICES = {
    "Last 7 Days": 7,
    "Last 30 Days": 30,
    "Last 90 Days": 90,
    "Last 6 Months": 182,
    "Last 12 Months": 365,
}

GRAIN_CHOICES = ("Daily", "Weekly", "Monthly")

WEEKDAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

MONTH_ORDER = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

ALL_SPORTS = "All Sports"


def period_start(latest_day, days):
    return latest_day - pd.Timedelta(days=days - 1)


def slice_by_dates(sales, start, end):
    within = (sales["sale_date"] >= pd.Timestamp(start)) & (sales["sale_date"] <= pd.Timestamp(end))
    return sales.loc[within].copy()


def slice_by_category(sales, category):
    if not category or category == ALL_SPORTS:
        return sales.copy()
    return sales.loc[sales["category"] == category].copy()


def totals(sales):
    if sales.empty:
        return {"revenue": 0.0, "units": 0, "orders": 0, "active_days": 0}
    return {
        "revenue": float(sales["revenue"].sum()),
        "units": int(sales["units_sold"].sum()),
        "orders": int(len(sales)),
        "active_days": int(sales["sale_date"].nunique()),
    }


def sales_by_grain(sales, grain):
    if sales.empty:
        return pd.DataFrame(columns=["period", "revenue", "units"])

    rule = {"Daily": "D", "Weekly": "W-MON", "Monthly": "MS"}[grain]
    aggregated = (
        sales.set_index("sale_date")
        .resample(rule)
        .agg(revenue=("revenue", "sum"), units=("units_sold", "sum"))
        .fillna(0.0)
        .reset_index()
        .rename(columns={"sale_date": "period"})
    )
    aggregated["units"] = aggregated["units"].astype(int)
    return aggregated


def category_performance(sales):
    if sales.empty:
        return pd.DataFrame(columns=["category", "revenue", "units", "products", "share"])

    performance = (
        sales.groupby("category")
        .agg(
            revenue=("revenue", "sum"),
            units=("units_sold", "sum"),
            products=("product_id", "nunique"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    total_revenue = performance["revenue"].sum()
    performance["share"] = np.where(
        total_revenue > 0, performance["revenue"] / total_revenue * 100.0, 0.0
    )
    return performance.reset_index(drop=True)


def product_leaderboard(sales, top_n=None):
    if sales.empty:
        return pd.DataFrame(columns=["product_id", "product_name", "category", "units", "revenue"])

    leaderboard = (
        sales.groupby(["product_id", "product_name", "category"])
        .agg(units=("units_sold", "sum"), revenue=("revenue", "sum"))
        .reset_index()
        .sort_values(["units", "revenue"], ascending=False)
        .reset_index(drop=True)
    )
    leaderboard.insert(0, "rank", np.arange(1, len(leaderboard) + 1))
    return leaderboard.head(top_n) if top_n else leaderboard


def weekday_pattern(sales):
    if sales.empty:
        return pd.DataFrame(columns=["weekday", "revenue", "units", "average_revenue"])

    working = sales.copy()
    working["weekday"] = working["sale_date"].dt.day_name()
    working["day_key"] = working["sale_date"].dt.normalize()

    pattern = (
        working.groupby("weekday")
        .agg(
            revenue=("revenue", "sum"),
            units=("units_sold", "sum"),
            days=("day_key", "nunique"),
        )
        .reindex(WEEKDAY_ORDER)
        .fillna(0.0)
        .reset_index()
    )
    pattern["average_revenue"] = np.where(
        pattern["days"] > 0, pattern["revenue"] / pattern["days"], 0.0
    )
    pattern["units"] = pattern["units"].astype(int)
    return pattern


def monthly_seasonality(sales):
    if sales.empty:
        return pd.DataFrame(columns=["month", "category", "average_units"])

    working = sales.copy()
    working["month"] = working["sale_date"].dt.month_name()
    working["day_key"] = working["sale_date"].dt.normalize()

    seasonality = (
        working.groupby(["month", "category"])
        .agg(units=("units_sold", "sum"), days=("day_key", "nunique"))
        .reset_index()
    )
    seasonality["average_units"] = np.where(
        seasonality["days"] > 0, seasonality["units"] / seasonality["days"], 0.0
    )
    seasonality["month"] = pd.Categorical(
        seasonality["month"], categories=MONTH_ORDER, ordered=True
    )
    return seasonality.sort_values(["month", "category"]).reset_index(drop=True)


def seasonal_peak_by_category(sales):
    seasonality = monthly_seasonality(sales)
    if seasonality.empty:
        return pd.DataFrame(columns=["category", "month", "average_units", "swing"])

    peaks = []
    for category, block in seasonality.groupby("category", observed=True):
        if block["average_units"].sum() <= 0:
            continue
        strongest = block.loc[block["average_units"].idxmax()]
        quietest = block.loc[block["average_units"].idxmin()]
        baseline = max(quietest["average_units"], 0.1)
        peaks.append(
            {
                "category": category,
                "month": str(strongest["month"]),
                "average_units": float(strongest["average_units"]),
                "quiet_month": str(quietest["month"]),
                "swing": float(strongest["average_units"] / baseline),
            }
        )
    return pd.DataFrame(peaks).sort_values("swing", ascending=False).reset_index(drop=True)


def _window_units(sales, start, end):
    window = slice_by_dates(sales, start, end)
    if window.empty:
        return pd.Series(dtype=float)
    return window.groupby("product_id")["units_sold"].sum()


def product_momentum(sales, latest_day, window=28):
    if sales.empty:
        return pd.DataFrame(
            columns=["product_id", "product_name", "category", "recent", "previous", "change_pct"]
        )

    recent_start = latest_day - pd.Timedelta(days=window - 1)
    previous_end = recent_start - pd.Timedelta(days=1)
    previous_start = previous_end - pd.Timedelta(days=window - 1)

    recent = _window_units(sales, recent_start, latest_day)
    previous = _window_units(sales, previous_start, previous_end)

    catalog = sales[["product_id", "product_name", "category"]].drop_duplicates("product_id")
    momentum = catalog.copy()
    momentum["recent"] = momentum["product_id"].map(recent).fillna(0.0)
    momentum["previous"] = momentum["product_id"].map(previous).fillna(0.0)
    momentum["change"] = momentum["recent"] - momentum["previous"]
    momentum["change_pct"] = np.where(
        momentum["previous"] > 0,
        momentum["change"] / momentum["previous"] * 100.0,
        np.where(momentum["recent"] > 0, 100.0, 0.0),
    )
    return momentum.sort_values("change_pct", ascending=False).reset_index(drop=True)


def rising_products(sales, latest_day, window=28, minimum_recent=15, top_n=6):
    momentum = product_momentum(sales, latest_day, window)
    if momentum.empty:
        return momentum
    gaining = momentum.loc[
        (momentum["change_pct"] > 10) & (momentum["recent"] >= minimum_recent)
    ]
    return gaining.head(top_n).reset_index(drop=True)


def slow_movers(sales, latest_day, window=90, bottom_n=6):
    if sales.empty:
        return pd.DataFrame(
            columns=["product_id", "product_name", "category", "units", "revenue", "quiet_days"]
        )

    start = latest_day - pd.Timedelta(days=window - 1)
    recent = slice_by_dates(sales, start, latest_day)
    catalog = sales[["product_id", "product_name", "category"]].drop_duplicates("product_id")

    grouped = recent.groupby("product_id").agg(
        units=("units_sold", "sum"),
        revenue=("revenue", "sum"),
        last_sale=("sale_date", "max"),
    )
    movers = catalog.merge(grouped, on="product_id", how="left")
    movers["units"] = movers["units"].fillna(0).astype(int)
    movers["revenue"] = movers["revenue"].fillna(0.0)
    movers["quiet_days"] = (latest_day - movers["last_sale"]).dt.days.fillna(window).astype(int)
    movers["daily_average"] = movers["units"] / window
    return movers.sort_values(["units", "revenue"]).head(bottom_n).reset_index(drop=True)


def overall_momentum(sales, latest_day, window=14):
    recent_start = latest_day - pd.Timedelta(days=window - 1)
    previous_end = recent_start - pd.Timedelta(days=1)
    previous_start = previous_end - pd.Timedelta(days=window - 1)

    recent = totals(slice_by_dates(sales, recent_start, latest_day))
    previous = totals(slice_by_dates(sales, previous_start, previous_end))

    change_pct = 0.0
    if previous["revenue"] > 0:
        change_pct = (recent["revenue"] - previous["revenue"]) / previous["revenue"] * 100.0
    elif recent["revenue"] > 0:
        change_pct = 100.0

    return {
        "window": window,
        "recent_revenue": recent["revenue"],
        "previous_revenue": previous["revenue"],
        "recent_units": recent["units"],
        "previous_units": previous["units"],
        "change_pct": change_pct,
        "recent_start": recent_start,
        "previous_start": previous_start,
        "previous_end": previous_end,
    }


def recent_daily_average(sales, latest_day, window=28):
    start = latest_day - pd.Timedelta(days=window - 1)
    recent = slice_by_dates(sales, start, latest_day)
    if recent.empty:
        return pd.Series(dtype=float)
    return recent.groupby("product_id")["units_sold"].sum() / window


def product_daily_history(daily_sales, product_id, days, latest_day):
    start = latest_day - pd.Timedelta(days=days - 1)
    history = daily_sales.loc[
        (daily_sales["product_id"] == product_id)
        & (daily_sales["date"] >= start)
        & (daily_sales["date"] <= latest_day)
    ]
    return history[["date", "units"]].reset_index(drop=True)

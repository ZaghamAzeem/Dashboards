from __future__ import annotations

import numpy as np

STATUS_GOOD = "Good Stock"
STATUS_LOW = "Running Low"
STATUS_RESTOCK = "Restock Needed"
STATUS_OUT = "Out of Stock"

STATUS_PRIORITY = [STATUS_OUT, STATUS_RESTOCK, STATUS_LOW, STATUS_GOOD]

STATUS_BADGE = {
    STATUS_GOOD: "🟢",
    STATUS_LOW: "🟡",
    STATUS_RESTOCK: "🔴",
    STATUS_OUT: "⚫",
}

STATUS_COLOR = {
    STATUS_GOOD: "#16A34A",
    STATUS_LOW: "#F59E0B",
    STATUS_RESTOCK: "#EF4444",
    STATUS_OUT: "#475569",
}

STATUS_ACTION = {
    STATUS_GOOD: "Stock Looks Good",
    STATUS_LOW: "Keep An Eye On Stock",
    STATUS_RESTOCK: "Restock Soon",
    STATUS_OUT: "Order Immediately",
}

STATUS_NOTE = {
    STATUS_GOOD: "Stock comfortably covers the demand expected this week.",
    STATUS_LOW: "Stock is getting close to the demand expected this week.",
    STATUS_RESTOCK: "Expected demand is higher than the stock on the shelf.",
    STATUS_OUT: "Nothing left on the shelf, so every sale is being missed.",
}

PRIORITY_HIGH = "HIGH PRIORITY"
PRIORITY_WATCH = "WATCH"
PRIORITY_NONE = "NO ACTION"

LOW_STOCK_MULTIPLIER = 1.75
RISING_THRESHOLD = 15.0
SLOWING_THRESHOLD = -15.0
MOMENTUM_UP = 8.0
MOMENTUM_DOWN = -8.0

MOMENTUM_FASTER = "Selling Faster"
MOMENTUM_STEADY = "Holding Steady"
MOMENTUM_SLOWER = "Moving Slowly"


def classify_stock_status(current_stock, expected_demand):
    stock = max(float(current_stock), 0.0)
    demand = max(float(expected_demand), 0.0)

    if stock <= 0:
        return STATUS_OUT
    if demand <= 0:
        return STATUS_GOOD
    if stock < demand:
        return STATUS_RESTOCK
    if stock < demand * LOW_STOCK_MULTIPLIER:
        return STATUS_LOW
    return STATUS_GOOD


def cover_days(current_stock, expected_demand, horizon=7):
    daily_demand = max(float(expected_demand), 0.0) / horizon
    if daily_demand <= 0:
        return float("inf")
    return max(float(current_stock), 0.0) / daily_demand


def restock_priority(status):
    if status in (STATUS_OUT, STATUS_RESTOCK):
        return PRIORITY_HIGH
    if status == STATUS_LOW:
        return PRIORITY_WATCH
    return PRIORITY_NONE


def suggested_action(status):
    return STATUS_ACTION[status]


def momentum_label(change_pct):
    if change_pct >= RISING_THRESHOLD:
        return MOMENTUM_FASTER
    if change_pct <= SLOWING_THRESHOLD:
        return MOMENTUM_SLOWER
    return MOMENTUM_STEADY


def sales_momentum_headline(change_pct):
    if change_pct >= MOMENTUM_UP:
        return "Sales are picking up"
    if change_pct <= MOMENTUM_DOWN:
        return "Sales have slowed recently"
    return "Sales are relatively stable"


def build_stock_overview(products, expected_demand, recent_daily_units=None):
    overview = products.copy()
    overview["expected_demand"] = (
        overview["product_id"].map(expected_demand).fillna(0.0).clip(lower=0.0)
    )
    if recent_daily_units is not None:
        overview["recent_daily_units"] = (
            overview["product_id"].map(recent_daily_units).fillna(0.0).clip(lower=0.0)
        )
    else:
        overview["recent_daily_units"] = overview["expected_demand"] / 7.0

    overview["current_stock"] = overview["current_stock"].clip(lower=0).astype(int)
    overview["status"] = [
        classify_stock_status(stock, demand)
        for stock, demand in zip(overview["current_stock"], overview["expected_demand"])
    ]
    overview["cover_days"] = [
        cover_days(stock, demand)
        for stock, demand in zip(overview["current_stock"], overview["expected_demand"])
    ]
    overview["priority"] = overview["status"].map(restock_priority)
    overview["action"] = overview["status"].map(suggested_action)
    overview["shortfall"] = (overview["expected_demand"] - overview["current_stock"]).clip(lower=0)
    overview["status_rank"] = overview["status"].map(
        {status: rank for rank, status in enumerate(STATUS_PRIORITY)}
    )
    return overview.sort_values(
        ["status_rank", "shortfall"], ascending=[True, False]
    ).reset_index(drop=True)


def status_counts(overview):
    counts = overview["status"].value_counts()
    return {status: int(counts.get(status, 0)) for status in STATUS_PRIORITY}


def products_needing_attention(overview):
    return overview.loc[overview["status"] != STATUS_GOOD].reset_index(drop=True)


def shopping_list(overview):
    groups = {}
    for priority in (PRIORITY_HIGH, PRIORITY_WATCH, PRIORITY_NONE):
        block = overview.loc[overview["priority"] == priority].copy()
        if priority == PRIORITY_NONE:
            block = block.sort_values("expected_demand", ascending=False)
        groups[priority] = block.reset_index(drop=True)
    return groups


def describe_forecast(current_stock, expected_demand, change_pct):
    status = classify_stock_status(current_stock, expected_demand)
    trend = momentum_label(change_pct)

    if status == STATUS_OUT:
        return (
            "There is nothing left on the shelf and customers are still asking for this item. "
            "Every day it stays empty is a sale going to another shop."
        )
    if status == STATUS_RESTOCK:
        shortfall = int(round(max(expected_demand - current_stock, 0)))
        return (
            f"Demand is expected to stay strong and current stock may not be enough. "
            f"Roughly {shortfall} more units than the shelf holds could be asked for this week."
        )
    if status == STATUS_LOW:
        return (
            "Stock will probably last the week, but there is very little spare. "
            "It is worth ordering before the shelf empties."
        )
    if trend == MOMENTUM_SLOWER:
        return (
            "Recent sales have slowed and there is plenty on the shelf, "
            "so immediate replenishment does not look necessary."
        )
    return "Current stock appears comfortable for the demand expected over the coming week."


def describe_product_recommendation(status, change_pct):
    trend = momentum_label(change_pct)

    if status == STATUS_OUT:
        return "This product has run out while customers are still buying it. Order it first."
    if status == STATUS_RESTOCK and trend == MOMENTUM_FASTER:
        return "This product is selling quickly and current stock may become insufficient."
    if status == STATUS_RESTOCK:
        return "Stock is below the demand expected this week, so a fresh order is advisable."
    if status == STATUS_LOW:
        return "Stock is thinning out. Keeping an eye on it this week would be sensible."
    if trend == MOMENTUM_FASTER:
        return "Sales are speeding up and stock is healthy, so this product is in a good position."
    if trend == MOMENTUM_SLOWER:
        return "Sales have eased off and stock is comfortable. There is no need to order more yet."
    return "Sales and stock are both steady. No action is needed at the moment."


def category_leader(performance):
    if performance.empty:
        return None
    leader = performance.iloc[0]
    return {
        "category": leader["category"],
        "revenue": float(leader["revenue"]),
        "units": int(leader["units"]),
        "share": float(leader["share"]),
    }


def busiest_weekday(pattern):
    if pattern.empty or pattern["revenue"].sum() <= 0:
        return None
    busiest = pattern.loc[pattern["average_revenue"].idxmax()]
    quietest = pattern.loc[pattern["average_revenue"].idxmin()]
    average = pattern["average_revenue"].mean()
    lift = 0.0
    if average > 0:
        lift = (busiest["average_revenue"] - average) / average * 100.0
    return {
        "weekday": busiest["weekday"],
        "quietest": quietest["weekday"],
        "average_revenue": float(busiest["average_revenue"]),
        "lift_pct": float(lift),
    }


def format_currency(value, compact=True):
    amount = float(value)
    if not np.isfinite(amount):
        return "Rs 0"
    if compact and abs(amount) >= 10_000_000:
        return f"Rs {amount / 10_000_000:,.2f} Cr"
    if compact and abs(amount) >= 100_000:
        return f"Rs {amount / 100_000:,.1f} Lac"
    return f"Rs {amount:,.0f}"


def format_units(value):
    number = float(value)
    if not np.isfinite(number):
        return "0"
    return f"{number:,.0f}"


def format_change(change_pct):
    if not np.isfinite(change_pct):
        return "0%"
    arrow = "▲" if change_pct > 0 else ("▼" if change_pct < 0 else "▬")
    return f"{arrow} {abs(change_pct):.1f}%"


def format_cover(days):
    if not np.isfinite(days):
        return "No demand expected"
    if days <= 0:
        return "Nothing left on the shelf"
    if days >= 60:
        return "More than 2 months"
    if days < 1:
        return "Less than a day"
    if days < 2:
        return "About a day"
    return f"About {days:.0f} days"

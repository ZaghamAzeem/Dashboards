import numpy as np
import pandas as pd

HEALTHY = "Healthy"
ATTENTION = "Attention"
CRITICAL = "Critical"
OUT_OF_STOCK = "Out of Stock"

STATUS_SEQUENCE = [OUT_OF_STOCK, CRITICAL, ATTENTION, HEALTHY]
STATUS_ICONS = {
    HEALTHY: "🟢",
    ATTENTION: "🟡",
    CRITICAL: "🔴",
    OUT_OF_STOCK: "⚫",
}

RESTOCK_SOON = "Restock Soon"
REVIEW_INVENTORY = "Review Inventory"
NO_IMMEDIATE_ACTION = "No Immediate Action"

CRITICAL_COVERAGE = 0.75
ATTENTION_COVERAGE = 1.25


def classify_inventory_status(current_stock, expected_demand):
    stock = max(0, int(current_stock))
    demand = max(0.0, float(expected_demand))
    if stock == 0:
        return OUT_OF_STOCK
    if demand <= 0:
        return HEALTHY
    coverage = stock / demand
    if coverage < CRITICAL_COVERAGE:
        return CRITICAL
    if coverage < ATTENTION_COVERAGE:
        return ATTENTION
    return HEALTHY


def suggested_action(status):
    if status in (OUT_OF_STOCK, CRITICAL):
        return RESTOCK_SOON
    if status == ATTENTION:
        return REVIEW_INVENTORY
    return NO_IMMEDIATE_ACTION


def coverage_ratio(current_stock, expected_demand):
    demand = max(0.0, float(expected_demand))
    if demand <= 0:
        return float("inf") if current_stock > 0 else 0.0
    return float(current_stock) / demand


def days_of_cover(current_stock, expected_demand, horizon_days=7):
    daily_demand = max(0.0, float(expected_demand)) / horizon_days
    if daily_demand <= 0:
        return float("inf") if current_stock > 0 else 0.0
    return float(current_stock) / daily_demand


def status_priority(status):
    return STATUS_SEQUENCE.index(status) if status in STATUS_SEQUENCE else len(STATUS_SEQUENCE)


def build_inventory_status(inventory, expected_demand, recent_sales=None):
    status_table = inventory.merge(expected_demand, on="product_id", how="left")
    status_table["expected_demand"] = status_table["expected_demand"].fillna(0).astype(int)
    if recent_sales is not None:
        status_table = status_table.merge(recent_sales, on="product_id", how="left")
        status_table["recent_units_sold"] = (
            status_table["recent_units_sold"].fillna(0).astype(int)
        )
    status_table["status"] = [
        classify_inventory_status(stock, demand)
        for stock, demand in zip(status_table["current_stock"], status_table["expected_demand"])
    ]
    status_table["suggested_action"] = status_table["status"].map(suggested_action)
    status_table["coverage"] = [
        coverage_ratio(stock, demand)
        for stock, demand in zip(status_table["current_stock"], status_table["expected_demand"])
    ]
    status_table["days_of_cover"] = [
        days_of_cover(stock, demand)
        for stock, demand in zip(status_table["current_stock"], status_table["expected_demand"])
    ]
    status_table["shortfall"] = (
        status_table["expected_demand"] - status_table["current_stock"]
    ).clip(lower=0)
    status_table["priority"] = status_table["status"].map(status_priority)
    status_table = status_table.sort_values(
        ["priority", "coverage", "expected_demand"], ascending=[True, True, False]
    )
    return status_table.reset_index(drop=True)


def status_counts(status_table):
    counts = status_table["status"].value_counts().to_dict()
    return {status: int(counts.get(status, 0)) for status in STATUS_SEQUENCE}


def products_needing_attention(status_table):
    return status_table[status_table["status"].isin([OUT_OF_STOCK, CRITICAL, ATTENTION])].copy()


def urgent_products(status_table):
    return status_table[status_table["status"].isin([OUT_OF_STOCK, CRITICAL])].copy()


def in_stock_count(status_table):
    return int((status_table["current_stock"] > 0).sum())


def low_stock_count(status_table):
    counts = status_counts(status_table)
    return counts[CRITICAL] + counts[ATTENTION]


def format_days_of_cover(value):
    if not np.isfinite(value):
        return "No demand expected"
    if value <= 0:
        return "No stock available"
    if value >= 60:
        return "Over 60 days of cover"
    if value < 1.5:
        return "Around a day of cover"
    return f"About {int(round(value))} days of cover"


def status_summary_frame(status_table):
    counts = status_counts(status_table)
    return pd.DataFrame(
        {
            "status": list(counts.keys()),
            "products": list(counts.values()),
        }
    )

import numpy as np
import pandas as pd
import pytest

from dashboard import business_logic


@pytest.fixture
def status_inputs():
    inventory = pd.DataFrame(
        {
            "product_id": ["P1", "P2", "P3", "P4"],
            "product_name": ["Healthy Item", "Watch Item", "Short Item", "Empty Item"],
            "category": ["Medical Supplies"] * 4,
            "unit_of_measure": ["boxes"] * 4,
            "current_stock": [300, 105, 30, 0],
        }
    )
    expected_demand = pd.DataFrame(
        {"product_id": ["P1", "P2", "P3", "P4"], "expected_demand": [100, 100, 100, 100]}
    )
    recent_sales = pd.DataFrame(
        {"product_id": ["P1", "P2", "P3", "P4"], "recent_units_sold": [90, 99, 88, 12]}
    )
    return inventory, expected_demand, recent_sales


def test_healthy_status_when_stock_covers_demand():
    assert business_logic.classify_inventory_status(300, 100) == business_logic.HEALTHY


def test_attention_status_when_stock_is_close_to_demand():
    assert business_logic.classify_inventory_status(105, 100) == business_logic.ATTENTION
    assert business_logic.classify_inventory_status(80, 100) == business_logic.ATTENTION


def test_critical_status_when_stock_is_well_below_demand():
    assert business_logic.classify_inventory_status(30, 100) == business_logic.CRITICAL


def test_out_of_stock_status_takes_priority():
    assert business_logic.classify_inventory_status(0, 100) == business_logic.OUT_OF_STOCK
    assert business_logic.classify_inventory_status(0, 0) == business_logic.OUT_OF_STOCK


def test_no_expected_demand_is_treated_as_healthy():
    assert business_logic.classify_inventory_status(25, 0) == business_logic.HEALTHY


def test_status_boundaries_follow_the_configured_thresholds():
    demand = 100
    critical_edge = business_logic.CRITICAL_COVERAGE * demand
    attention_edge = business_logic.ATTENTION_COVERAGE * demand
    assert business_logic.classify_inventory_status(critical_edge - 1, demand) == (
        business_logic.CRITICAL
    )
    assert business_logic.classify_inventory_status(critical_edge, demand) == (
        business_logic.ATTENTION
    )
    assert business_logic.classify_inventory_status(attention_edge, demand) == (
        business_logic.HEALTHY
    )


def test_suggested_actions_match_each_status():
    assert business_logic.suggested_action(business_logic.OUT_OF_STOCK) == (
        business_logic.RESTOCK_SOON
    )
    assert business_logic.suggested_action(business_logic.CRITICAL) == (
        business_logic.RESTOCK_SOON
    )
    assert business_logic.suggested_action(business_logic.ATTENTION) == (
        business_logic.REVIEW_INVENTORY
    )
    assert business_logic.suggested_action(business_logic.HEALTHY) == (
        business_logic.NO_IMMEDIATE_ACTION
    )


def test_days_of_cover_reflects_daily_demand():
    assert business_logic.days_of_cover(70, 70) == pytest.approx(7.0)
    assert business_logic.days_of_cover(140, 70) == pytest.approx(14.0)
    assert not np.isfinite(business_logic.days_of_cover(10, 0))
    assert business_logic.days_of_cover(0, 70) == 0.0


def test_inventory_status_table_is_complete(status_inputs):
    inventory, expected_demand, recent_sales = status_inputs
    table = business_logic.build_inventory_status(inventory, expected_demand, recent_sales)
    assert len(table) == 4
    for column in ["status", "suggested_action", "coverage", "days_of_cover", "shortfall"]:
        assert column in table.columns
    assert dict(zip(table["product_id"], table["status"])) == {
        "P1": business_logic.HEALTHY,
        "P2": business_logic.ATTENTION,
        "P3": business_logic.CRITICAL,
        "P4": business_logic.OUT_OF_STOCK,
    }


def test_inventory_status_table_puts_urgent_products_first(status_inputs):
    inventory, expected_demand, recent_sales = status_inputs
    table = business_logic.build_inventory_status(inventory, expected_demand, recent_sales)
    assert list(table["product_id"]) == ["P4", "P3", "P2", "P1"]


def test_shortfall_is_never_negative(status_inputs):
    inventory, expected_demand, recent_sales = status_inputs
    table = business_logic.build_inventory_status(inventory, expected_demand, recent_sales)
    assert (table["shortfall"] >= 0).all()
    assert int(table.loc[table["product_id"] == "P3", "shortfall"].iloc[0]) == 70


def test_missing_forecast_is_handled_safely(status_inputs):
    inventory, _, recent_sales = status_inputs
    partial_demand = pd.DataFrame({"product_id": ["P1"], "expected_demand": [100]})
    table = business_logic.build_inventory_status(inventory, partial_demand, recent_sales)
    assert (table["expected_demand"] >= 0).all()
    assert set(table["status"]) <= set(business_logic.STATUS_SEQUENCE)


def test_status_counts_and_summaries(status_inputs):
    inventory, expected_demand, recent_sales = status_inputs
    table = business_logic.build_inventory_status(inventory, expected_demand, recent_sales)
    counts = business_logic.status_counts(table)
    assert counts == {
        business_logic.OUT_OF_STOCK: 1,
        business_logic.CRITICAL: 1,
        business_logic.ATTENTION: 1,
        business_logic.HEALTHY: 1,
    }
    assert business_logic.in_stock_count(table) == 3
    assert business_logic.low_stock_count(table) == 2
    assert len(business_logic.urgent_products(table)) == 2
    assert len(business_logic.products_needing_attention(table)) == 3
    assert business_logic.status_summary_frame(table)["products"].sum() == 4


def test_days_of_cover_is_presented_in_plain_language():
    assert business_logic.format_days_of_cover(14.0) == "About 14 days of cover"
    assert business_logic.format_days_of_cover(float("inf")) == "No demand expected"
    assert business_logic.format_days_of_cover(120.0) == "Over 60 days of cover"
    assert business_logic.format_days_of_cover(0.0) == "No stock available"
    assert business_logic.format_days_of_cover(1.2) == "Around a day of cover"

from __future__ import annotations

import sqlite3

import pandas as pd
import pytest

from data import make_dataset


@pytest.fixture(scope="module")
def generated_tables(tmp_path_factory):
    database_path = tmp_path_factory.mktemp("shop") / "sports_shop.db"
    summary = make_dataset.generate(database_path)

    connection = sqlite3.connect(database_path)
    try:
        tables = {
            "products": pd.read_sql("SELECT * FROM products", connection),
            "sales": pd.read_sql("SELECT * FROM sales_transactions", connection),
            "movements": pd.read_sql("SELECT * FROM inventory_movements", connection),
        }
    finally:
        connection.close()

    tables["sales"]["sale_date"] = pd.to_datetime(tables["sales"]["sale_date"])
    tables["movements"]["movement_date"] = pd.to_datetime(tables["movements"]["movement_date"])
    tables["summary"] = summary
    return tables


def test_catalog_size_is_in_the_expected_range(generated_tables):
    products = generated_tables["products"]
    assert 30 <= len(products) <= 50
    assert products["product_id"].is_unique
    assert products["product_name"].is_unique


def test_catalog_values_are_valid(generated_tables):
    products = generated_tables["products"]
    assert (products["unit_price"] > 0).all()
    assert (products["current_stock"] >= 0).all()
    assert (products["reorder_level"] > 0).all()
    assert not products[["product_name", "category", "subcategory"]].isna().any().any()


def test_catalog_covers_every_sport(generated_tables):
    categories = set(generated_tables["products"]["category"])
    assert categories == set(make_dataset.SEASONAL_SHAPE)


def test_sales_history_spans_two_years(generated_tables):
    sales = generated_tables["sales"]
    span = (sales["sale_date"].max() - sales["sale_date"].min()).days
    assert span >= make_dataset.HISTORY_DAYS - 10


def test_sales_rows_are_valid(generated_tables):
    sales = generated_tables["sales"]
    assert (sales["units_sold"] > 0).all()
    assert (sales["revenue"] >= 0).all()
    assert (sales["unit_price"] > 0).all()
    assert sales["sale_date"].notna().all()
    assert sales["transaction_id"].is_unique


def test_sales_reference_known_products(generated_tables):
    known = set(generated_tables["products"]["product_id"])
    assert set(generated_tables["sales"]["product_id"]).issubset(known)


def test_promotions_reduce_the_selling_price(generated_tables):
    sales = generated_tables["sales"]
    discounted = sales.loc[sales["discount_pct"] > 0]
    assert not discounted.empty
    assert (discounted["discount_pct"] <= 25).all()


def test_inventory_movements_are_consistent(generated_tables):
    movements = generated_tables["movements"]
    sales_moves = movements.loc[movements["movement_type"] == "Sale"]
    restocks = movements.loc[movements["movement_type"] == "Restock"]

    assert (sales_moves["quantity_change"] < 0).all()
    assert (restocks["quantity_change"] > 0).all()
    assert (movements["stock_after"] >= 0).all()
    assert not restocks.empty


def test_demand_varies_between_products(generated_tables):
    units = generated_tables["sales"].groupby("product_id")["units_sold"].sum()
    assert units.max() > units.min() * 3


def test_weekend_trade_is_stronger_than_midweek(generated_tables):
    sales = generated_tables["sales"].copy()
    sales["weekday"] = sales["sale_date"].dt.dayofweek
    by_day = sales.groupby("weekday")["units_sold"].sum()
    assert by_day.loc[5] > by_day.loc[1]


def test_stock_levels_are_mixed(generated_tables):
    stock = generated_tables["products"]["current_stock"]
    assert (stock >= 0).all()
    assert stock.nunique() > 5


def test_history_contains_stockouts_and_replenishment(generated_tables):
    movements = generated_tables["movements"]
    assert (movements["stock_after"] == 0).any()
    assert (movements["movement_type"] == "Restock").sum() > len(
        generated_tables["products"]
    )


def test_summary_matches_the_stored_tables(generated_tables):
    summary = generated_tables["summary"]
    assert summary["products"] == len(generated_tables["products"])
    assert summary["transactions"] == len(generated_tables["sales"])
    assert summary["units_sold"] == int(generated_tables["sales"]["units_sold"].sum())

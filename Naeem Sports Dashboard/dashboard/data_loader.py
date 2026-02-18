from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from dashboard import forecasting

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "sports_shop.db"

FRIENDLY_ERROR = "We couldn't load the shop information. Please refresh the dashboard."
SETUP_HINT = "The shop data has not been prepared yet."


class ShopDataUnavailable(Exception):
    pass


@dataclass(frozen=True)
class ShopData:
    products: pd.DataFrame
    sales: pd.DataFrame
    movements: pd.DataFrame
    daily_sales: pd.DataFrame
    loaded_at: datetime

    @property
    def latest_day(self):
        return self.sales["sale_date"].max()

    @property
    def earliest_day(self):
        return self.sales["sale_date"].min()

    @property
    def sports(self):
        return sorted(self.products["category"].unique())


def read_tables(database_path=DATABASE_PATH):
    if not Path(database_path).exists():
        raise ShopDataUnavailable(SETUP_HINT)

    connection = sqlite3.connect(database_path)
    try:
        products = pd.read_sql("SELECT * FROM products", connection)
        sales = pd.read_sql("SELECT * FROM sales_transactions", connection)
        movements = pd.read_sql("SELECT * FROM inventory_movements", connection)
    except (sqlite3.DatabaseError, pd.errors.DatabaseError) as error:
        raise ShopDataUnavailable(FRIENDLY_ERROR) from error
    finally:
        connection.close()

    if products.empty or sales.empty:
        raise ShopDataUnavailable(SETUP_HINT)
    return products, sales, movements


def clean_products(products):
    cleaned = products.drop_duplicates(subset="product_id").copy()
    cleaned = cleaned.dropna(subset=["product_id", "product_name", "category"])

    for column in ("unit_price", "current_stock", "reorder_level"):
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce").fillna(0)

    cleaned["current_stock"] = cleaned["current_stock"].clip(lower=0).astype(int)
    cleaned["reorder_level"] = cleaned["reorder_level"].clip(lower=0).astype(int)
    cleaned["unit_price"] = cleaned["unit_price"].clip(lower=0.0).astype(float)
    cleaned["subcategory"] = cleaned["subcategory"].fillna("General")
    return cleaned.reset_index(drop=True)


def clean_sales(sales, products):
    cleaned = sales.drop_duplicates(subset="transaction_id").copy()
    cleaned["sale_date"] = pd.to_datetime(cleaned["sale_date"], errors="coerce")
    cleaned = cleaned.dropna(subset=["sale_date", "product_id"])

    for column in ("units_sold", "unit_price", "revenue", "discount_pct"):
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce").fillna(0.0)

    cleaned = cleaned.loc[cleaned["units_sold"] > 0]
    cleaned = cleaned.loc[cleaned["revenue"] >= 0]
    cleaned = cleaned.loc[cleaned["product_id"].isin(products["product_id"])]
    cleaned["units_sold"] = cleaned["units_sold"].astype(int)

    enriched = cleaned.merge(
        products[["product_id", "product_name", "category", "subcategory"]],
        on="product_id",
        how="left",
    )
    return enriched.sort_values("sale_date").reset_index(drop=True)


def clean_movements(movements, products):
    if movements.empty:
        return movements

    cleaned = movements.drop_duplicates(subset="movement_id").copy()
    cleaned["movement_date"] = pd.to_datetime(cleaned["movement_date"], errors="coerce")
    cleaned = cleaned.dropna(subset=["movement_date", "product_id"])
    cleaned = cleaned.loc[cleaned["product_id"].isin(products["product_id"])]

    for column in ("quantity_change", "stock_after"):
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce").fillna(0).astype(int)

    cleaned["stock_after"] = cleaned["stock_after"].clip(lower=0)
    return cleaned.sort_values("movement_date").reset_index(drop=True)


def build_daily_sales(sales, products):
    if sales.empty:
        return pd.DataFrame(columns=["date", "product_id", "units", "revenue"])

    grouped = (
        sales.groupby([sales["sale_date"].dt.normalize(), "product_id"])
        .agg(units=("units_sold", "sum"), revenue=("revenue", "sum"))
        .reset_index()
        .rename(columns={"sale_date": "date"})
    )

    calendar = pd.date_range(grouped["date"].min(), grouped["date"].max(), freq="D")
    grid = pd.MultiIndex.from_product(
        [calendar, products["product_id"]], names=["date", "product_id"]
    )
    complete = (
        grouped.set_index(["date", "product_id"])
        .reindex(grid, fill_value=0.0)
        .reset_index()
    )
    complete["units"] = complete["units"].astype(float)
    return complete.merge(
        products[["product_id", "product_name", "category"]], on="product_id", how="left"
    )


@st.cache_data(show_spinner=False)
def load_shop_data():
    products, sales, movements = read_tables()
    clean_catalog = clean_products(products)
    clean_sales_frame = clean_sales(sales, clean_catalog)

    if clean_sales_frame.empty:
        raise ShopDataUnavailable(SETUP_HINT)

    return ShopData(
        products=clean_catalog,
        sales=clean_sales_frame,
        movements=clean_movements(movements, clean_catalog),
        daily_sales=build_daily_sales(clean_sales_frame, clean_catalog),
        loaded_at=datetime.now(),
    )


@st.cache_data(show_spinner=False)
def load_expected_demand():
    shop = load_shop_data()
    forecast = forecasting.forecast_all_products(shop.daily_sales, shop.products)
    return forecast


def refresh():
    load_shop_data.clear()
    load_expected_demand.clear()

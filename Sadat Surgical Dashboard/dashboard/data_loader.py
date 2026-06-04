import sqlite3
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "sadat_surgical.db"
SETUP_COMMAND = "python data/make_dataset.py"

SALES_COLUMNS = ["sale_date", "product_id", "units_sold", "on_promotion", "stock_on_hand"]
PRODUCT_COLUMNS = ["product_id", "product_name", "category", "unit_of_measure"]


class BusinessDataUnavailable(Exception):
    pass


def business_data_is_available(database_path=DATABASE_PATH):
    return Path(database_path).exists()


def read_tables(database_path=DATABASE_PATH):
    if not business_data_is_available(database_path):
        raise BusinessDataUnavailable(str(database_path))
    connection = sqlite3.connect(f"file:{Path(database_path).as_posix()}?mode=ro", uri=True)
    try:
        products = pd.read_sql_query("SELECT * FROM products", connection)
        sales = pd.read_sql_query("SELECT * FROM daily_sales", connection)
        dataset_info = pd.read_sql_query("SELECT * FROM dataset_info", connection)
    finally:
        connection.close()
    return products, sales, dataset_info


def clean_products(products):
    cleaned = products.loc[:, PRODUCT_COLUMNS].copy()
    cleaned = cleaned.dropna(subset=["product_id", "product_name", "category"])
    cleaned = cleaned.drop_duplicates(subset="product_id")
    for column in ["product_id", "product_name", "category", "unit_of_measure"]:
        cleaned[column] = cleaned[column].astype(str).str.strip()
    return cleaned.sort_values("product_name").reset_index(drop=True)


def clean_sales(sales, products):
    cleaned = sales.loc[:, SALES_COLUMNS].copy()
    cleaned["sale_date"] = pd.to_datetime(cleaned["sale_date"], errors="coerce")
    cleaned = cleaned.dropna(subset=["sale_date", "product_id"])
    cleaned = cleaned[cleaned["product_id"].isin(products["product_id"])]
    for column in ["units_sold", "on_promotion", "stock_on_hand"]:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce").fillna(0)
        cleaned[column] = cleaned[column].clip(lower=0).astype(int)
    cleaned = cleaned.drop_duplicates(subset=["sale_date", "product_id"], keep="last")
    cleaned = cleaned.merge(products, on="product_id", how="left")
    return cleaned.sort_values(["sale_date", "product_id"]).reset_index(drop=True)


def load_business_data(database_path=DATABASE_PATH):
    raw_products, raw_sales, dataset_info = read_tables(database_path)
    products = clean_products(raw_products)
    sales = clean_sales(raw_sales, products)
    generated_on = str(dataset_info["generated_on"].iloc[0]) if len(dataset_info) else ""
    return products, sales, generated_on


def latest_business_date(sales):
    return sales["sale_date"].max()


def earliest_business_date(sales):
    return sales["sale_date"].min()


def current_inventory(products, sales):
    closing_day = latest_business_date(sales)
    closing_positions = sales[sales["sale_date"] == closing_day]
    closing_positions = closing_positions[["product_id", "stock_on_hand"]]
    closing_positions = closing_positions.rename(columns={"stock_on_hand": "current_stock"})
    inventory = products.merge(closing_positions, on="product_id", how="left")
    inventory["current_stock"] = inventory["current_stock"].fillna(0).astype(int)
    return inventory

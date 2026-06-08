import pandas as pd
import pytest

from dashboard import data_loader


@pytest.fixture
def messy_sales(sample_products):
    return pd.DataFrame(
        {
            "sale_date": ["2025-06-01", "2025-06-01", "not a date", "2025-06-02", "2025-06-02"],
            "product_id": ["SI-900", "SI-900", "SI-900", "MS-900", "UNKNOWN-1"],
            "units_sold": [10, 12, 5, -4, 7],
            "on_promotion": [0, 0, 0, 1, 0],
            "stock_on_hand": [40, 38, 10, -6, 20],
        }
    )


def test_missing_business_data_is_detected(tmp_path):
    assert not data_loader.business_data_is_available(tmp_path / "absent.db")


def test_reading_missing_business_data_raises_a_clear_error(tmp_path):
    with pytest.raises(data_loader.BusinessDataUnavailable):
        data_loader.read_tables(tmp_path / "absent.db")


def test_cleaning_removes_invalid_records(messy_sales, sample_products):
    cleaned = data_loader.clean_sales(messy_sales, sample_products)
    assert len(cleaned) == 2
    assert cleaned["sale_date"].notna().all()
    assert set(cleaned["product_id"]) <= set(sample_products["product_id"])


def test_cleaning_keeps_the_latest_duplicate(messy_sales, sample_products):
    cleaned = data_loader.clean_sales(messy_sales, sample_products)
    duplicated_day = cleaned[cleaned["product_id"] == "SI-900"]
    assert int(duplicated_day["units_sold"].iloc[0]) == 12


def test_cleaning_prevents_negative_quantities(messy_sales, sample_products):
    cleaned = data_loader.clean_sales(messy_sales, sample_products)
    assert (cleaned["units_sold"] >= 0).all()
    assert (cleaned["stock_on_hand"] >= 0).all()


def test_cleaning_attaches_product_details(messy_sales, sample_products):
    cleaned = data_loader.clean_sales(messy_sales, sample_products)
    assert {"product_name", "category", "unit_of_measure"} <= set(cleaned.columns)
    assert cleaned["product_name"].notna().all()


def test_current_inventory_uses_the_latest_closing_stock(sample_products, sample_sales):
    inventory = data_loader.current_inventory(sample_products, sample_sales)
    latest_day = sample_sales[sample_sales["sale_date"] == sample_sales["sale_date"].max()]
    expected = dict(zip(latest_day["product_id"], latest_day["stock_on_hand"]))
    assert dict(zip(inventory["product_id"], inventory["current_stock"])) == expected
    assert len(inventory) == len(sample_products)


def test_generated_data_loads_with_product_details(generated_business_data):
    products, sales, generated_on = generated_business_data
    assert not products.empty
    assert not sales.empty
    assert generated_on
    assert sales["product_name"].notna().all()

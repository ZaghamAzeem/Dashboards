import pandas as pd

from data.make_dataset import HISTORY_DAYS, PRODUCT_CATALOGUE

EXPECTED_SAMPLE_PRODUCTS = {
    "Surgical Gloves",
    "Face Masks",
    "Gauze Packs",
    "Artery Forceps",
    "Surgical Probes",
}


def test_catalogue_covers_both_categories():
    categories = {product["category"] for product in PRODUCT_CATALOGUE}
    assert categories == {"Surgical Instruments", "Medical Supplies"}


def test_catalogue_identifiers_are_unique():
    identifiers = [product["product_id"] for product in PRODUCT_CATALOGUE]
    assert len(identifiers) == len(set(identifiers))


def test_generated_products_match_catalogue(generated_business_data):
    products, _, _ = generated_business_data
    assert len(products) == len(PRODUCT_CATALOGUE)
    assert EXPECTED_SAMPLE_PRODUCTS.issubset(set(products["product_name"]))


def test_generated_sales_have_valid_dates(generated_business_data):
    _, sales, _ = generated_business_data
    assert sales["sale_date"].notna().all()
    assert pd.api.types.is_datetime64_any_dtype(sales["sale_date"])
    span = (sales["sale_date"].max() - sales["sale_date"].min()).days + 1
    assert span == HISTORY_DAYS


def test_every_product_has_a_complete_history(generated_business_data):
    products, sales, _ = generated_business_data
    counts = sales.groupby("product_id")["sale_date"].nunique()
    assert set(counts.index) == set(products["product_id"])
    assert counts.nunique() == 1
    assert int(counts.iloc[0]) == HISTORY_DAYS


def test_no_impossible_quantities(generated_business_data):
    _, sales, _ = generated_business_data
    assert (sales["units_sold"] >= 0).all()
    assert (sales["stock_on_hand"] >= 0).all()
    assert sales["on_promotion"].isin([0, 1]).all()


def test_no_duplicate_transactions(generated_business_data):
    _, sales, _ = generated_business_data
    assert not sales.duplicated(subset=["sale_date", "product_id"]).any()


def test_data_contains_a_meaningful_inventory_scenario(generated_business_data):
    _, sales, _ = generated_business_data
    recent = sales[sales["sale_date"] >= sales["sale_date"].max() - pd.Timedelta(days=89)]
    assert (recent["stock_on_hand"] == 0).any()
    assert recent["units_sold"].groupby(recent["product_id"]).sum().min() >= 0


def test_products_have_varied_demand_levels(generated_business_data):
    _, sales, _ = generated_business_data
    totals = sales.groupby("product_id")["units_sold"].sum()
    assert totals.max() > totals.min() * 10

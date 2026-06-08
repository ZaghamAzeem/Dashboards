import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard import data_loader

SAMPLE_PRODUCTS = [
    ("SI-900", "Test Forceps", "Surgical Instruments", "pieces", 12.0),
    ("MS-900", "Test Gloves", "Medical Supplies", "boxes", 90.0),
]
SAMPLE_DAYS = 220
WEEKDAY_WEIGHTS = np.array([1.20, 1.15, 1.10, 1.05, 0.95, 0.35, 0.20])


@pytest.fixture(scope="session")
def sample_products():
    return pd.DataFrame(
        [
            {
                "product_id": product_id,
                "product_name": name,
                "category": category,
                "unit_of_measure": unit,
            }
            for product_id, name, category, unit, _ in SAMPLE_PRODUCTS
        ]
    )


@pytest.fixture(scope="session")
def sample_sales(sample_products):
    calendar = pd.date_range(end=pd.Timestamp("2025-06-30"), periods=SAMPLE_DAYS, freq="D")
    rng = np.random.default_rng(7)
    frames = []
    for product_id, _, _, _, base_demand in SAMPLE_PRODUCTS:
        weekday_component = WEEKDAY_WEIGHTS[calendar.dayofweek.to_numpy()]
        expected = base_demand * weekday_component
        units_sold = rng.poisson(expected)
        stock = np.maximum(0, (base_demand * 9 - np.cumsum(units_sold) % (base_demand * 9)))
        frames.append(
            pd.DataFrame(
                {
                    "sale_date": calendar,
                    "product_id": product_id,
                    "units_sold": units_sold.astype(int),
                    "on_promotion": rng.integers(0, 2, size=SAMPLE_DAYS),
                    "stock_on_hand": stock.astype(int),
                }
            )
        )
    sales = pd.concat(frames, ignore_index=True)
    return sales.merge(sample_products, on="product_id", how="left")


@pytest.fixture(scope="session")
def sample_inventory(sample_products, sample_sales):
    return data_loader.current_inventory(sample_products, sample_sales)


@pytest.fixture(scope="session")
def generated_business_data():
    if not data_loader.business_data_is_available():
        pytest.skip("Business data has not been generated yet")
    return data_loader.load_business_data()

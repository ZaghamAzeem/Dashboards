from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard import data_loader

REFERENCE_DAY = pd.Timestamp("2026-06-30")


@pytest.fixture
def sample_products():
    return pd.DataFrame(
        {
            "product_id": ["P1", "P2", "P3"],
            "product_name": ["Hard Ball Cricket Bat", "Yoga Mat", "Tennis Net"],
            "category": ["Cricket", "Fitness", "Tennis"],
            "subcategory": ["Bats", "Training Aids", "Equipment"],
            "unit_price": [8000.0, 1800.0, 7800.0],
            "current_stock": [4, 90, 0],
            "reorder_level": [10, 20, 5],
        }
    )


def build_sales(products, days, end_day=REFERENCE_DAY):
    calendar = pd.date_range(end=end_day, periods=days, freq="D")
    rows = []
    for offset, day in enumerate(calendar):
        weekend = day.dayofweek >= 5
        volumes = {
            "P1": 6 if weekend else 3,
            "P2": 2,
            "P3": 1 if offset % 9 == 0 else 0,
        }
        for product_id, units in volumes.items():
            if units <= 0:
                continue
            price = float(products.loc[products["product_id"] == product_id, "unit_price"].iloc[0])
            rows.append(
                {
                    "sale_date": day,
                    "product_id": product_id,
                    "units_sold": units,
                    "unit_price": price,
                    "discount_pct": 0.0,
                    "revenue": price * units,
                }
            )

    frame = pd.DataFrame(rows)
    frame.insert(0, "transaction_id", np.arange(1, len(frame) + 1))
    return frame.merge(
        products[["product_id", "product_name", "category", "subcategory"]],
        on="product_id",
        how="left",
    )


@pytest.fixture
def sample_sales(sample_products):
    return build_sales(sample_products, days=220)


@pytest.fixture
def short_sales(sample_products):
    return build_sales(sample_products, days=40)


@pytest.fixture
def sample_daily_sales(sample_sales, sample_products):
    return data_loader.build_daily_sales(sample_sales, sample_products)


@pytest.fixture
def short_daily_sales(short_sales, sample_products):
    return data_loader.build_daily_sales(short_sales, sample_products)


@pytest.fixture
def latest_day(sample_sales):
    return sample_sales["sale_date"].max()

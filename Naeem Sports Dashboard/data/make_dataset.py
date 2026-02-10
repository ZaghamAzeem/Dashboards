from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

RANDOM_SEED = 20240914
HISTORY_DAYS = 730
DATA_DIR = Path(__file__).resolve().parent
DATABASE_PATH = DATA_DIR / "sports_shop.db"

CATALOG = [
    ("Match Football", "Football", "Balls", 3200, "star"),
    ("Training Football", "Football", "Balls", 1850, "strong"),
    ("Football Boots", "Football", "Footwear", 5400, "star"),
    ("Shin Guards", "Football", "Protective Gear", 950, "steady"),
    ("Goalkeeper Gloves", "Football", "Protective Gear", 2600, "steady"),
    ("Football Socks", "Football", "Apparel", 550, "strong"),
    ("Football Jersey", "Football", "Apparel", 1750, "strong"),
    ("Ball Inflation Pump", "Football", "Equipment", 700, "slow"),
    ("Hard Ball Cricket Bat", "Cricket", "Bats", 8500, "star"),
    ("Tennis Ball Cricket Bat", "Cricket", "Bats", 3400, "star"),
    ("Leather Cricket Ball", "Cricket", "Balls", 1400, "strong"),
    ("Tape Ball", "Cricket", "Balls", 320, "star"),
    ("Batting Gloves", "Cricket", "Protective Gear", 2400, "strong"),
    ("Wicket Keeping Gloves", "Cricket", "Protective Gear", 3100, "steady"),
    ("Cricket Helmet", "Cricket", "Protective Gear", 4600, "steady"),
    ("Cricket Batting Pads", "Cricket", "Protective Gear", 4200, "steady"),
    ("Cricket Stumps Set", "Cricket", "Equipment", 2200, "steady"),
    ("Cricket Kit Bag", "Cricket", "Bags", 4900, "steady"),
    ("Badminton Racket", "Badminton", "Rackets", 2800, "star"),
    ("Shuttlecock Pack", "Badminton", "Shuttles", 1100, "star"),
    ("Badminton Net", "Badminton", "Equipment", 1900, "slow"),
    ("Racket Grip Tape", "Badminton", "Accessories", 250, "strong"),
    ("Badminton Racket Cover", "Badminton", "Bags", 800, "slow"),
    ("Tennis Racket", "Tennis", "Rackets", 6200, "steady"),
    ("Tennis Balls Can", "Tennis", "Balls", 1300, "strong"),
    ("Tennis Overgrip", "Tennis", "Accessories", 400, "steady"),
    ("Tennis Net", "Tennis", "Equipment", 7800, "slow"),
    ("Tennis Racket Bag", "Tennis", "Bags", 2900, "slow"),
    ("Dumbbell Pair", "Fitness", "Weights", 4300, "strong"),
    ("Kettlebell", "Fitness", "Weights", 3900, "steady"),
    ("Weight Lifting Belt", "Fitness", "Support", 2100, "steady"),
    ("Resistance Band Set", "Fitness", "Training Aids", 1200, "star"),
    ("Yoga Mat", "Fitness", "Training Aids", 1800, "star"),
    ("Skipping Rope", "Fitness", "Training Aids", 450, "star"),
    ("Exercise Ball", "Fitness", "Training Aids", 1600, "steady"),
    ("Hand Grip Strengthener", "Fitness", "Training Aids", 380, "strong"),
    ("Push Up Bars", "Fitness", "Training Aids", 900, "steady"),
    ("Sports Water Bottle", "Accessories", "Hydration", 600, "star"),
    ("Sports Bag", "Accessories", "Bags", 2300, "strong"),
    ("Knee Support", "Accessories", "Support", 850, "strong"),
    ("Ankle Support", "Accessories", "Support", 750, "steady"),
    ("Sports Cap", "Accessories", "Apparel", 700, "steady"),
    ("Sports Towel", "Accessories", "Apparel", 500, "steady"),
    ("Wrist Band", "Accessories", "Support", 300, "strong"),
    ("Referee Whistle", "Accessories", "Equipment", 350, "slow"),
]

SEASONAL_SHAPE = {
    "Football": [1.05, 0.95, 0.88, 0.82, 0.80, 0.85, 0.95, 1.15, 1.35, 1.30, 1.20, 1.10],
    "Cricket": [0.78, 0.85, 1.10, 1.30, 1.35, 1.25, 1.15, 1.20, 1.05, 0.90, 0.80, 0.75],
    "Badminton": [1.25, 1.15, 0.95, 0.80, 0.72, 0.70, 0.75, 0.85, 1.00, 1.15, 1.30, 1.32],
    "Tennis": [0.85, 0.90, 1.05, 1.20, 1.28, 1.22, 1.10, 1.05, 1.00, 0.95, 0.88, 0.82],
    "Fitness": [1.45, 1.25, 1.05, 0.95, 0.92, 0.88, 0.85, 0.90, 0.98, 1.02, 1.05, 1.15],
    "Accessories": [1.05, 1.00, 1.02, 1.05, 1.08, 1.00, 0.95, 1.02, 1.08, 1.05, 1.00, 1.02],
}

WEEKDAY_SHAPE = np.array([0.80, 0.76, 0.84, 0.88, 1.10, 1.48, 1.34])

TIER_BASE_DEMAND = {"star": 6.4, "strong": 3.3, "steady": 1.7, "slow": 0.55}

DISCOUNT_CHOICES = np.array([10, 15, 20, 25])


def build_product_table(rng):
    records = []
    for index, (name, category, subcategory, price, tier) in enumerate(CATALOG, start=1):
        base_demand = TIER_BASE_DEMAND[tier] * rng.uniform(0.75, 1.28)
        records.append(
            {
                "product_id": "SP{:03d}".format(index),
                "product_name": name,
                "category": category,
                "subcategory": subcategory,
                "unit_price": float(price),
                "popularity_tier": tier,
                "base_demand": base_demand,
                "annual_growth": float(np.clip(rng.normal(0.12, 0.30), -0.38, 0.62)),
                "reorder_level": int(max(6, round(base_demand * 9))),
                "order_discipline": 0.6 if rng.random() < 0.25 else 1.0,
            }
        )
    return pd.DataFrame(records)


def build_promotion_matrix(products, rng):
    discounts = np.zeros((len(products), HISTORY_DAYS))
    for row in range(len(products)):
        for _ in range(rng.poisson(6)):
            start = int(rng.integers(0, HISTORY_DAYS - 10))
            length = int(rng.integers(4, 10))
            discounts[row, start : start + length] = rng.choice(DISCOUNT_CHOICES)
    return discounts


def build_event_matrix(products, rng):
    uplift = np.ones((len(products), HISTORY_DAYS))
    categories = products["category"].to_numpy()
    for _ in range(6):
        category = rng.choice(list(SEASONAL_SHAPE))
        start = int(rng.integers(30, HISTORY_DAYS - 15))
        length = int(rng.integers(6, 13))
        strength = float(rng.uniform(1.8, 2.6))
        uplift[categories == category, start : start + length] *= strength
    return uplift


def simulate_demand(products, calendar, rng):
    discounts = build_promotion_matrix(products, rng)
    events = build_event_matrix(products, rng)

    weekday_factor = WEEKDAY_SHAPE[calendar.dayofweek.to_numpy()]
    month_index = calendar.month.to_numpy() - 1
    day_index = np.arange(HISTORY_DAYS)

    demand = np.zeros((len(products), HISTORY_DAYS), dtype=int)
    for row, product in products.iterrows():
        seasonal_factor = np.array(SEASONAL_SHAPE[product["category"]])[month_index]
        trend_factor = (1.0 + product["annual_growth"]) ** (day_index / 365.0)
        promotion_factor = 1.0 + (discounts[row] / 100.0) * 3.2
        intensity = (
            product["base_demand"]
            * weekday_factor
            * seasonal_factor
            * trend_factor
            * promotion_factor
            * events[row]
        )
        demand[row] = rng.poisson(np.clip(intensity, 0.02, None))
    return demand, discounts


def simulate_inventory(products, demand, rng):
    sold = np.zeros_like(demand)
    closing_stock = np.zeros_like(demand)
    replenishments = []

    supply_gap_start = np.full(len(products), HISTORY_DAYS + 1)
    for row in range(len(products)):
        if rng.random() < 0.16:
            supply_gap_start[row] = HISTORY_DAYS - int(rng.integers(9, 28))

    for row, product in products.iterrows():
        stock = int(max(10, round(product["base_demand"] * 42)))
        reorder_level = product["reorder_level"]
        order_size = int(
            max(reorder_level * 2.6, product["base_demand"] * 34) * product["order_discipline"]
        )
        pending_arrival = None
        pending_quantity = 0

        for day in range(HISTORY_DAYS):
            if pending_arrival == day:
                stock += pending_quantity
                replenishments.append((row, day, pending_quantity, stock))
                pending_arrival = None

            units = int(min(demand[row, day], stock))
            stock -= units
            sold[row, day] = units
            closing_stock[row, day] = stock

            if pending_arrival is None and stock <= reorder_level and day < supply_gap_start[row]:
                pending_arrival = day + int(rng.integers(2, 9))
                pending_quantity = int(order_size * rng.uniform(0.85, 1.2))

    return sold, closing_stock, replenishments


def build_sales_transactions(products, calendar, sold, discounts, rng):
    rows = []
    for index, product in products.iterrows():
        for day in np.flatnonzero(sold[index]):
            units_remaining = int(sold[index, day])
            splits = min(units_remaining, int(rng.integers(1, 4)))
            portions = np.full(splits, units_remaining // splits)
            portions[: units_remaining % splits] += 1
            discount = float(discounts[index, day])
            unit_price = round(product["unit_price"] * (1 - discount / 100.0), 2)
            for portion in portions:
                rows.append(
                    (
                        calendar[day].strftime("%Y-%m-%d"),
                        product["product_id"],
                        int(portion),
                        unit_price,
                        discount,
                        round(unit_price * int(portion), 2),
                    )
                )
    frame = pd.DataFrame(
        rows,
        columns=["sale_date", "product_id", "units_sold", "unit_price", "discount_pct", "revenue"],
    )
    frame = frame.sort_values(["sale_date", "product_id"]).reset_index(drop=True)
    frame.insert(0, "transaction_id", np.arange(1, len(frame) + 1))
    return frame


def build_inventory_movements(products, calendar, sold, closing_stock, replenishments):
    rows = []
    for index, product in products.iterrows():
        for day in np.flatnonzero(sold[index]):
            rows.append(
                (
                    calendar[day].strftime("%Y-%m-%d"),
                    product["product_id"],
                    "Sale",
                    -int(sold[index, day]),
                    int(closing_stock[index, day]),
                )
            )
    for row, day, quantity, stock_after in replenishments:
        rows.append(
            (
                calendar[day].strftime("%Y-%m-%d"),
                products.at[row, "product_id"],
                "Restock",
                int(quantity),
                int(stock_after),
            )
        )
    frame = pd.DataFrame(
        rows,
        columns=["movement_date", "product_id", "movement_type", "quantity_change", "stock_after"],
    )
    frame = frame.sort_values(["movement_date", "product_id"]).reset_index(drop=True)
    frame.insert(0, "movement_id", np.arange(1, len(frame) + 1))
    return frame


SCHEMA = """
CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    unit_price REAL NOT NULL,
    current_stock INTEGER NOT NULL,
    reorder_level INTEGER NOT NULL
);

CREATE TABLE sales_transactions (
    transaction_id INTEGER PRIMARY KEY,
    sale_date TEXT NOT NULL,
    product_id TEXT NOT NULL REFERENCES products(product_id),
    units_sold INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    discount_pct REAL NOT NULL,
    revenue REAL NOT NULL
);

CREATE TABLE inventory_movements (
    movement_id INTEGER PRIMARY KEY,
    movement_date TEXT NOT NULL,
    product_id TEXT NOT NULL REFERENCES products(product_id),
    movement_type TEXT NOT NULL,
    quantity_change INTEGER NOT NULL,
    stock_after INTEGER NOT NULL
);

CREATE INDEX idx_sales_date ON sales_transactions(sale_date);
CREATE INDEX idx_sales_product ON sales_transactions(product_id);
CREATE INDEX idx_movements_product ON inventory_movements(product_id);
"""


def write_database(products, sales, movements, database_path=DATABASE_PATH):
    database_path.unlink(missing_ok=True)
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(SCHEMA)
        products.to_sql("products", connection, if_exists="append", index=False)
        sales.to_sql("sales_transactions", connection, if_exists="append", index=False)
        movements.to_sql("inventory_movements", connection, if_exists="append", index=False)
        connection.commit()
    finally:
        connection.close()


def build_catalog_snapshot(products, closing_stock):
    catalog = products[
        ["product_id", "product_name", "category", "subcategory", "unit_price", "reorder_level"]
    ].copy()
    catalog["current_stock"] = closing_stock[:, -1].astype(int)
    return catalog[
        [
            "product_id",
            "product_name",
            "category",
            "subcategory",
            "unit_price",
            "current_stock",
            "reorder_level",
        ]
    ]


def generate(database_path=DATABASE_PATH):
    rng = np.random.default_rng(RANDOM_SEED)
    calendar = pd.date_range(end=pd.Timestamp.today().normalize(), periods=HISTORY_DAYS, freq="D")

    products = build_product_table(rng)
    demand, discounts = simulate_demand(products, calendar, rng)
    sold, closing_stock, replenishments = simulate_inventory(products, demand, rng)

    sales = build_sales_transactions(products, calendar, sold, discounts, rng)
    movements = build_inventory_movements(products, calendar, sold, closing_stock, replenishments)
    catalog = build_catalog_snapshot(products, closing_stock)

    write_database(catalog, sales, movements, database_path)
    return {
        "products": len(catalog),
        "transactions": len(sales),
        "movements": len(movements),
        "first_day": calendar[0].date().isoformat(),
        "last_day": calendar[-1].date().isoformat(),
        "units_sold": int(sales["units_sold"].sum()),
        "revenue": float(sales["revenue"].sum()),
    }


def main():
    summary = generate()
    print("Naeem Sports Goods Shop dataset created")
    print("  database    : {}".format(DATABASE_PATH))
    print("  products    : {}".format(summary["products"]))
    print("  sales rows  : {:,}".format(summary["transactions"]))
    print("  stock moves : {:,}".format(summary["movements"]))
    print("  history     : {} to {}".format(summary["first_day"], summary["last_day"]))
    print("  units sold  : {:,}".format(summary["units_sold"]))
    print("  revenue     : Rs {:,.0f}".format(summary["revenue"]))


if __name__ == "__main__":
    main()

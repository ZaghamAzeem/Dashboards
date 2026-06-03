import sqlite3
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

DATABASE_PATH = Path(__file__).resolve().parent / "sadat_surgical.db"
RANDOM_SEED = 20240517
HISTORY_DAYS = 730

SURGICAL_INSTRUMENTS = "Surgical Instruments"
MEDICAL_SUPPLIES = "Medical Supplies"

PRODUCT_CATALOGUE = [
    {
        "product_id": "SI-001",
        "product_name": "Surgical Scissors",
        "category": SURGICAL_INSTRUMENTS,
        "unit_of_measure": "pieces",
        "base_demand": 14.0,
        "weekend_factor": 0.35,
        "seasonal_amplitude": 0.12,
        "seasonal_peak_month": 10,
        "annual_growth": 0.06,
        "promotion_rate": 0.030,
        "promotion_lift": 1.55,
        "spike_rate": 0.010,
        "spike_lift": 2.2,
        "dispersion": 7.0,
        "cover_days": 26,
        "reorder_days": 12,
        "lead_time_days": 9,
        "lead_time_spread": 3,
    },
    {
        "product_id": "SI-002",
        "product_name": "Mayo Scissors",
        "category": SURGICAL_INSTRUMENTS,
        "unit_of_measure": "pieces",
        "base_demand": 9.0,
        "weekend_factor": 0.30,
        "seasonal_amplitude": 0.10,
        "seasonal_peak_month": 9,
        "annual_growth": 0.04,
        "promotion_rate": 0.025,
        "promotion_lift": 1.45,
        "spike_rate": 0.008,
        "spike_lift": 2.0,
        "dispersion": 6.0,
        "cover_days": 30,
        "reorder_days": 14,
        "lead_time_days": 10,
        "lead_time_spread": 3,
    },
    {
        "product_id": "SI-003",
        "product_name": "Metzenbaum Scissors",
        "category": SURGICAL_INSTRUMENTS,
        "unit_of_measure": "pieces",
        "base_demand": 3.0,
        "weekend_factor": 0.25,
        "seasonal_amplitude": 0.08,
        "seasonal_peak_month": 11,
        "annual_growth": -0.05,
        "promotion_rate": 0.020,
        "promotion_lift": 1.40,
        "spike_rate": 0.005,
        "spike_lift": 1.8,
        "dispersion": 4.0,
        "cover_days": 45,
        "reorder_days": 20,
        "lead_time_days": 12,
        "lead_time_spread": 4,
    },
    {
        "product_id": "SI-004",
        "product_name": "Artery Forceps",
        "category": SURGICAL_INSTRUMENTS,
        "unit_of_measure": "pieces",
        "base_demand": 18.0,
        "weekend_factor": 0.32,
        "seasonal_amplitude": 0.14,
        "seasonal_peak_month": 8,
        "annual_growth": 0.09,
        "promotion_rate": 0.035,
        "promotion_lift": 1.60,
        "spike_rate": 0.012,
        "spike_lift": 2.3,
        "dispersion": 7.5,
        "cover_days": 22,
        "reorder_days": 10,
        "lead_time_days": 8,
        "lead_time_spread": 3,
    },
    {
        "product_id": "SI-005",
        "product_name": "Hemostatic Forceps",
        "category": SURGICAL_INSTRUMENTS,
        "unit_of_measure": "pieces",
        "base_demand": 11.0,
        "weekend_factor": 0.30,
        "seasonal_amplitude": 0.11,
        "seasonal_peak_month": 7,
        "annual_growth": 0.05,
        "promotion_rate": 0.028,
        "promotion_lift": 1.50,
        "spike_rate": 0.009,
        "spike_lift": 2.1,
        "dispersion": 6.5,
        "cover_days": 18,
        "reorder_days": 8,
        "lead_time_days": 11,
        "lead_time_spread": 5,
    },
    {
        "product_id": "SI-006",
        "product_name": "Tissue Forceps",
        "category": SURGICAL_INSTRUMENTS,
        "unit_of_measure": "pieces",
        "base_demand": 8.0,
        "weekend_factor": 0.28,
        "seasonal_amplitude": 0.09,
        "seasonal_peak_month": 6,
        "annual_growth": 0.02,
        "promotion_rate": 0.022,
        "promotion_lift": 1.40,
        "spike_rate": 0.007,
        "spike_lift": 1.9,
        "dispersion": 5.5,
        "cover_days": 28,
        "reorder_days": 13,
        "lead_time_days": 9,
        "lead_time_spread": 3,
    },
    {
        "product_id": "SI-007",
        "product_name": "Dressing Forceps",
        "category": SURGICAL_INSTRUMENTS,
        "unit_of_measure": "pieces",
        "base_demand": 12.5,
        "weekend_factor": 0.33,
        "seasonal_amplitude": 0.10,
        "seasonal_peak_month": 12,
        "annual_growth": 0.03,
        "promotion_rate": 0.026,
        "promotion_lift": 1.45,
        "spike_rate": 0.008,
        "spike_lift": 2.0,
        "dispersion": 6.0,
        "cover_days": 24,
        "reorder_days": 11,
        "lead_time_days": 9,
        "lead_time_spread": 3,
    },
    {
        "product_id": "SI-008",
        "product_name": "Needle Holders",
        "category": SURGICAL_INSTRUMENTS,
        "unit_of_measure": "pieces",
        "base_demand": 10.0,
        "weekend_factor": 0.31,
        "seasonal_amplitude": 0.13,
        "seasonal_peak_month": 9,
        "annual_growth": 0.07,
        "promotion_rate": 0.030,
        "promotion_lift": 1.55,
        "spike_rate": 0.010,
        "spike_lift": 2.2,
        "dispersion": 6.0,
        "cover_days": 20,
        "reorder_days": 9,
        "lead_time_days": 12,
        "lead_time_spread": 5,
    },
    {
        "product_id": "SI-009",
        "product_name": "Surgical Retractors",
        "category": SURGICAL_INSTRUMENTS,
        "unit_of_measure": "pieces",
        "base_demand": 4.0,
        "weekend_factor": 0.26,
        "seasonal_amplitude": 0.08,
        "seasonal_peak_month": 5,
        "annual_growth": -0.03,
        "promotion_rate": 0.018,
        "promotion_lift": 1.35,
        "spike_rate": 0.005,
        "spike_lift": 1.8,
        "dispersion": 4.5,
        "cover_days": 42,
        "reorder_days": 19,
        "lead_time_days": 12,
        "lead_time_spread": 4,
    },
    {
        "product_id": "SI-010",
        "product_name": "Scalpel Handles",
        "category": SURGICAL_INSTRUMENTS,
        "unit_of_measure": "pieces",
        "base_demand": 16.0,
        "weekend_factor": 0.34,
        "seasonal_amplitude": 0.12,
        "seasonal_peak_month": 10,
        "annual_growth": 0.08,
        "promotion_rate": 0.032,
        "promotion_lift": 1.60,
        "spike_rate": 0.011,
        "spike_lift": 2.2,
        "dispersion": 7.0,
        "cover_days": 23,
        "reorder_days": 10,
        "lead_time_days": 8,
        "lead_time_spread": 3,
    },
    {
        "product_id": "SI-011",
        "product_name": "Surgical Probes",
        "category": SURGICAL_INSTRUMENTS,
        "unit_of_measure": "pieces",
        "base_demand": 1.8,
        "weekend_factor": 0.22,
        "seasonal_amplitude": 0.06,
        "seasonal_peak_month": 4,
        "annual_growth": -0.08,
        "promotion_rate": 0.015,
        "promotion_lift": 1.30,
        "spike_rate": 0.004,
        "spike_lift": 1.7,
        "dispersion": 3.5,
        "cover_days": 55,
        "reorder_days": 25,
        "lead_time_days": 14,
        "lead_time_spread": 4,
    },
    {
        "product_id": "MS-001",
        "product_name": "Surgical Gloves",
        "category": MEDICAL_SUPPLIES,
        "unit_of_measure": "boxes",
        "base_demand": 132.0,
        "weekend_factor": 0.42,
        "seasonal_amplitude": 0.16,
        "seasonal_peak_month": 12,
        "annual_growth": 0.11,
        "promotion_rate": 0.045,
        "promotion_lift": 1.70,
        "spike_rate": 0.014,
        "spike_lift": 2.1,
        "dispersion": 9.0,
        "cover_days": 16,
        "reorder_days": 7,
        "lead_time_days": 6,
        "lead_time_spread": 2,
    },
    {
        "product_id": "MS-002",
        "product_name": "Examination Gloves",
        "category": MEDICAL_SUPPLIES,
        "unit_of_measure": "boxes",
        "base_demand": 148.0,
        "weekend_factor": 0.45,
        "seasonal_amplitude": 0.15,
        "seasonal_peak_month": 1,
        "annual_growth": 0.09,
        "promotion_rate": 0.042,
        "promotion_lift": 1.65,
        "spike_rate": 0.013,
        "spike_lift": 2.0,
        "dispersion": 9.0,
        "cover_days": 15,
        "reorder_days": 7,
        "lead_time_days": 6,
        "lead_time_spread": 2,
    },
    {
        "product_id": "MS-003",
        "product_name": "Face Masks",
        "category": MEDICAL_SUPPLIES,
        "unit_of_measure": "boxes",
        "base_demand": 176.0,
        "weekend_factor": 0.48,
        "seasonal_amplitude": 0.26,
        "seasonal_peak_month": 1,
        "annual_growth": 0.05,
        "promotion_rate": 0.050,
        "promotion_lift": 1.75,
        "spike_rate": 0.016,
        "spike_lift": 2.4,
        "dispersion": 8.0,
        "cover_days": 14,
        "reorder_days": 6,
        "lead_time_days": 7,
        "lead_time_spread": 3,
    },
    {
        "product_id": "MS-004",
        "product_name": "Syringes",
        "category": MEDICAL_SUPPLIES,
        "unit_of_measure": "boxes",
        "base_demand": 158.0,
        "weekend_factor": 0.44,
        "seasonal_amplitude": 0.14,
        "seasonal_peak_month": 11,
        "annual_growth": 0.07,
        "promotion_rate": 0.040,
        "promotion_lift": 1.60,
        "spike_rate": 0.012,
        "spike_lift": 2.0,
        "dispersion": 9.0,
        "cover_days": 17,
        "reorder_days": 8,
        "lead_time_days": 6,
        "lead_time_spread": 2,
    },
    {
        "product_id": "MS-005",
        "product_name": "IV Cannulas",
        "category": MEDICAL_SUPPLIES,
        "unit_of_measure": "boxes",
        "base_demand": 74.0,
        "weekend_factor": 0.46,
        "seasonal_amplitude": 0.12,
        "seasonal_peak_month": 8,
        "annual_growth": 0.10,
        "promotion_rate": 0.035,
        "promotion_lift": 1.55,
        "spike_rate": 0.011,
        "spike_lift": 2.1,
        "dispersion": 8.0,
        "cover_days": 13,
        "reorder_days": 6,
        "lead_time_days": 10,
        "lead_time_spread": 4,
    },
    {
        "product_id": "MS-006",
        "product_name": "Gauze Packs",
        "category": MEDICAL_SUPPLIES,
        "unit_of_measure": "packs",
        "base_demand": 96.0,
        "weekend_factor": 0.43,
        "seasonal_amplitude": 0.13,
        "seasonal_peak_month": 7,
        "annual_growth": 0.12,
        "promotion_rate": 0.038,
        "promotion_lift": 1.60,
        "spike_rate": 0.013,
        "spike_lift": 2.3,
        "dispersion": 8.5,
        "cover_days": 12,
        "reorder_days": 5,
        "lead_time_days": 11,
        "lead_time_spread": 5,
    },
    {
        "product_id": "MS-007",
        "product_name": "Surgical Drapes",
        "category": MEDICAL_SUPPLIES,
        "unit_of_measure": "packs",
        "base_demand": 42.0,
        "weekend_factor": 0.38,
        "seasonal_amplitude": 0.11,
        "seasonal_peak_month": 10,
        "annual_growth": 0.04,
        "promotion_rate": 0.030,
        "promotion_lift": 1.50,
        "spike_rate": 0.009,
        "spike_lift": 2.0,
        "dispersion": 7.0,
        "cover_days": 21,
        "reorder_days": 10,
        "lead_time_days": 8,
        "lead_time_spread": 3,
    },
    {
        "product_id": "MS-008",
        "product_name": "Sterile Swabs",
        "category": MEDICAL_SUPPLIES,
        "unit_of_measure": "packs",
        "base_demand": 63.0,
        "weekend_factor": 0.41,
        "seasonal_amplitude": 0.10,
        "seasonal_peak_month": 6,
        "annual_growth": 0.03,
        "promotion_rate": 0.028,
        "promotion_lift": 1.45,
        "spike_rate": 0.008,
        "spike_lift": 1.9,
        "dispersion": 7.5,
        "cover_days": 19,
        "reorder_days": 9,
        "lead_time_days": 7,
        "lead_time_spread": 3,
    },
    {
        "product_id": "MS-009",
        "product_name": "Adhesive Tape",
        "category": MEDICAL_SUPPLIES,
        "unit_of_measure": "rolls",
        "base_demand": 48.0,
        "weekend_factor": 0.39,
        "seasonal_amplitude": 0.09,
        "seasonal_peak_month": 3,
        "annual_growth": 0.02,
        "promotion_rate": 0.026,
        "promotion_lift": 1.40,
        "spike_rate": 0.007,
        "spike_lift": 1.8,
        "dispersion": 7.0,
        "cover_days": 25,
        "reorder_days": 12,
        "lead_time_days": 7,
        "lead_time_spread": 2,
    },
    {
        "product_id": "MS-010",
        "product_name": "Disposable Caps",
        "category": MEDICAL_SUPPLIES,
        "unit_of_measure": "packs",
        "base_demand": 31.0,
        "weekend_factor": 0.37,
        "seasonal_amplitude": 0.08,
        "seasonal_peak_month": 2,
        "annual_growth": -0.02,
        "promotion_rate": 0.022,
        "promotion_lift": 1.40,
        "spike_rate": 0.006,
        "spike_lift": 1.8,
        "dispersion": 6.5,
        "cover_days": 34,
        "reorder_days": 16,
        "lead_time_days": 9,
        "lead_time_spread": 3,
    },
]


def build_calendar(history_days):
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=history_days - 1)
    return pd.date_range(start=start_date, end=end_date, freq="D")


def weekday_profile(profile, rng):
    weekday_shape = np.array([1.06, 1.10, 1.08, 1.04, 0.96, 1.0, 1.0])
    weights = weekday_shape * rng.uniform(0.94, 1.06, size=7)
    weights[5] *= profile["weekend_factor"] * 1.35
    weights[6] *= profile["weekend_factor"]
    return weights / weights.mean()


def seasonal_multiplier(calendar, profile):
    month_angle = 2 * np.pi * (calendar.month.to_numpy() - profile["seasonal_peak_month"]) / 12.0
    return 1.0 + profile["seasonal_amplitude"] * np.cos(month_angle)


def trend_multiplier(calendar, profile):
    elapsed_years = np.arange(len(calendar)) / 365.0
    return (1.0 + profile["annual_growth"]) ** elapsed_years


def promotion_flags(calendar, profile, rng):
    flags = np.zeros(len(calendar), dtype=int)
    day = 0
    while day < len(calendar):
        if rng.random() < profile["promotion_rate"]:
            duration = int(rng.integers(4, 11))
            flags[day:day + duration] = 1
            day += duration + int(rng.integers(20, 60))
        else:
            day += 1
    return flags


def spike_multiplier(calendar, profile, rng):
    multipliers = np.ones(len(calendar))
    day = 0
    while day < len(calendar):
        if rng.random() < profile["spike_rate"]:
            duration = int(rng.integers(2, 6))
            intensity = profile["spike_lift"] * rng.uniform(0.85, 1.2)
            multipliers[day:day + duration] = intensity
            day += duration + int(rng.integers(30, 90))
        else:
            day += 1
    return multipliers


def simulate_demand(calendar, profile, rng):
    weekday_weights = weekday_profile(profile, rng)
    weekday_component = weekday_weights[calendar.dayofweek.to_numpy()]
    promotions = promotion_flags(calendar, profile, rng)
    promotion_component = np.where(promotions == 1, profile["promotion_lift"], 1.0)
    expected = (
        profile["base_demand"]
        * weekday_component
        * seasonal_multiplier(calendar, profile)
        * trend_multiplier(calendar, profile)
        * promotion_component
        * spike_multiplier(calendar, profile, rng)
    )
    dispersion = profile["dispersion"]
    noisy_rate = expected * rng.gamma(dispersion, 1.0 / dispersion, size=len(calendar))
    return rng.poisson(np.clip(noisy_rate, 0.05, None)), promotions


def simulate_inventory(demand, profile, rng):
    average_demand = float(np.mean(demand))
    reorder_point = max(1, int(round(average_demand * profile["reorder_days"])))
    stock = int(round(average_demand * profile["cover_days"] * rng.uniform(0.7, 1.0)))
    incoming = {}
    stock_levels = np.zeros(len(demand), dtype=int)
    units_sold = np.zeros(len(demand), dtype=int)
    for day, requested in enumerate(demand):
        stock += incoming.pop(day, 0)
        sold = int(min(requested, stock))
        stock -= sold
        recent_demand = float(np.mean(demand[max(0, day - 27):day + 1]))
        if stock <= reorder_point and not incoming:
            lead_time = int(
                max(3, rng.normal(profile["lead_time_days"], profile["lead_time_spread"]))
            )
            replenishment = max(2, int(round(recent_demand * profile["cover_days"])))
            arrival = day + lead_time
            if arrival < len(demand):
                incoming[arrival] = incoming.get(arrival, 0) + replenishment
        units_sold[day] = sold
        stock_levels[day] = stock
        reorder_point = max(1, int(round(recent_demand * profile["reorder_days"])))
    return units_sold, stock_levels


def generate_sales_frame():
    calendar = build_calendar(HISTORY_DAYS)
    master_rng = np.random.default_rng(RANDOM_SEED)
    records = []
    for profile in PRODUCT_CATALOGUE:
        rng = np.random.default_rng(int(master_rng.integers(0, 2**31 - 1)))
        demand, promotions = simulate_demand(calendar, profile, rng)
        units_sold, stock_levels = simulate_inventory(demand, profile, rng)
        records.append(
            pd.DataFrame(
                {
                    "sale_date": calendar.strftime("%Y-%m-%d"),
                    "product_id": profile["product_id"],
                    "units_sold": units_sold,
                    "on_promotion": promotions,
                    "stock_on_hand": stock_levels,
                }
            )
        )
    return pd.concat(records, ignore_index=True)


def generate_product_frame():
    columns = ["product_id", "product_name", "category", "unit_of_measure"]
    return pd.DataFrame(PRODUCT_CATALOGUE)[columns]


def write_database(products, sales, database_path):
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        database_path.unlink()
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE products ("
            "product_id TEXT PRIMARY KEY, "
            "product_name TEXT NOT NULL, "
            "category TEXT NOT NULL, "
            "unit_of_measure TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE daily_sales ("
            "sale_date TEXT NOT NULL, "
            "product_id TEXT NOT NULL, "
            "units_sold INTEGER NOT NULL, "
            "on_promotion INTEGER NOT NULL, "
            "stock_on_hand INTEGER NOT NULL, "
            "PRIMARY KEY (sale_date, product_id), "
            "FOREIGN KEY (product_id) REFERENCES products (product_id))"
        )
        connection.execute(
            "CREATE TABLE dataset_info ("
            "generated_on TEXT NOT NULL, history_days INTEGER NOT NULL)"
        )
        products.to_sql("products", connection, if_exists="append", index=False)
        sales.to_sql("daily_sales", connection, if_exists="append", index=False)
        connection.execute(
            "INSERT INTO dataset_info (generated_on, history_days) VALUES (?, ?)",
            (date.today().isoformat(), HISTORY_DAYS),
        )
        connection.execute("CREATE INDEX idx_sales_date ON daily_sales (sale_date)")
        connection.execute("CREATE INDEX idx_sales_product ON daily_sales (product_id)")


def main():
    products = generate_product_frame()
    sales = generate_sales_frame()
    write_database(products, sales, DATABASE_PATH)
    latest_date = sales["sale_date"].max()
    closing_stock = sales[sales["sale_date"] == latest_date]
    print("Sadat Surgical and Medical Supplies - business data prepared")
    print(f"Products generated      : {len(products)}")
    print(f"Daily records generated : {len(sales):,}")
    print(f"History covered         : {sales['sale_date'].min()} to {latest_date}")
    print(f"Products out of stock   : {int((closing_stock['stock_on_hand'] == 0).sum())}")
    print(f"Database written to     : {DATABASE_PATH}")


if __name__ == "__main__":
    main()

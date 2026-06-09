import pandas as pd

from dashboard import analytics


def test_filter_sales_respects_date_bounds(sample_sales):
    start = pd.Timestamp("2025-05-01")
    end = pd.Timestamp("2025-05-31")
    filtered = analytics.filter_sales(sample_sales, start_date=start, end_date=end)
    assert filtered["sale_date"].min() >= start
    assert filtered["sale_date"].max() <= end
    assert len(filtered) == 31 * sample_sales["product_id"].nunique()


def test_filter_sales_respects_category(sample_sales):
    filtered = analytics.filter_sales(sample_sales, categories=["Medical Supplies"])
    assert set(filtered["category"]) == {"Medical Supplies"}


def test_daily_aggregation_preserves_totals(sample_sales):
    aggregated = analytics.sales_over_time(sample_sales, analytics.DAILY)
    assert aggregated["units_sold"].sum() == sample_sales["units_sold"].sum()
    assert aggregated["period"].is_monotonic_increasing


def test_every_aggregation_is_ordered_and_within_the_total(sample_sales):
    expected_total = sample_sales["units_sold"].sum()
    for granularity in analytics.GRANULARITIES:
        aggregated = analytics.sales_over_time(sample_sales, granularity)
        assert not aggregated.empty
        assert aggregated["period"].is_monotonic_increasing
        assert 0 < aggregated["units_sold"].sum() <= expected_total


def test_incomplete_final_month_is_excluded(sample_sales):
    ending_mid_month = analytics.filter_sales(
        sample_sales, end_date=pd.Timestamp("2025-06-03")
    )
    monthly = analytics.sales_over_time(ending_mid_month, analytics.MONTHLY)
    assert monthly["period"].max() == pd.Timestamp("2025-05-01")


def test_complete_final_month_is_kept(sample_sales):
    ending_on_month_end = analytics.filter_sales(
        sample_sales, end_date=pd.Timestamp("2025-05-31")
    )
    monthly = analytics.sales_over_time(ending_on_month_end, analytics.MONTHLY)
    assert monthly["period"].max() == pd.Timestamp("2025-05-01")


def test_weekly_view_only_covers_complete_weeks(sample_sales):
    part_weeks = analytics.filter_sales(
        sample_sales,
        start_date=pd.Timestamp("2025-05-07"),
        end_date=pd.Timestamp("2025-06-05"),
    )
    weekly = analytics.sales_over_time(part_weeks, analytics.WEEKLY)
    assert weekly["period"].min() == pd.Timestamp("2025-05-19")
    assert weekly["period"].max() == pd.Timestamp("2025-06-02")
    assert (weekly["units_sold"] > 0).all()


def test_complete_final_week_is_kept(sample_sales):
    whole_weeks = analytics.filter_sales(
        sample_sales,
        start_date=pd.Timestamp("2025-05-06"),
        end_date=pd.Timestamp("2025-06-02"),
    )
    weekly = analytics.sales_over_time(whole_weeks, analytics.WEEKLY)
    assert weekly["period"].max() == pd.Timestamp("2025-06-02")
    assert len(weekly) == 4


def test_daily_aggregation_matches_number_of_days(sample_sales):
    daily = analytics.sales_over_time(sample_sales, analytics.DAILY)
    assert len(daily) == sample_sales["sale_date"].nunique()


def test_sales_by_category_shares_sum_to_one(sample_sales):
    totals = analytics.sales_by_category(sample_sales)
    assert len(totals) == 2
    assert abs(totals["share"].sum() - 1.0) < 1e-9
    assert totals["units_sold"].is_monotonic_decreasing


def test_top_products_are_ordered_by_demand(sample_sales):
    leaders = analytics.top_products(sample_sales, limit=2)
    assert list(leaders["product_name"]) == ["Test Gloves", "Test Forceps"]
    assert leaders["units_sold"].is_monotonic_decreasing


def test_slow_moving_products_are_the_weakest_sellers(sample_sales):
    slow = analytics.slow_moving_products(sample_sales, limit=1)
    assert slow.iloc[0]["product_name"] == "Test Forceps"


def test_weekday_pattern_is_complete_and_ordered(sample_sales):
    pattern = analytics.weekday_demand_pattern(sample_sales)
    assert list(pattern["weekday"].astype(str)) == analytics.WEEKDAY_ORDER
    assert (pattern["average_units"] > 0).all()


def test_weekday_pattern_detects_quieter_weekends(sample_sales):
    assert analytics.weekday_versus_weekend(sample_sales) > 1.5


def test_units_sold_in_window_matches_manual_sum(sample_sales):
    reference = sample_sales["sale_date"].max()
    window = sample_sales[sample_sales["sale_date"] > reference - pd.Timedelta(days=7)]
    assert analytics.units_sold_in_window(sample_sales, reference, 7) == int(
        window["units_sold"].sum()
    )


def test_recent_sales_by_product_covers_every_product(sample_sales):
    reference = sample_sales["sale_date"].max()
    recent = analytics.recent_sales_by_product(sample_sales, reference, 30)
    assert set(recent["product_id"]) == set(sample_sales["product_id"])
    assert (recent["recent_units_sold"] >= 0).all()


def test_sales_trend_detects_growth():
    calendar = pd.date_range(end=pd.Timestamp("2025-06-30"), periods=60, freq="D")
    rising = pd.DataFrame(
        {
            "sale_date": calendar,
            "product_id": "SI-900",
            "product_name": "Test Forceps",
            "category": "Surgical Instruments",
            "unit_of_measure": "pieces",
            "units_sold": range(10, 70),
            "on_promotion": 0,
            "stock_on_hand": 100,
        }
    )
    trend = analytics.sales_trend(rising)
    assert trend["direction"] == analytics.TREND_RISING
    assert trend["change_ratio"] > 0


def test_sales_trend_detects_decline():
    calendar = pd.date_range(end=pd.Timestamp("2025-06-30"), periods=60, freq="D")
    falling = pd.DataFrame(
        {
            "sale_date": calendar,
            "product_id": "SI-900",
            "product_name": "Test Forceps",
            "category": "Surgical Instruments",
            "unit_of_measure": "pieces",
            "units_sold": range(70, 10, -1),
            "on_promotion": 0,
            "stock_on_hand": 100,
        }
    )
    trend = analytics.sales_trend(falling)
    assert trend["direction"] == analytics.TREND_DECLINING
    assert trend["change_ratio"] < 0


def test_empty_selection_returns_empty_aggregations(sample_sales):
    empty = analytics.filter_sales(sample_sales, categories=["Unknown Category"])
    assert empty.empty
    assert analytics.sales_over_time(empty, analytics.DAILY).empty
    assert analytics.sales_by_category(empty).empty
    assert analytics.top_products(empty).empty


def test_stockout_days_are_counted(generated_business_data):
    _, sales, _ = generated_business_data
    reference = sales["sale_date"].max()
    counts = analytics.stockout_days(sales, reference, 180)
    assert (counts["days_without_stock"] > 0).all()

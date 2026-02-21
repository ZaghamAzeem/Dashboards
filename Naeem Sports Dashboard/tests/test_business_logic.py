from __future__ import annotations

import math

import pandas as pd
import pytest

from dashboard import business_logic as rules


def test_empty_shelf_is_out_of_stock():
    assert rules.classify_stock_status(0, 12) == rules.STATUS_OUT
    assert rules.classify_stock_status(-3, 12) == rules.STATUS_OUT


def test_stock_below_expected_demand_needs_restocking():
    assert rules.classify_stock_status(8, 20) == rules.STATUS_RESTOCK


def test_stock_just_above_expected_demand_is_running_low():
    assert rules.classify_stock_status(22, 20) == rules.STATUS_LOW


def test_comfortable_stock_is_good():
    assert rules.classify_stock_status(80, 20) == rules.STATUS_GOOD


def test_a_product_with_no_expected_demand_is_good():
    assert rules.classify_stock_status(5, 0) == rules.STATUS_GOOD


def test_cover_days_translate_demand_into_time():
    assert rules.cover_days(70, 70) == pytest.approx(7.0)
    assert rules.cover_days(35, 70) == pytest.approx(3.5)
    assert math.isinf(rules.cover_days(35, 0))


def test_priority_follows_the_stock_status():
    assert rules.restock_priority(rules.STATUS_OUT) == rules.PRIORITY_HIGH
    assert rules.restock_priority(rules.STATUS_RESTOCK) == rules.PRIORITY_HIGH
    assert rules.restock_priority(rules.STATUS_LOW) == rules.PRIORITY_WATCH
    assert rules.restock_priority(rules.STATUS_GOOD) == rules.PRIORITY_NONE


def test_every_status_has_a_badge_an_action_and_a_note():
    for status in rules.STATUS_PRIORITY:
        assert rules.STATUS_BADGE[status]
        assert rules.STATUS_COLOR[status].startswith("#")
        assert rules.suggested_action(status)
        assert rules.STATUS_NOTE[status]


def test_momentum_labels_use_plain_language():
    assert rules.momentum_label(40) == rules.MOMENTUM_FASTER
    assert rules.momentum_label(0) == rules.MOMENTUM_STEADY
    assert rules.momentum_label(-40) == rules.MOMENTUM_SLOWER


def test_sales_headline_describes_the_direction():
    assert rules.sales_momentum_headline(25) == "Sales are picking up"
    assert rules.sales_momentum_headline(0) == "Sales are relatively stable"
    assert rules.sales_momentum_headline(-25) == "Sales have slowed recently"


@pytest.fixture
def overview(sample_products):
    expected = pd.Series({"P1": 30.0, "P2": 12.0, "P3": 6.0})
    return rules.build_stock_overview(sample_products, expected)


def test_stock_overview_classifies_every_product(overview):
    statuses = dict(zip(overview["product_name"], overview["status"]))
    assert statuses["Hard Ball Cricket Bat"] == rules.STATUS_RESTOCK
    assert statuses["Yoga Mat"] == rules.STATUS_GOOD
    assert statuses["Tennis Net"] == rules.STATUS_OUT


def test_stock_overview_sorts_the_most_urgent_first(overview):
    assert overview.iloc[0]["status"] == rules.STATUS_OUT
    assert overview.iloc[-1]["status"] == rules.STATUS_GOOD


def test_stock_overview_measures_the_shortfall(overview):
    bat = overview.loc[overview["product_name"] == "Hard Ball Cricket Bat"].iloc[0]
    assert bat["shortfall"] == pytest.approx(26.0)
    mat = overview.loc[overview["product_name"] == "Yoga Mat"].iloc[0]
    assert mat["shortfall"] == 0


def test_missing_forecast_values_do_not_break_the_overview(sample_products):
    result = rules.build_stock_overview(sample_products, pd.Series(dtype=float))
    assert (result["expected_demand"] == 0).all()
    assert set(result["status"]) == {rules.STATUS_GOOD, rules.STATUS_OUT}


def test_status_counts_cover_the_whole_catalogue(overview):
    counts = rules.status_counts(overview)
    assert set(counts) == set(rules.STATUS_PRIORITY)
    assert sum(counts.values()) == len(overview)


def test_products_needing_attention_excludes_healthy_stock(overview):
    attention = rules.products_needing_attention(overview)
    assert rules.STATUS_GOOD not in set(attention["status"])


def test_shopping_list_places_every_product_in_one_group(overview):
    groups = rules.shopping_list(overview)
    total = sum(len(block) for block in groups.values())
    assert total == len(overview)
    assert set(groups) == {rules.PRIORITY_HIGH, rules.PRIORITY_WATCH, rules.PRIORITY_NONE}


def test_forecast_explanations_are_written_for_every_situation():
    empty_shelf = rules.describe_forecast(0, 20, 5)
    short = rules.describe_forecast(5, 20, 30)
    healthy = rules.describe_forecast(200, 20, 0)
    quiet = rules.describe_forecast(200, 20, -40)

    assert len({empty_shelf, short, healthy, quiet}) == 4
    assert all(len(text) > 40 for text in (empty_shelf, short, healthy, quiet))
    assert "15" in short


def test_product_recommendations_change_with_the_situation():
    urgent = rules.describe_product_recommendation(rules.STATUS_OUT, 0)
    fast = rules.describe_product_recommendation(rules.STATUS_RESTOCK, 50)
    calm = rules.describe_product_recommendation(rules.STATUS_GOOD, 0)
    assert urgent != fast != calm


def test_category_leader_reads_the_top_row():
    performance = pd.DataFrame(
        {
            "category": ["Cricket", "Football"],
            "revenue": [500.0, 300.0],
            "units": [50, 30],
            "products": [3, 2],
            "share": [62.5, 37.5],
        }
    )
    leader = rules.category_leader(performance)
    assert leader["category"] == "Cricket"
    assert leader["share"] == pytest.approx(62.5)
    assert rules.category_leader(performance.iloc[0:0]) is None


def test_busiest_weekday_reports_a_lift_over_the_average():
    pattern = pd.DataFrame(
        {
            "weekday": ["Monday", "Saturday"],
            "revenue": [100.0, 300.0],
            "units": [10, 30],
            "days": [4, 4],
            "average_revenue": [25.0, 75.0],
        }
    )
    busiest = rules.busiest_weekday(pattern)
    assert busiest["weekday"] == "Saturday"
    assert busiest["quietest"] == "Monday"
    assert busiest["lift_pct"] == pytest.approx(50.0)


def test_currency_formatting_uses_readable_units():
    assert rules.format_currency(45_300) == "Rs 45,300"
    assert rules.format_currency(1_150_000) == "Rs 11.5 Lac"
    assert rules.format_currency(27_600_000) == "Rs 2.76 Cr"
    assert rules.format_currency(1_150_000, compact=False) == "Rs 1,150,000"


def test_change_and_cover_formatting_stay_readable():
    assert rules.format_change(12.34).startswith("▲")
    assert rules.format_change(-12.34).startswith("▼")
    assert rules.format_cover(float("inf")) == "No demand expected"
    assert rules.format_cover(0) == "Nothing left on the shelf"
    assert rules.format_cover(0.4) == "Less than a day"
    assert rules.format_cover(9.0) == "About 9 days"
    assert rules.format_cover(120.0) == "More than 2 months"

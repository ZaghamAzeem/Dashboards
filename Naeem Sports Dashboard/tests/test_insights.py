from __future__ import annotations

import pandas as pd
import pytest

from dashboard import analytics, insights
from dashboard import business_logic as rules


@pytest.fixture
def performance():
    return pd.DataFrame(
        {
            "category": ["Cricket", "Football"],
            "revenue": [750.0, 250.0],
            "units": [75, 25],
            "products": [4, 3],
            "share": [75.0, 25.0],
        }
    )


@pytest.fixture
def steady_momentum():
    return {"change_pct": 0.0}


def counts_of(out=0, restock=0, low=0, good=10):
    return {
        rules.STATUS_OUT: out,
        rules.STATUS_RESTOCK: restock,
        rules.STATUS_LOW: low,
        rules.STATUS_GOOD: good,
    }


def test_sales_story_names_the_leading_sport(performance, steady_momentum):
    story = insights.sales_story(performance, steady_momentum)
    assert story.startswith("Cricket products are leading sales with 75%")


def test_sales_story_keeps_the_shop_wide_share_when_one_sport_is_chosen(
    performance, steady_momentum
):
    story = insights.sales_story(performance, steady_momentum, selected_sport="Football")
    assert "Football products took" in story
    assert "25% of everything the shop sold" in story
    assert "100%" not in story


def test_sales_story_ignores_a_sport_with_no_sales(performance, steady_momentum):
    story = insights.sales_story(performance, steady_momentum, selected_sport="Tennis")
    assert story.startswith("Cricket")


def test_inventory_story_uses_singular_wording_for_one_product():
    story = insights.inventory_story(counts_of(out=1, restock=2))
    assert story.startswith("1 product is completely out of stock")
    assert "1 products" not in story


def test_inventory_story_uses_plural_wording_for_several_products():
    story = insights.inventory_story(counts_of(out=3, restock=2))
    assert story.startswith("3 products are completely out of stock")


def test_inventory_story_reports_a_healthy_shelf():
    assert insights.inventory_story(counts_of()) == (
        "Every product on the shelf has enough stock for the week ahead."
    )


def test_inventory_story_covers_every_combination():
    for out in range(3):
        for restock in range(3):
            for low in range(3):
                story = insights.inventory_story(counts_of(out, restock, low))
                assert story and story[-1] == "."
                assert " 1 products" not in story


def test_todays_story_returns_three_readable_lines(
    performance, steady_momentum, sample_products
):
    overview = rules.build_stock_overview(
        sample_products, pd.Series({"P1": 30.0, "P2": 12.0, "P3": 6.0})
    )
    leaderboard = pd.DataFrame(
        {
            "rank": [1],
            "product_id": ["P1"],
            "product_name": ["Hard Ball Cricket Bat"],
            "category": ["Cricket"],
            "units": [120],
            "revenue": [960000.0],
        }
    )
    story = insights.build_todays_story(
        performance, steady_momentum, counts_of(out=1), overview, leaderboard
    )
    assert len(story) == insights.MAX_STORY_LINES
    assert all(isinstance(line, str) and line.endswith(".") for line in story)


def test_smart_insights_are_capped_and_labelled(
    performance, steady_momentum, sample_sales, sample_products, latest_day
):
    overview = rules.build_stock_overview(
        sample_products, pd.Series({"P1": 30.0, "P2": 12.0, "P3": 6.0})
    )
    generated = insights.build_smart_insights(
        performance,
        steady_momentum,
        analytics.product_leaderboard(sample_sales),
        analytics.rising_products(sample_sales, latest_day),
        overview,
        counts_of(out=1, low=1),
        analytics.weekday_pattern(sample_sales),
        analytics.seasonal_peak_by_category(sample_sales),
        analytics.slow_movers(sample_sales, latest_day),
    )
    assert 4 <= len(generated) <= insights.MAX_INSIGHTS
    for insight in generated:
        assert insight["icon"] and insight["title"] and insight["text"]


def test_stories_stay_silent_when_there_is_nothing_to_say():
    empty = pd.DataFrame(columns=["category", "revenue", "units", "products", "share"])
    assert insights.sales_story(empty, {"change_pct": 0.0}) is None
    assert insights.seasonal_story(empty) is None
    assert insights.busiest_day_story(analytics.weekday_pattern(pd.DataFrame())) is None

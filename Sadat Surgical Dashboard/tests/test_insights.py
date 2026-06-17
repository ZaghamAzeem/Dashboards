import pandas as pd
import pytest

from dashboard import business_logic, insights

TECHNICAL_TERMS = [
    "model",
    "regression",
    "feature",
    "sql",
    "api",
    "rmse",
    "algorithm",
    "pipeline",
    "dataframe",
]


@pytest.fixture
def status_table():
    inventory = pd.DataFrame(
        {
            "product_id": ["SI-900", "MS-900"],
            "product_name": ["Test Forceps", "Test Gloves"],
            "category": ["Surgical Instruments", "Medical Supplies"],
            "unit_of_measure": ["pieces", "boxes"],
            "current_stock": [400, 40],
        }
    )
    expected_demand = pd.DataFrame(
        {"product_id": ["SI-900", "MS-900"], "expected_demand": [80, 600]}
    )
    recent_sales = pd.DataFrame(
        {"product_id": ["SI-900", "MS-900"], "recent_units_sold": [78, 540]}
    )
    return business_logic.build_inventory_status(inventory, expected_demand, recent_sales)


def contains_no_technical_language(message):
    lowered = message.lower()
    return not any(term in lowered for term in TECHNICAL_TERMS)


def test_sales_insight_describes_the_trend(sample_sales):
    message = insights.generate_sales_insight(sample_sales)
    assert message
    assert contains_no_technical_language(message)


def test_sales_insight_reacts_to_rising_demand():
    calendar = pd.date_range(end=pd.Timestamp("2025-06-30"), periods=60, freq="D")
    rising = pd.DataFrame(
        {
            "sale_date": calendar,
            "product_id": "SI-900",
            "product_name": "Test Forceps",
            "category": "Surgical Instruments",
            "unit_of_measure": "pieces",
            "units_sold": range(20, 80),
            "on_promotion": 0,
            "stock_on_hand": 100,
        }
    )
    assert "upward" in insights.generate_sales_insight(rising)


def test_inventory_insight_mentions_products_needing_action(status_table):
    message = insights.generate_inventory_insight(status_table)
    assert message
    assert contains_no_technical_language(message)


def test_forecast_insight_flags_a_shortfall():
    message = insights.generate_forecast_insight("Test Gloves", 40, 600, "boxes")
    assert "replenishment" in message.lower()


def test_forecast_insight_confirms_sufficient_stock():
    message = insights.generate_forecast_insight("Test Forceps", 400, 80, "pieces")
    assert "sufficient" in message.lower()


def test_forecast_insight_handles_an_empty_shelf():
    message = insights.generate_forecast_insight("Test Gloves", 0, 600, "boxes")
    assert "out of stock" in message.lower()


def test_reorder_insight_names_the_most_pressing_product(status_table):
    message = insights.generate_reorder_insight(status_table)
    assert "Test Gloves" in message


def test_product_insight_combines_stock_and_demand(sample_sales, status_table):
    product_row = status_table[status_table["product_id"] == "MS-900"].iloc[0]
    product_sales = sample_sales[sample_sales["product_id"] == "MS-900"]
    message = insights.generate_product_insight(product_row, product_sales)
    assert message
    assert contains_no_technical_language(message)


def test_business_insights_are_generated_from_data(sample_sales, status_table):
    messages = insights.generate_business_insights(sample_sales, status_table)
    assert 3 <= len(messages) <= insights.MAX_INSIGHTS
    assert all(message.strip() for message in messages)
    assert any("Test Gloves" in message for message in messages)
    assert all(contains_no_technical_language(message) for message in messages)


def test_business_story_has_five_sections(sample_sales, status_table):
    forecast = pd.DataFrame(
        {
            "forecast_date": pd.date_range("2025-07-01", periods=7, freq="D"),
            "expected_units": [100.0] * 7,
        }
    )
    story = insights.build_business_story(sample_sales, status_table, forecast)
    headings = [heading for heading, _ in story]
    assert headings == [
        "What Happened?",
        "What Is Happening Now?",
        "What May Happen Next?",
        "What Needs Attention?",
        "What Should We Consider?",
    ]
    assert all(body.strip() for _, body in story)

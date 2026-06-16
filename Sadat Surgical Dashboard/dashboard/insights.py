import pandas as pd

from dashboard import analytics, business_logic

RECENT_WINDOW_DAYS = 30
FORECAST_WINDOW_DAYS = 7
MAX_INSIGHTS = 5


def pluralize(count, singular, plural=None):
    if count == 1:
        return singular
    return plural if plural else f"{singular}s"


def format_units(value):
    return f"{int(round(value)):,}"


def format_percentage(ratio):
    return f"{abs(ratio) * 100:.0f}%"


def generate_sales_insight(sales, reference_date=None, window_days=None):
    trend = analytics.sales_trend(
        sales, reference_date, window_days or analytics.COMPARISON_WINDOW_DAYS
    )
    if trend["recent_units"] == 0 and trend["previous_units"] == 0:
        return "There is not enough sales activity in this selection to describe a trend."
    change = format_percentage(trend["change_ratio"])
    if trend["direction"] == analytics.TREND_RISING:
        message = f"Sales are trending upward, about {change} higher than the previous period."
    elif trend["direction"] == analytics.TREND_DECLINING:
        message = f"Sales are trending downward, about {change} lower than the previous period."
    else:
        message = "Sales have remained relatively stable compared with the previous period."
    if trend["is_variable"]:
        message += " Daily demand has also been more variable than usual."
    return message


def generate_inventory_insight(status_table):
    if status_table.empty:
        return "No inventory information is available for this selection."
    counts = business_logic.status_counts(status_table)
    total = int(status_table.shape[0])
    healthy = counts[business_logic.HEALTHY]
    needs_action = counts[business_logic.CRITICAL] + counts[business_logic.OUT_OF_STOCK]
    watching = counts[business_logic.ATTENTION]
    if needs_action == 0 and watching == 0:
        return "All products currently hold enough stock for the demand expected this week."
    if healthy >= total * 0.7 and needs_action <= 1:
        return (
            f"Most products currently have sufficient stock, "
            f"while {watching + needs_action} "
            f"{pluralize(watching + needs_action, 'product needs', 'products need')} "
            "closer monitoring."
        )
    if needs_action >= 3:
        return (
            f"Several products require replenishment attention: {needs_action} "
            f"{pluralize(needs_action, 'product is', 'products are')} "
            "below the stock level expected demand suggests."
        )
    return (
        f"{healthy} of {total} products are comfortably stocked, "
        f"and {needs_action + watching} "
        f"{pluralize(needs_action + watching, 'product', 'products')} "
        "should be reviewed before the coming week."
    )


def generate_forecast_insight(product_name, current_stock, expected_demand, unit_of_measure):
    if expected_demand <= 0:
        return (
            f"Very little demand is expected for {product_name} over the next seven days, "
            "so current stock should be sufficient."
        )
    if current_stock == 0:
        return (
            f"{product_name} is currently out of stock while about "
            f"{format_units(expected_demand)} {unit_of_measure} are expected to be needed "
            "over the next seven days. Replenishment should be arranged."
        )
    coverage = business_logic.coverage_ratio(current_stock, expected_demand)
    if coverage < business_logic.CRITICAL_COVERAGE:
        shortfall = expected_demand - current_stock
        return (
            f"Expected demand is higher than current stock. About "
            f"{format_units(shortfall)} {unit_of_measure} more than the amount on hand may be "
            "needed this week, so replenishment should be considered."
        )
    if coverage < business_logic.ATTENTION_COVERAGE:
        return (
            f"Current stock of {product_name} is close to the demand expected over the next "
            "seven days. It is worth reviewing before stock runs low."
        )
    cover = business_logic.format_days_of_cover(
        business_logic.days_of_cover(current_stock, expected_demand)
    )
    return (
        f"Current stock appears sufficient for the demand expected for {product_name} over the "
        f"next seven days, covering roughly {cover.lower()}."
    )


def generate_reorder_insight(status_table):
    if status_table.empty:
        return "No products match this selection."
    urgent = business_logic.urgent_products(status_table)
    watching = status_table[status_table["status"] == business_logic.ATTENTION]
    if urgent.empty and watching.empty:
        return "No products currently require a purchasing decision."
    if urgent.empty:
        names = ", ".join(watching["product_name"].head(3))
        return f"No urgent purchases are indicated. Worth reviewing: {names}."
    leading = urgent.iloc[0]
    return (
        f"{len(urgent)} {pluralize(len(urgent), 'product', 'products')} should be restocked soon. "
        f"{leading['product_name']} is the most pressing, with "
        f"{format_units(leading['current_stock'])} in stock against about "
        f"{format_units(leading['expected_demand'])} expected this week."
    )


def generate_product_insight(product_row, product_sales, reference_date=None):
    name = product_row["product_name"]
    unit = product_row["unit_of_measure"]
    status = product_row["status"]
    trend = analytics.sales_trend(product_sales, reference_date)
    pattern = analytics.weekday_demand_pattern(product_sales)
    sentences = [
        generate_forecast_insight(
            name,
            int(product_row["current_stock"]),
            int(product_row["expected_demand"]),
            unit,
        )
    ]
    if trend["direction"] == analytics.TREND_RISING:
        sentences.append(
            f"Demand has been growing recently, up about "
            f"{format_percentage(trend['change_ratio'])} over the last four weeks."
        )
    elif trend["direction"] == analytics.TREND_DECLINING:
        sentences.append(
            f"Demand has eased recently, down about "
            f"{format_percentage(trend['change_ratio'])} over the last four weeks."
        )
    else:
        sentences.append("Demand has been steady over the last four weeks.")
    if not pattern.empty:
        busiest = pattern.loc[pattern["average_units"].idxmax(), "weekday"]
        sentences.append(f"{busiest} is usually the busiest day for this product.")
    if status in (business_logic.CRITICAL, business_logic.OUT_OF_STOCK):
        sentences.append("This product is on the list of items needing attention.")
    return " ".join(sentences)


def generate_business_insights(sales, status_table, reference_date=None, limit=MAX_INSIGHTS):
    insights = []
    reference = pd.Timestamp(reference_date) if reference_date else sales["sale_date"].max()
    recent_sales = analytics.filter_sales(
        sales, start_date=reference - pd.Timedelta(days=RECENT_WINDOW_DAYS - 1), end_date=reference
    )
    leaders = analytics.top_products(recent_sales, limit=1)
    if not leaders.empty:
        leader = leaders.iloc[0]
        insights.append(
            f"{leader['product_name']} is currently the highest-demand product, with "
            f"{format_units(leader['units_sold'])} {leader['unit_of_measure']} sold in the last "
            f"{RECENT_WINDOW_DAYS} days."
        )
    category_totals = analytics.sales_by_category(recent_sales)
    if len(category_totals) > 1:
        top_category = category_totals.iloc[0]
        insights.append(
            f"{top_category['category']} account for the largest share of recent sales, at about "
            f"{format_percentage(top_category['share'])} of units sold."
        )
    if not status_table.empty:
        needs_restock = business_logic.urgent_products(status_table)
        if not needs_restock.empty:
            insights.append(
                f"{len(needs_restock)} "
                f"{pluralize(len(needs_restock), 'product may', 'products may')} require "
                "replenishment before expected demand is met."
            )
        else:
            insights.append(
                "No products are currently below the stock level expected demand suggests."
            )
    weekday_ratio = analytics.weekday_versus_weekend(recent_sales)
    if weekday_ratio > 1.15:
        insights.append(
            f"Demand is stronger on weekdays than weekends, by roughly "
            f"{weekday_ratio:.1f} times the weekend average."
        )
    elif 0 < weekday_ratio < 0.9:
        insights.append("Weekend demand has been unusually strong compared with weekdays.")
    if not status_table.empty:
        tightest = status_table.iloc[0]
        if tightest["status"] != business_logic.HEALTHY:
            insights.append(
                f"{tightest['product_name']} has lower stock "
                f"({format_units(tightest['current_stock'])}) than the "
                f"{format_units(tightest['expected_demand'])} expected over the next seven days."
            )
    slow_movers = analytics.slow_moving_products(recent_sales, limit=1)
    if not slow_movers.empty:
        slowest = slow_movers.iloc[0]
        insights.append(
            f"{slowest['product_name']} has been the slowest-moving product recently, with only "
            f"{format_units(slowest['units_sold'])} {slowest['unit_of_measure']} sold in the last "
            f"{RECENT_WINDOW_DAYS} days."
        )
    trend_message = generate_sales_insight(sales, reference)
    insights.append(trend_message)
    return insights[:limit]


def build_business_story(sales, status_table, forecast, reference_date=None):
    reference = pd.Timestamp(reference_date) if reference_date else sales["sale_date"].max()
    recent_units = analytics.units_sold_in_window(sales, reference, RECENT_WINDOW_DAYS)
    previous_window_end = reference - pd.Timedelta(days=RECENT_WINDOW_DAYS)
    previous_units = analytics.units_sold_in_window(
        sales, previous_window_end, RECENT_WINDOW_DAYS
    )
    leaders = analytics.top_products(
        analytics.filter_sales(
            sales,
            start_date=reference - pd.Timedelta(days=RECENT_WINDOW_DAYS - 1),
            end_date=reference,
        ),
        limit=3,
    )
    leading_names = ", ".join(leaders["product_name"]) if not leaders.empty else "no products"
    if previous_units:
        change = (recent_units - previous_units) / previous_units
        movement = (
            f"about {format_percentage(change)} "
            f"{'higher' if change >= 0 else 'lower'} than the previous 30 days"
        )
    else:
        movement = "the first recorded period of activity"
    counts = business_logic.status_counts(status_table)
    expected_total = int(round(forecast["expected_units"].sum())) if not forecast.empty else 0
    urgent = business_logic.urgent_products(status_table)
    watching = status_table[status_table["status"] == business_logic.ATTENTION]

    what_happened = (
        f"Over the last {RECENT_WINDOW_DAYS} days the business sold "
        f"{format_units(recent_units)} units, {movement}. The strongest sellers were "
        f"{leading_names}."
    )
    position_segments = [
        (counts[business_logic.HEALTHY], "comfortably stocked"),
        (counts[business_logic.ATTENTION], "close to expected demand"),
        (counts[business_logic.CRITICAL], "below expected demand"),
        (counts[business_logic.OUT_OF_STOCK], "out of stock"),
    ]
    described = [
        f"{count} {pluralize(count, 'is', 'are')} {description}"
        for count, description in position_segments
    ]
    what_is_happening = (
        f"Of {len(status_table)} {pluralize(len(status_table), 'product')}, "
        f"{', '.join(described[:-1])}, and {described[-1]}."
    )
    what_may_happen = (
        f"Around {format_units(expected_total)} units are expected to be needed across all "
        f"products over the next {FORECAST_WINDOW_DAYS} days, based on how each product has "
        "been selling."
    )
    if urgent.empty:
        what_needs_attention = (
            "No product is currently short of the stock its expected demand suggests."
        )
    else:
        urgent_names = ", ".join(urgent["product_name"].head(4))
        what_needs_attention = (
            f"{len(urgent)} {pluralize(len(urgent), 'product needs', 'products need')} "
            f"attention first: {urgent_names}."
        )
    if urgent.empty and watching.empty:
        what_to_consider = "No purchasing action appears necessary this week."
    else:
        restock_names = ", ".join(urgent["product_name"].head(3))
        review_names = ", ".join(watching["product_name"].head(3))
        parts = []
        if restock_names:
            parts.append(f"Restock soon: {restock_names}.")
        if review_names:
            parts.append(f"Worth reviewing: {review_names}.")
        what_to_consider = " ".join(parts)

    return [
        ("What Happened?", what_happened),
        ("What Is Happening Now?", what_is_happening),
        ("What May Happen Next?", what_may_happen),
        ("What Needs Attention?", what_needs_attention),
        ("What Should We Consider?", what_to_consider),
    ]

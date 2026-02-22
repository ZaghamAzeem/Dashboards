from __future__ import annotations

from dashboard import business_logic as rules

MAX_STORY_LINES = 3
MAX_INSIGHTS = 6


def sales_story(performance, momentum):
    leader = rules.category_leader(performance)
    if leader is None:
        return None

    direction = rules.sales_momentum_headline(momentum["change_pct"])
    return (
        f"{leader['category']} products are leading sales with "
        f"{leader['share']:.0f}% of the money taken. {direction}."
    )


def inventory_story(counts):
    needing_attention = counts[rules.STATUS_OUT] + counts[rules.STATUS_RESTOCK]
    watching = counts[rules.STATUS_LOW]

    if needing_attention == 0 and watching == 0:
        return "Every product on the shelf has enough stock for the week ahead."
    if needing_attention == 0:
        return f"{watching} products are running low and are worth watching this week."
    if counts[rules.STATUS_OUT] == 0:
        return (
            f"{needing_attention} products need restocking, "
            f"and {watching} more are running low."
        )
    return (
        f"{counts[rules.STATUS_OUT]} products have run out completely and "
        f"{counts[rules.STATUS_RESTOCK]} more need restocking soon."
    )


def favourite_product_story(leaderboard):
    if leaderboard.empty:
        return None
    best = leaderboard.iloc[0]
    return (
        f"{best['product_name']} is the shop favourite with "
        f"{rules.format_units(best['units'])} units sold in this period."
    )


def momentum_story(rising):
    if rising.empty:
        return "No product is showing a clear jump in sales at the moment."
    best = rising.iloc[0]
    return (
        f"{best['product_name']} is selling faster than before, up from "
        f"{rules.format_units(best['previous'])} to {rules.format_units(best['recent'])} units."
    )


def forecast_story(overview):
    if overview.empty:
        return None
    busiest = overview.sort_values("expected_demand", ascending=False).iloc[0]
    if busiest["expected_demand"] <= 0:
        return "No strong demand is expected in the coming week."
    return (
        f"{busiest['product_name']} is expected to be the busiest seller next week with "
        f"around {rules.format_units(busiest['expected_demand'])} units of demand."
    )


def restock_story(overview):
    urgent = overview.loc[overview["priority"] == rules.PRIORITY_HIGH]
    if urgent.empty:
        return "Nothing on the shelf needs an urgent order this week."
    top = urgent.iloc[0]
    return (
        f"{top['product_name']} is the most pressing item to reorder, with "
        f"{rules.format_units(top['current_stock'])} in stock against "
        f"{rules.format_units(top['expected_demand'])} units of expected demand."
    )


def busiest_day_story(pattern):
    busiest = rules.busiest_weekday(pattern)
    if busiest is None:
        return None
    return (
        f"{busiest['weekday']} is currently the busiest sales day, taking about "
        f"{busiest['lift_pct']:.0f}% more than an average day. "
        f"{busiest['quietest']} is the quietest."
    )


def seasonal_story(peaks):
    if peaks.empty:
        return None
    strongest = peaks.iloc[0]
    return (
        f"{strongest['category']} demand swings the most across the year, peaking in "
        f"{strongest['month']} and easing off in {strongest['quiet_month']}."
    )


def slow_mover_story(movers):
    if movers.empty:
        return None
    quietest = movers.iloc[0]
    return (
        f"{quietest['product_name']} is the slowest seller right now with only "
        f"{rules.format_units(quietest['units'])} units sold recently."
    )


def build_todays_story(performance, momentum, counts, overview, leaderboard):
    lines = []
    for candidate in (
        sales_story(performance, momentum),
        inventory_story(counts),
        forecast_story(overview),
        favourite_product_story(leaderboard),
    ):
        if candidate:
            lines.append(candidate)
    return lines[:MAX_STORY_LINES]


def build_smart_insights(
    performance, momentum, leaderboard, rising, overview, counts, pattern, peaks, movers
):
    candidates = [
        ("🏅", "Strongest Sport", sales_story(performance, momentum)),
        ("🥇", "Shop Favourite", favourite_product_story(leaderboard)),
        ("🔥", "Gaining Attention", momentum_story(rising)),
        ("📦", "Stock Health", inventory_story(counts)),
        ("🔮", "Coming Week", forecast_story(overview)),
        ("🛒", "First To Reorder", restock_story(overview)),
        ("📅", "Busiest Day", busiest_day_story(pattern)),
        ("🌦️", "Seasonal Swing", seasonal_story(peaks)),
        ("🐢", "Moving Slowly", slow_mover_story(movers)),
    ]
    insights = [
        {"icon": icon, "title": title, "text": text}
        for icon, title, text in candidates
        if text
    ]
    return insights[:MAX_INSIGHTS]

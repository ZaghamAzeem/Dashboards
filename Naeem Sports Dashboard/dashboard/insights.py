from __future__ import annotations

from dashboard import business_logic as rules

MAX_STORY_LINES = 3
MAX_INSIGHTS = 6


def _plural(count, word):
    return word if count == 1 else f"{word}s"


def _is_are(count):
    return "is" if count == 1 else "are"


def _needs(count):
    return "needs" if count == 1 else "need"


def sales_story(performance, momentum, selected_sport=None):
    if performance.empty:
        return None

    direction = rules.sales_momentum_headline(momentum["change_pct"])
    chosen = performance.loc[performance["category"] == selected_sport]

    if selected_sport and not chosen.empty:
        row = chosen.iloc[0]
        return (
            f"{selected_sport} products took {rules.format_currency(row['revenue'])} in this "
            f"period, {row['share']:.0f}% of everything the shop sold. {direction}."
        )

    leader = rules.category_leader(performance)
    return (
        f"{leader['category']} products are leading sales with "
        f"{leader['share']:.0f}% of the money taken. {direction}."
    )


def inventory_story(counts):
    out = counts[rules.STATUS_OUT]
    restock = counts[rules.STATUS_RESTOCK]
    low = counts[rules.STATUS_LOW]

    if out == 0 and restock == 0 and low == 0:
        return "Every product on the shelf has enough stock for the week ahead."
    if out == 0 and restock == 0:
        return (
            f"{low} {_plural(low, 'product')} {_is_are(low)} running low "
            "and worth watching this week."
        )
    if out == 0:
        return (
            f"{restock} {_plural(restock, 'product')} {_is_are(restock)} below the stock "
            f"needed for this week, and {low} more {_is_are(low)} running low."
        )
    if restock == 0:
        return (
            f"{out} {_plural(out, 'product')} {_is_are(out)} completely out of stock, "
            f"with {low} more running low."
        )
    return (
        f"{out} {_plural(out, 'product')} {_is_are(out)} completely out of stock and "
        f"{restock} more {_needs(restock)} restocking soon."
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


def build_todays_story(performance, momentum, counts, overview, leaderboard, selected_sport=None):
    lines = []
    for candidate in (
        sales_story(performance, momentum, selected_sport),
        inventory_story(counts),
        forecast_story(overview),
        favourite_product_story(leaderboard),
    ):
        if candidate:
            lines.append(candidate)
    return lines[:MAX_STORY_LINES]


def build_smart_insights(
    performance,
    momentum,
    leaderboard,
    rising,
    overview,
    counts,
    pattern,
    peaks,
    movers,
    selected_sport=None,
):
    candidates = [
        ("🏅", "Sales Picture", sales_story(performance, momentum, selected_sport)),
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

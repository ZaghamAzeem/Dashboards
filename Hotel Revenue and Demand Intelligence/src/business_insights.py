from __future__ import annotations

import pandas as pd

from src import analytics
from src.customer_analysis import (
    customer_type_profile,
    repeat_guest_comparison,
    segment_guests,
    segment_summary,
)
from src.utils import format_money, format_number, format_percent


def _insight(title: str, text: str, tone: str, weight: float) -> dict:
    return {"title": title, "text": text, "tone": tone, "weight": weight}


def _direction_word(change: float) -> str:
    return "ahead of" if change > 0 else "behind"


def business_story(context, limit: int = 5) -> list[dict]:
    if not context.has_data:
        return []

    candidates: list[dict] = []
    kpis = context.kpis
    changes = context.changes

    revenue_change = changes.get("revenue")
    if revenue_change is not None and abs(revenue_change) >= 1:
        tone = "healthy" if revenue_change > 0 else "watch"
        candidates.append(_insight(
            "Revenue",
            f"Room revenue reached {format_money(kpis['revenue'])} for this period, "
            f"{abs(revenue_change):.1f}% {_direction_word(revenue_change)} the previous period.",
            tone,
            abs(revenue_change) + 6,
        ))

    occupancy_change = changes.get("occupancy_rate")
    if occupancy_change is not None and abs(occupancy_change) >= 1:
        tone = "healthy" if occupancy_change > 0 else "watch"
        candidates.append(_insight(
            "Room demand",
            f"Rooms were {format_percent(kpis['occupancy_rate'])} full on average, "
            f"{abs(occupancy_change):.1f}% {_direction_word(occupancy_change)} the previous period.",
            tone,
            abs(occupancy_change) + 4,
        ))

    adr_change = changes.get("adr")
    if adr_change is not None and abs(adr_change) >= 1.5:
        tone = "healthy" if adr_change > 0 else "watch"
        candidates.append(_insight(
            "Average room rate",
            f"The average nightly rate was {format_money(kpis['adr'], 2)}, "
            f"{abs(adr_change):.1f}% {_direction_word(adr_change)} the previous period.",
            tone,
            abs(adr_change) + 2,
        ))

    revenue_by_room = analytics.revenue_by_dimension(context.room_nights, "room_type")
    if not revenue_by_room.empty:
        top = revenue_by_room.iloc[0]
        candidates.append(_insight(
            "Leading room category",
            f"{top['room_type']}s generated {format_money(top['revenue'])}, "
            f"{top['revenue_share']:.0f}% of all room revenue, at an average rate of "
            f"{format_money(top['adr'], 0)} a night.",
            "healthy",
            8,
        ))

    if not context.weekday.empty and context.weekday["revenue"].notna().any():
        weekday = context.weekday.dropna(subset=["revenue"])
        best = weekday.loc[weekday["revenue"].idxmax()]
        worst = weekday.loc[weekday["revenue"].idxmin()]
        gap = (best["revenue"] - worst["revenue"]) / worst["revenue"] * 100 if worst["revenue"] else 0
        if gap >= 8:
            candidates.append(_insight(
                "Best trading days",
                f"{best['weekday']}s earn about {gap:.0f}% more room revenue than {worst['weekday']}s, "
                f"averaging {format_money(best['revenue'])} a day at "
                f"{format_percent(best['occupancy_rate'])} occupancy.",
                "neutral",
                gap * 0.4 + 5,
            ))

    channel_cancellations = analytics.cancellation_breakdown(context.bookings, "booking_channel")
    if len(channel_cancellations) >= 2:
        worst = channel_cancellations.iloc[0]
        best = channel_cancellations.iloc[-1]
        if worst["cancellation_rate"] - best["cancellation_rate"] >= 6:
            candidates.append(_insight(
                "Cancellations",
                f"{worst['booking_channel']} bookings are cancelled "
                f"{worst['cancellation_rate']:.0f}% of the time, against "
                f"{best['cancellation_rate']:.0f}% for {best['booking_channel']} bookings.",
                "watch",
                (worst["cancellation_rate"] - best["cancellation_rate"]) * 0.5 + 5,
            ))

    repeat = repeat_guest_comparison(context.bookings, context.room_nights)
    if len(repeat) == 2 and repeat["revenue_per_guest"].min() > 0:
        returning = repeat.loc[repeat["guest_group"] == "Returning guests"]
        first_time = repeat.loc[repeat["guest_group"] == "First-time guests"]
        if not returning.empty and not first_time.empty:
            uplift = (
                returning["revenue_per_guest"].iat[0] / first_time["revenue_per_guest"].iat[0] - 1
            ) * 100
            if abs(uplift) >= 5:
                candidates.append(_insight(
                    "Returning guests",
                    f"Each returning guest is worth "
                    f"{format_money(returning['revenue_per_guest'].iat[0])} over the period, "
                    f"{abs(uplift):.0f}% {'more' if uplift > 0 else 'less'} than a first-time guest, "
                    f"and they cancel {returning['cancellation_rate'].iat[0]:.0f}% of bookings "
                    f"against {first_time['cancellation_rate'].iat[0]:.0f}%.",
                    "healthy" if uplift > 0 else "watch",
                    min(abs(uplift) * 0.2, 12) + 5,
                ))

    pressure = analytics.occupancy_pressure(context.daily)
    if pressure.get("peak_days", 0) >= max(context.days * 0.08, 3):
        candidates.append(_insight(
            "Busy nights",
            f"{pressure['peak_days']} nights ran at 90% occupancy or higher, "
            f"including {pd.Timestamp(pressure['best_day']):%d %B %Y}. "
            "Those dates carry the most pricing power.",
            "neutral",
            7,
        ))

    ranked = sorted(candidates, key=lambda item: item["weight"], reverse=True)
    return ranked[:limit]


def revenue_insights(context) -> list[dict]:
    if not context.has_data or context.monthly.empty:
        return []
    insights = []
    complete_months = context.monthly.loc[context.monthly["days"] >= 28]
    reference = complete_months if len(complete_months) >= 2 else context.monthly

    if len(reference) >= 2:
        best = reference.loc[reference["revenue"].idxmax()]
        weakest = reference.loc[reference["revenue"].idxmin()]
        insights.append(_insight(
            "Strongest month",
            f"{best['month_label']} was the strongest month with {format_money(best['revenue'])} "
            f"in room revenue at {format_percent(best['occupancy_rate'])} occupancy.",
            "healthy", 10,
        ))
        insights.append(_insight(
            "Quietest month",
            f"{weakest['month_label']} was the quietest with {format_money(weakest['revenue'])} "
            f"and {format_percent(weakest['occupancy_rate'])} occupancy.",
            "watch", 9,
        ))

    trend = analytics.revenue_trend_direction(context.monthly)
    if trend["change"] is not None:
        wording = {
            "growing": "building",
            "softening": "easing back",
            "steady": "holding steady",
        }[trend["direction"]]
        tone = {"growing": "healthy", "softening": "watch", "steady": "neutral"}[trend["direction"]]
        comparison = (
            "the same three months a year earlier"
            if trend["basis"] == "year_on_year"
            else "the three months before that, which partly reflects the time of year"
        )
        insights.append(_insight(
            "Recent direction",
            f"Revenue is {wording}: the last three months averaged "
            f"{format_money(trend['recent'])} a month against {format_money(trend['previous'])} "
            f"in {comparison} ({trend['change']:+.1f}%).",
            tone, 11,
        ))

    for dimension, label in (("room_type", "room category"), ("booking_channel", "booking source"),
                             ("customer_type", "guest type")):
        breakdown = analytics.revenue_by_dimension(context.room_nights, dimension)
        if breakdown.empty:
            continue
        top = breakdown.iloc[0]
        insights.append(_insight(
            f"Top {label}",
            f"{top[dimension]} leads this {label} with {format_money(top['revenue'])} "
            f"({top['revenue_share']:.0f}% of room revenue) at {format_money(top['adr'], 0)} a night.",
            "neutral", 8,
        ))

    daily = context.daily
    if not daily.empty and len(daily) >= 14:
        threshold = daily["revenue"].quantile(0.92)
        strong_days = daily.loc[daily["revenue"] >= threshold]
        if not strong_days.empty:
            insights.append(_insight(
                "Peak trading days",
                f"The busiest {len(strong_days)} nights each earned at least "
                f"{format_money(threshold)}, averaging "
                f"{format_percent(strong_days['occupancy_rate'].mean())} occupancy.",
                "healthy", 7,
            ))
    return sorted(insights, key=lambda item: item["weight"], reverse=True)


def booking_insights(context) -> list[dict]:
    if not context.has_data:
        return []
    insights = []
    lead = analytics.booking_lead_time_profile(context.bookings)
    if not lead.empty:
        top = lead.loc[lead["bookings"].idxmax()]
        insights.append(_insight(
            "Booking window",
            f"Most rooms are reserved {str(top['lead_time_group']).lower()} "
            f"({top['share']:.0f}% of confirmed bookings). The average booking arrives "
            f"{format_number(context.kpis['average_lead_time'])} days after it is made.",
            "neutral", 9,
        ))

    weekday_bookings = analytics.booking_weekday_profile(context.bookings)
    if not weekday_bookings.empty:
        busiest = weekday_bookings.loc[weekday_bookings["bookings"].idxmax()]
        insights.append(_insight(
            "When guests book",
            f"{busiest['booking_weekday']} is the most active booking day, carrying "
            f"{busiest['share']:.0f}% of all reservations made.",
            "neutral", 7,
        ))

    by_customer = analytics.bookings_by_dimension(context.bookings, "customer_type")
    if not by_customer.empty:
        top = by_customer.iloc[0]
        insights.append(_insight(
            "Main guest type",
            f"{top['customer_type']} guests account for {top['bookings']:,} confirmed bookings "
            f"with an average stay of {top['average_length_of_stay']:.1f} nights.",
            "neutral", 8,
        ))

    if not context.seasonal.empty:
        best = context.seasonal.loc[context.seasonal["occupancy_rate"].idxmax()]
        quiet = context.seasonal.loc[context.seasonal["occupancy_rate"].idxmin()]
        insights.append(_insight(
            "Seasonal demand",
            f"{best['season']} is the busiest season at "
            f"{format_percent(best['occupancy_rate'])} occupancy, while {quiet['season']} runs at "
            f"{format_percent(quiet['occupancy_rate'])}.",
            "neutral", 10,
        ))
    return sorted(insights, key=lambda item: item["weight"], reverse=True)


def room_insights(context, performance: pd.DataFrame) -> list[dict]:
    if performance is None or performance.empty:
        return []
    insights = []
    best = performance.iloc[0]
    insights.append(_insight(
        "Best performing category",
        f"{best['room_type']} leads on overall performance with "
        f"{format_percent(best['occupancy_rate'])} occupancy and "
        f"{format_money(best['revpar'], 0)} earned per available room each night.",
        "healthy", 10,
    ))

    weakest = performance.iloc[-1]
    if weakest["room_type"] != best["room_type"]:
        insights.append(_insight(
            "Category to review",
            f"{weakest['room_type']} sits at {format_percent(weakest['occupancy_rate'])} occupancy "
            f"and achieves {weakest['rate_realisation']:.0f}% of its published rate.",
            "watch" if weakest["status"] == "Needs Attention" else "neutral", 9,
        ))

    highest_revenue = performance.loc[performance["revenue"].idxmax()]
    if highest_revenue["room_type"] != best["room_type"]:
        insights.append(_insight(
            "Biggest revenue contributor",
            f"{highest_revenue['room_type']} brings in the most money overall: "
            f"{format_money(highest_revenue['revenue'])}, "
            f"{highest_revenue['revenue_share']:.0f}% of room revenue.",
            "neutral", 8,
        ))

    most_cancelled = performance.loc[performance["cancellation_rate"].idxmax()]
    if most_cancelled["cancellation_rate"] >= 20:
        insights.append(_insight(
            "Cancellation exposure",
            f"{most_cancelled['room_type']} bookings are cancelled "
            f"{format_percent(most_cancelled['cancellation_rate'])} of the time, "
            "the highest of any category.",
            "watch", 7,
        ))
    return sorted(insights, key=lambda item: item["weight"], reverse=True)


def guest_insights(context) -> list[dict]:
    if not context.has_data:
        return []
    insights = []
    profile = customer_type_profile(context.bookings, context.room_nights)
    if not profile.empty:
        top = profile.iloc[0]
        insights.append(_insight(
            "Most valuable guest type",
            f"{top['customer_type']} guests contribute {format_money(top['revenue'])} "
            f"({top['revenue_share']:.0f}% of room revenue) at "
            f"{format_money(top['revenue_per_booking'], 0)} per stay.",
            "healthy", 10,
        ))
        longest = profile.loc[profile["average_length_of_stay"].idxmax()]
        insights.append(_insight(
            "Longest stays",
            f"{longest['customer_type']} guests stay the longest at "
            f"{longest['average_length_of_stay']:.1f} nights on average.",
            "neutral", 7,
        ))

    guest_ids = set(context.bookings["guest_id"].unique())
    segmented = segment_guests(context.guests.loc[context.guests["guest_id"].isin(guest_ids)])
    summary = segment_summary(segmented)
    if not summary.empty:
        high_value = summary.loc[summary["segment"].astype(str) == "High Value"]
        if not high_value.empty:
            row = high_value.iloc[0]
            insights.append(_insight(
                "High value guests",
                f"{format_number(row['guests'])} guests sit in the high value group: "
                f"{row['guest_share']:.0f}% of guests producing {row['revenue_share']:.0f}% "
                f"of guest spending, averaging {format_money(row['average_spend'])} each.",
                "healthy", 11,
            ))

    repeat = repeat_guest_comparison(context.bookings, context.room_nights)
    if len(repeat) == 2:
        returning = repeat.loc[repeat["guest_group"] == "Returning guests"].iloc[0]
        insights.append(_insight(
            "Returning business",
            f"Returning guests account for {returning['revenue_share']:.0f}% of room revenue "
            f"and cancel {format_percent(returning['cancellation_rate'])} of their bookings.",
            "neutral", 9,
        ))
    return sorted(insights, key=lambda item: item["weight"], reverse=True)


def cancellation_insights(context) -> list[dict]:
    if not context.has_data:
        return []
    insights = []
    summary = analytics.cancellation_summary(context.bookings)
    insights.append(_insight(
        "Overall position",
        f"{format_number(summary['cancelled_bookings'])} of "
        f"{format_number(len(context.bookings))} reservations were cancelled "
        f"({format_percent(summary['cancellation_rate'])}), representing "
        f"{format_money(summary['lost_value'])} of room value that had to be resold.",
        "watch" if summary["cancellation_rate"] >= 20 else "neutral", 12,
    ))

    for dimension, label in (("booking_channel", "booking source"),
                             ("customer_type", "guest type"),
                             ("room_type", "room category")):
        breakdown = analytics.cancellation_breakdown(context.bookings, dimension)
        if len(breakdown) < 2:
            continue
        worst = breakdown.iloc[0]
        best = breakdown.iloc[-1]
        gap = worst["cancellation_rate"] - best["cancellation_rate"]
        if gap < 4:
            continue
        insights.append(_insight(
            f"By {label}",
            f"{worst[dimension]} shows the highest cancellation rate at "
            f"{format_percent(worst['cancellation_rate'])}, against "
            f"{format_percent(best['cancellation_rate'])} for {best[dimension]}.",
            "watch" if gap >= 10 else "neutral", gap,
        ))

    lead = analytics.cancellation_breakdown(context.bookings, "lead_time_group")
    if len(lead) >= 2:
        latest = lead.loc[lead["cancellation_rate"].idxmax()]
        earliest = lead.loc[lead["cancellation_rate"].idxmin()]
        insights.append(_insight(
            "Booking window effect",
            f"Reservations made {str(latest['lead_time_group']).lower()} are cancelled "
            f"{format_percent(latest['cancellation_rate'])} of the time, compared with "
            f"{format_percent(earliest['cancellation_rate'])} for bookings made "
            f"{str(earliest['lead_time_group']).lower()}.",
            "watch", 11,
        ))

    promotion = context.bookings.groupby("promotion_used")["is_cancelled"].agg(["mean", "size"])
    if len(promotion) == 2 and promotion["size"].min() >= 40:
        promo_rate = promotion.loc[1, "mean"] * 100
        standard_rate = promotion.loc[0, "mean"] * 100
        if abs(promo_rate - standard_rate) >= 3:
            insights.append(_insight(
                "Promotional bookings",
                f"Bookings taken on a promotional rate are cancelled "
                f"{format_percent(promo_rate)} of the time against "
                f"{format_percent(standard_rate)} at standard rates.",
                "watch" if promo_rate > standard_rate else "healthy",
                abs(promo_rate - standard_rate) + 3,
            ))
    return sorted(insights, key=lambda item: item["weight"], reverse=True)


def _recommendation(category: str, title: str, body: str, action: str,
                    tone: str, priority: float) -> dict:
    return {
        "category": category,
        "title": title,
        "body": body,
        "action": action,
        "tone": tone,
        "priority": priority,
    }


def management_recommendations(context, performance: pd.DataFrame,
                               forecast_result: dict | None = None) -> list[dict]:
    if not context.has_data:
        return []

    recommendations: list[dict] = []
    hotel_occupancy = context.kpis["occupancy_rate"]
    hotel_cancellation = context.kpis["cancellation_rate"]

    if performance is not None and not performance.empty:
        pricing = performance.loc[
            (performance["occupancy_rate"] >= hotel_occupancy + 3)
            & (performance["rate_realisation"] < 97)
        ]
        if not pricing.empty:
            row = pricing.sort_values("occupancy_rate", ascending=False).iloc[0]
            recommendations.append(_recommendation(
                "Revenue Opportunity",
                f"{row['room_type']} is filling faster than the rest of the hotel",
                f"{row['room_type']} runs at {format_percent(row['occupancy_rate'])} occupancy "
                f"against {format_percent(hotel_occupancy)} for the hotel overall, yet its average "
                f"rate of {format_money(row['adr'], 0)} is only {row['rate_realisation']:.0f}% of the "
                f"published rate of {format_money(row['base_rate'], 0)}. Demand is stronger than the "
                "price currently reflects.",
                f"Review {row['room_type']} pricing on the busiest nights before releasing more availability.",
                "watch", 3.2,
            ))

        attention = performance.loc[performance["status"] == "Needs Attention"]
        if not attention.empty:
            row = attention.iloc[-1]
            recommendations.append(_recommendation(
                "Room Performance",
                f"{row['room_type']} is not keeping pace",
                f"{row['room_type']} is filling at {format_percent(row['occupancy_rate'])} and earning "
                f"{format_money(row['revpar'], 0)} per available room each night, the weakest of the "
                f"room categories. It contributes {row['revenue_share']:.0f}% of room revenue from "
                f"{row['rooms_available']:.0f} rooms.",
                f"Consider packaging or repositioning {row['room_type']} for quieter midweek nights.",
                "priority", 3.6,
            ))

    channel_cancellations = analytics.cancellation_breakdown(context.bookings, "booking_channel")
    if not channel_cancellations.empty:
        worst = channel_cancellations.iloc[0]
        share = worst["total"] / len(context.bookings) * 100
        if worst["cancellation_rate"] >= hotel_cancellation * 1.2 and share >= 8:
            recommendations.append(_recommendation(
                "Cancellation Concern",
                f"{worst['booking_channel']} bookings fall away most often",
                f"{worst['booking_channel']} carries {share:.0f}% of all reservations but cancels "
                f"{format_percent(worst['cancellation_rate'])} of them, against "
                f"{format_percent(hotel_cancellation)} across the hotel. That accounts for "
                f"{format_money(worst['lost_value'])} of room value returned to sale.",
                "Review deposit and cancellation terms on this source, and hold back inventory on peak dates.",
                "priority", 3.8,
            ))

    lead_cancellations = analytics.cancellation_breakdown(context.bookings, "lead_time_group")
    if len(lead_cancellations) >= 2:
        worst_lead = lead_cancellations.iloc[0]
        best_lead = lead_cancellations.iloc[-1]
        if worst_lead["cancellation_rate"] - best_lead["cancellation_rate"] >= 10:
            recommendations.append(_recommendation(
                "Booking Risk",
                "Early reservations are the least reliable",
                f"Rooms booked {str(worst_lead['lead_time_group']).lower()} are cancelled "
                f"{format_percent(worst_lead['cancellation_rate'])} of the time, while bookings made "
                f"{str(best_lead['lead_time_group']).lower()} hold at "
                f"{format_percent(best_lead['cancellation_rate'])}. Early demand should be treated as "
                "provisional when planning staffing and supplies.",
                "Apply a deposit or firmer terms to reservations taken far in advance.",
                "watch", 2.9,
            ))

    repeat = repeat_guest_comparison(context.bookings, context.room_nights)
    if len(repeat) == 2:
        returning = repeat.loc[repeat["guest_group"] == "Returning guests"].iloc[0]
        first_time = repeat.loc[repeat["guest_group"] == "First-time guests"].iloc[0]
        if returning["revenue_per_guest"] > first_time["revenue_per_guest"] * 1.05:
            uplift = (returning["revenue_per_guest"] / first_time["revenue_per_guest"] - 1) * 100
            recommendations.append(_recommendation(
                "Guest Opportunity",
                "Returning guests are worth more and cancel less",
                f"Each returning guest is worth {format_money(returning['revenue_per_guest'], 0)} over "
                f"this period against {format_money(first_time['revenue_per_guest'], 0)} for a "
                f"first-time guest ({uplift:+.0f}%), booking "
                f"{returning['bookings_per_guest']:.1f} stays each. They also cancel "
                f"{format_percent(returning['cancellation_rate'])} of bookings compared with "
                f"{format_percent(first_time['cancellation_rate'])}, and supply "
                f"{returning['revenue_share']:.0f}% of room revenue.",
                "Build a simple loyalty offer for guests who have stayed before, focused on quieter months.",
                "healthy", 3.0,
            ))

    guest_ids = set(context.bookings["guest_id"].unique())
    summary = segment_summary(
        segment_guests(context.guests.loc[context.guests["guest_id"].isin(guest_ids)])
    )
    if not summary.empty:
        high_value = summary.loc[summary["segment"].astype(str) == "High Value"]
        if not high_value.empty:
            row = high_value.iloc[0]
            if row["revenue_share"] >= row["guest_share"] * 1.2:
                recommendations.append(_recommendation(
                    "Guest Opportunity",
                    "A small group of guests carries a large share of spending",
                    f"The high value group is {row['guest_share']:.0f}% of guests but produces "
                    f"{row['revenue_share']:.0f}% of guest spending, at "
                    f"{format_money(row['average_spend'])} each across "
                    f"{row['average_stays']:.1f} stays on average.",
                    "Give this group priority on upgrades and early access to peak dates.",
                    "healthy", 2.5,
                ))

    promotion = context.bookings.groupby("promotion_used").agg(
        cancellation_rate=("is_cancelled", "mean"),
        bookings=("booking_id", "count"),
        average_rate=("nightly_rate", "mean"),
    )
    if len(promotion) == 2 and promotion["bookings"].min() >= 50:
        rate_gap = (1 - promotion.loc[1, "average_rate"] / promotion.loc[0, "average_rate"]) * 100
        cancel_gap = (promotion.loc[1, "cancellation_rate"] - promotion.loc[0, "cancellation_rate"]) * 100
        promo_share = promotion.loc[1, "bookings"] / len(context.bookings) * 100
        if rate_gap >= 4 or cancel_gap >= 3:
            recommendations.append(_recommendation(
                "Promotion Review",
                "Promotional rates cost more than the discount alone",
                f"Promotional bookings are taken at {rate_gap:.0f}% below the standard average rate "
                f"and are cancelled {format_percent(promotion.loc[1, 'cancellation_rate'] * 100)} of "
                f"the time against {format_percent(promotion.loc[0, 'cancellation_rate'] * 100)} for "
                f"standard bookings. They make up {promo_share:.0f}% of reservations in this period.",
                "Limit promotional rates to dates that genuinely need the volume, and attach firmer terms.",
                "watch", 2.7,
            ))

    if not context.monthly.empty:
        complete = context.monthly.loc[context.monthly["days"] >= 28]
        if len(complete) >= 3:
            quietest = complete.loc[complete["occupancy_rate"].idxmin()]
            if quietest["occupancy_rate"] <= hotel_occupancy - 7:
                recommendations.append(_recommendation(
                    "Demand Planning",
                    f"{quietest['month_label']} leaves the most rooms unsold",
                    f"{quietest['month_label']} ran at {format_percent(quietest['occupancy_rate'])} "
                    f"occupancy against {format_percent(hotel_occupancy)} across the period, earning "
                    f"{format_money(quietest['revenue'])}. This soft stretch is predictable and can be "
                    "planned for rather than reacted to.",
                    "Plan targeted offers and group business into this window well ahead of time.",
                    "watch", 2.8,
                ))

    channel_revenue = analytics.revenue_by_dimension(context.room_nights, "booking_channel")
    if not channel_revenue.empty:
        direct = channel_revenue.loc[channel_revenue["booking_channel"] == "Direct Website"]
        agency = channel_revenue.loc[
            channel_revenue["booking_channel"].isin(["Online Booking Platform", "Travel Agency"])
        ]
        if not direct.empty and not agency.empty:
            agency_share = agency["revenue"].sum() / channel_revenue["revenue"].sum() * 100
            agency_rate = agency["revenue"].sum() / agency["room_nights"].sum()
            if agency_share >= 30:
                recommendations.append(_recommendation(
                    "Channel Mix",
                    "Third-party sources hold a large share of revenue",
                    f"Online platforms and travel agencies together deliver {agency_share:.0f}% of room "
                    f"revenue at an average rate of {format_money(agency_rate, 0)} a night, against "
                    f"{format_money(direct['adr'].iat[0], 0)} for the direct website. Every point moved "
                    "to direct booking is worth more per room night.",
                    "Give direct bookers a visible reason to book on the hotel website.",
                    "watch", 2.6,
                ))

    if forecast_result and forecast_result.get("available"):
        forecast = forecast_result["forecast"]
        comparison = forecast_result["comparison"]
        peak = forecast.loc[forecast["occupancy_rate"].idxmax()]
        if peak["occupancy_rate"] >= 88:
            recommendations.append(_recommendation(
                "Demand Planning",
                "Rooms are expected to run tight in the coming days",
                f"Occupancy is expected to reach {format_percent(peak['occupancy_rate'])} on "
                f"{peak['weekday']} {pd.Timestamp(peak['stay_date']):%d %B}, with an expected "
                f"{format_money(forecast['revenue'].sum())} of room revenue over the next "
                f"{len(forecast)} nights.",
                "Protect availability on the busiest nights and confirm that staffing is in place.",
                "priority", 3.9,
            ))
        elif comparison["revenue_change"] is not None and comparison["revenue_change"] <= -5:
            recommendations.append(_recommendation(
                "Demand Planning",
                "The coming period looks quieter than the one just finished",
                f"Expected room revenue over the next {len(forecast)} nights is "
                f"{format_money(comparison['expected_revenue'])}, "
                f"{abs(comparison['revenue_change']):.0f}% below the period just completed, with "
                f"occupancy easing to {format_percent(comparison['expected_occupancy'])}.",
                "Open short-stay offers on the softest nights before the window closes.",
                "watch", 3.4,
            ))
        else:
            recommendations.append(_recommendation(
                "Demand Planning",
                "Demand ahead is steady",
                f"Occupancy over the next {len(forecast)} nights is expected to average "
                f"{format_percent(comparison['expected_occupancy'])}, close to the "
                f"{format_percent(comparison['recent_occupancy'])} just recorded, with "
                f"{format_money(comparison['expected_revenue'])} of expected room revenue.",
                "Hold current pricing and review again at the end of the week.",
                "healthy", 1.8,
            ))

    return sorted(recommendations, key=lambda item: item["priority"], reverse=True)[:7]


def priority_counts(recommendations: list[dict]) -> dict:
    counts = {"priority": 0, "watch": 0, "healthy": 0}
    for item in recommendations:
        counts[item["tone"]] = counts.get(item["tone"], 0) + 1
    return counts

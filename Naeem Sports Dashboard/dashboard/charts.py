from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from dashboard import business_logic as rules

CATEGORY_COLORS = {
    "Football": "#2563EB",
    "Cricket": "#F97316",
    "Badminton": "#10B981",
    "Tennis": "#8B5CF6",
    "Fitness": "#0EA5E9",
    "Accessories": "#64748B",
}

INK = "#0F172A"
MUTED = "#64748B"
GRID = "#EEF2F7"
ACCENT = "#F97316"
DEEP = "#1D4ED8"
SOFT_BAR = "#DBE4F5"
FORECAST_COLOR = "#F97316"

FONT_STACK = "Inter, Segoe UI, Helvetica Neue, Arial, sans-serif"


def category_color(category):
    return CATEGORY_COLORS.get(category, MUTED)


def _style(figure, height=340, legend=False):
    figure.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=28, b=8),
        font=dict(family=FONT_STACK, size=13, color=MUTED),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
        hoverlabel=dict(bgcolor="white", bordercolor="#E2E8F0", font_size=13),
        bargap=0.25,
    )
    figure.update_xaxes(showgrid=False, linecolor=GRID, ticks="outside", tickcolor=GRID)
    figure.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False, linecolor="rgba(0,0,0,0)")
    return figure


def sales_momentum_chart(daily_frame, previous_daily_average):
    figure = go.Figure()
    if daily_frame.empty:
        return _style(figure)

    smoothed = daily_frame["revenue"].rolling(7, min_periods=1).mean()

    figure.add_trace(
        go.Bar(
            x=daily_frame["period"],
            y=daily_frame["revenue"],
            marker_color=SOFT_BAR,
            name="Daily sales",
            hovertemplate="%{x|%d %b %Y}<br>Sales: Rs %{y:,.0f}<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=daily_frame["period"],
            y=smoothed,
            mode="lines",
            line=dict(color=DEEP, width=3.5, shape="spline"),
            name="Recent average",
            hovertemplate="%{x|%d %b %Y}<br>Weekly average: Rs %{y:,.0f}<extra></extra>",
        )
    )

    if previous_daily_average > 0:
        figure.add_hline(
            y=previous_daily_average,
            line=dict(color=ACCENT, width=2, dash="dot"),
            annotation_text="Previous period average",
            annotation_position="top left",
            annotation_font=dict(color=ACCENT, size=12),
        )

    figure.update_yaxes(tickprefix="Rs ")
    return _style(figure, height=360, legend=True)


def sales_trend_chart(frame, grain):
    figure = go.Figure()
    if frame.empty:
        return _style(figure)

    hover_format = {"Daily": "%d %b %Y", "Weekly": "Week of %d %b %Y", "Monthly": "%b %Y"}[grain]

    figure.add_trace(
        go.Scatter(
            x=frame["period"],
            y=frame["revenue"],
            mode="lines",
            fill="tozeroy",
            line=dict(color=DEEP, width=3, shape="spline"),
            fillcolor="rgba(37, 99, 235, 0.10)",
            hovertemplate=f"%{{x|{hover_format}}}<br>Sales: Rs %{{y:,.0f}}<extra></extra>",
        )
    )
    figure.update_yaxes(tickprefix="Rs ")
    return _style(figure, height=380)


def category_bar_chart(performance):
    figure = go.Figure()
    if performance.empty:
        return _style(figure)

    ordered = performance.sort_values("revenue")
    figure.add_trace(
        go.Bar(
            x=ordered["revenue"],
            y=ordered["category"],
            orientation="h",
            marker_color=[category_color(name) for name in ordered["category"]],
            text=[f"{share:.0f}%" for share in ordered["share"]],
            textposition="outside",
            textfont=dict(color=INK, size=13),
            customdata=ordered[["units", "share"]],
            hovertemplate=(
                "<b>%{y}</b><br>Sales: Rs %{x:,.0f}"
                "<br>Units: %{customdata[0]:,.0f}"
                "<br>Share: %{customdata[1]:.1f}%<extra></extra>"
            ),
        )
    )
    figure.update_xaxes(showgrid=True, gridcolor=GRID, title_text="", tickprefix="Rs ")
    figure.update_yaxes(showgrid=False, tickfont=dict(color=INK, size=14))
    figure.update_layout(bargap=0.35)
    return _style(figure, height=max(280, 58 * len(ordered)))


def weekday_chart(pattern):
    figure = go.Figure()
    if pattern.empty:
        return _style(figure)

    peak = pattern["average_revenue"].max()
    colors = [ACCENT if value == peak else SOFT_BAR for value in pattern["average_revenue"]]

    figure.add_trace(
        go.Bar(
            x=pattern["weekday"],
            y=pattern["average_revenue"],
            marker_color=colors,
            marker_line_width=0,
            hovertemplate="<b>%{x}</b><br>Average day: Rs %{y:,.0f}<extra></extra>",
        )
    )
    figure.update_layout(bargap=0.4)
    figure.update_xaxes(tickfont=dict(color=INK, size=13))
    figure.update_yaxes(tickprefix="Rs ")
    return _style(figure, height=320)


def seasonal_chart(seasonality):
    figure = go.Figure()
    if seasonality.empty:
        return _style(figure)

    for category, block in seasonality.groupby("category", observed=True):
        ordered = block.sort_values("month")
        figure.add_trace(
            go.Scatter(
                x=[str(month) for month in ordered["month"]],
                y=ordered["average_units"],
                mode="lines+markers",
                name=category,
                line=dict(color=category_color(category), width=3, shape="spline"),
                marker=dict(size=6),
                hovertemplate=(
                    f"<b>{category}</b><br>%{{x}}<br>"
                    "About %{y:.1f} units a day<extra></extra>"
                ),
            )
        )
    figure.update_yaxes(title_text="Units sold per day")
    return _style(figure, height=420, legend=True)


def stock_status_bar(counts):
    figure = go.Figure()
    total = sum(counts.values())
    if total == 0:
        return _style(figure, height=150)

    for status in rules.STATUS_PRIORITY:
        value = counts[status]
        if value == 0:
            continue
        figure.add_trace(
            go.Bar(
                x=[value],
                y=["Stock"],
                orientation="h",
                name=f"{rules.STATUS_BADGE[status]} {status}",
                marker_color=rules.STATUS_COLOR[status],
                text=[str(value)],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="white", size=15),
                hovertemplate=f"<b>{status}</b><br>%{{x}} products<extra></extra>",
            )
        )

    figure.update_layout(barmode="stack", bargap=0.1)
    figure.update_xaxes(visible=False)
    figure.update_yaxes(visible=False)
    return _style(figure, height=150, legend=True)


def history_and_forecast_chart(history, forecast):
    figure = go.Figure()
    if history.empty and forecast.empty:
        return _style(figure)

    figure.add_trace(
        go.Bar(
            x=history["date"],
            y=history["units"],
            name="Last 30 days",
            marker_color=SOFT_BAR,
            hovertemplate="%{x|%d %b}<br>Sold: %{y:.0f} units<extra></extra>",
        )
    )
    figure.add_trace(
        go.Bar(
            x=forecast["date"],
            y=forecast["expected_units"],
            name="Next 7 days",
            marker_color=FORECAST_COLOR,
            marker_pattern_shape="/",
            hovertemplate="%{x|%d %b}<br>Expected: %{y:.1f} units<extra></extra>",
        )
    )

    if not history.empty and not forecast.empty:
        boundary = (history["date"].max() + pd.Timedelta(hours=12)).to_pydatetime()
        figure.add_vline(x=boundary, line=dict(color=MUTED, width=1.5, dash="dot"))
        figure.add_annotation(
            x=boundary,
            y=1.0,
            yref="paper",
            yanchor="bottom",
            text="Today",
            showarrow=False,
            font=dict(color=MUTED, size=12),
        )

    figure.update_yaxes(title_text="Units")
    return _style(figure, height=380, legend=True)


def product_history_chart(history):
    figure = go.Figure()
    if history.empty:
        return _style(figure)

    smoothed = history["units"].rolling(14, min_periods=1).mean()

    figure.add_trace(
        go.Scatter(
            x=history["date"],
            y=history["units"],
            mode="lines",
            line=dict(color="#CBD5E1", width=1),
            name="Daily sales",
            hovertemplate="%{x|%d %b %Y}<br>Sold: %{y:.0f} units<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=history["date"],
            y=smoothed,
            mode="lines",
            line=dict(color=DEEP, width=3, shape="spline"),
            name="Two week average",
            hovertemplate="%{x|%d %b %Y}<br>Average: %{y:.1f} units<extra></extra>",
        )
    )
    figure.update_yaxes(title_text="Units")
    return _style(figure, height=340, legend=True)


def upcoming_demand_chart(demand_by_category):
    figure = go.Figure()
    if demand_by_category.empty:
        return _style(figure)

    ordered = demand_by_category.sort_values("expected_units")
    figure.add_trace(
        go.Bar(
            x=ordered["expected_units"],
            y=ordered["category"],
            orientation="h",
            marker_color=[category_color(name) for name in ordered["category"]],
            text=[f"{value:,.0f}" for value in ordered["expected_units"]],
            textposition="outside",
            textfont=dict(color=INK, size=13),
            hovertemplate="<b>%{y}</b><br>Expected: %{x:,.0f} units<extra></extra>",
        )
    )
    figure.update_xaxes(showgrid=True, gridcolor=GRID)
    figure.update_yaxes(showgrid=False, tickfont=dict(color=INK, size=14))
    figure.update_layout(bargap=0.35)
    return _style(figure, height=max(260, 52 * len(ordered)))


def momentum_comparison_chart(momentum_frame):
    figure = go.Figure()
    if momentum_frame.empty:
        return _style(figure)

    ordered = momentum_frame.sort_values("change_pct")
    figure.add_trace(
        go.Bar(
            x=ordered["previous"],
            y=ordered["product_name"],
            orientation="h",
            name="Earlier weeks",
            marker_color=SOFT_BAR,
            hovertemplate="<b>%{y}</b><br>Earlier: %{x:,.0f} units<extra></extra>",
        )
    )
    figure.add_trace(
        go.Bar(
            x=ordered["recent"],
            y=ordered["product_name"],
            orientation="h",
            name="Recent weeks",
            marker_color=ACCENT,
            hovertemplate="<b>%{y}</b><br>Recent: %{x:,.0f} units<extra></extra>",
        )
    )
    figure.update_layout(barmode="group", bargap=0.3)
    figure.update_yaxes(showgrid=False, tickfont=dict(color=INK, size=13))
    figure.update_xaxes(showgrid=True, gridcolor=GRID, title_text="Units sold")
    return _style(figure, height=max(300, 62 * len(ordered)), legend=True)

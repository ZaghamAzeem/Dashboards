from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.utils import CHART_COLORS, PALETTE, style_chart

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def revenue_trend(daily: pd.DataFrame, height: int = 320) -> go.Figure:
    smoothing = 7 if len(daily) >= 21 else 1
    smoothed = daily["revenue"].rolling(smoothing, min_periods=1).mean()
    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=daily["stay_date"], y=daily["revenue"], mode="lines", name="Daily revenue",
        line=dict(color=PALETTE["sand"], width=1),
        hovertemplate="%{x|%d %b %Y}<br>Revenue $%{y:,.0f}<extra></extra>",
    ))
    figure.add_trace(go.Scatter(
        x=daily["stay_date"], y=smoothed, mode="lines", name="Underlying trend",
        line=dict(color=PALETTE["ink"], width=2.6),
        fill="tozeroy", fillcolor="rgba(16,36,58,0.06)",
        hovertemplate="%{x|%d %b %Y}<br>Trend $%{y:,.0f}<extra></extra>",
    ))
    figure.update_yaxes(title="Room revenue per night", tickprefix="$", separatethousands=True)
    return style_chart(figure, height=height, show_legend=True, margin_top=40)


def demand_trend(daily: pd.DataFrame, height: int = 320) -> go.Figure:
    smoothing = 7 if len(daily) >= 21 else 1
    smoothed = daily["occupancy_rate"].rolling(smoothing, min_periods=1).mean()
    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=daily["stay_date"], y=daily["occupancy_rate"], mode="lines", name="Nightly occupancy",
        line=dict(color="rgba(108,127,146,0.45)", width=1),
        hovertemplate="%{x|%d %b %Y}<br>%{y:.0f}% full<extra></extra>",
    ))
    figure.add_trace(go.Scatter(
        x=daily["stay_date"], y=smoothed, mode="lines", name="Underlying trend",
        line=dict(color=PALETTE["positive"], width=2.6),
        hovertemplate="%{x|%d %b %Y}<br>%{y:.0f}% full<extra></extra>",
    ))
    figure.update_yaxes(title="Rooms occupied", ticksuffix="%", range=[0, 105])
    return style_chart(figure, height=height, show_legend=True, margin_top=40)


def horizontal_bar(frame: pd.DataFrame, category: str, value: str, value_prefix: str = "$",
                   value_suffix: str = "", height: int = 300, colour: str | None = None,
                   axis_title: str = "") -> go.Figure:
    ordered = frame.sort_values(value)
    labels = [f"{value_prefix}{item:,.0f}{value_suffix}" for item in ordered[value]]
    figure = go.Figure(go.Bar(
        x=ordered[value], y=ordered[category], orientation="h",
        marker=dict(color=colour or PALETTE["ink"], line=dict(width=0)),
        text=labels, textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>" + value_prefix + "%{x:,.0f}" + value_suffix + "<extra></extra>",
    ))
    figure.update_xaxes(title=axis_title, showticklabels=False,
                        range=[0, ordered[value].max() * 1.22 if len(ordered) else 1])
    figure.update_yaxes(title="")
    return style_chart(figure, height=height)


def category_donut(labels, values, height: int = 300) -> go.Figure:
    figure = go.Figure(go.Pie(
        labels=list(labels), values=list(values), hole=0.62, sort=True,
        marker=dict(colors=CHART_COLORS, line=dict(color="#FFFFFF", width=2)),
        textinfo="label+percent", textposition="outside",
        hovertemplate="%{label}<br>%{percent} of revenue<extra></extra>",
    ))
    return style_chart(figure, height=height)


def monthly_revenue(monthly: pd.DataFrame, height: int = 330) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(go.Bar(
        x=monthly["month_label"], y=monthly["revenue"], name="Room revenue",
        marker=dict(color=PALETTE["ink"]),
        hovertemplate="%{x}<br>Revenue $%{y:,.0f}<extra></extra>",
    ))
    figure.add_trace(go.Scatter(
        x=monthly["month_label"], y=monthly["occupancy_rate"], name="Occupancy",
        yaxis="y2", mode="lines+markers",
        line=dict(color=PALETTE["brass"], width=2.4), marker=dict(size=6),
        hovertemplate="%{x}<br>%{y:.0f}% full<extra></extra>",
    ))
    figure.update_layout(
        yaxis=dict(title="Room revenue", tickprefix="$", separatethousands=True),
        yaxis2=dict(title="Occupancy", overlaying="y", side="right", ticksuffix="%",
                    range=[0, 105], showgrid=False),
    )
    return style_chart(figure, height=height, show_legend=True, margin_top=40)


def weekday_pattern(weekday: pd.DataFrame, value: str = "revenue", height: int = 300,
                    prefix: str = "$", suffix: str = "") -> go.Figure:
    frame = weekday.dropna(subset=[value])
    peak = frame[value].max() if len(frame) else 0
    colours = [PALETTE["brass"] if item >= peak * 0.97 else PALETTE["ink"] for item in frame[value]]
    figure = go.Figure(go.Bar(
        x=frame["weekday"], y=frame[value], marker=dict(color=colours),
        text=[f"{prefix}{item:,.0f}{suffix}" for item in frame[value]],
        textposition="outside", cliponaxis=False,
        hovertemplate="%{x}<br>" + prefix + "%{y:,.0f}" + suffix + "<extra></extra>",
    ))
    figure.update_yaxes(title="", showticklabels=False, range=[0, peak * 1.2 if peak else 1])
    return style_chart(figure, height=height)


def seasonal_pattern(daily: pd.DataFrame, height: int = 330) -> go.Figure:
    frame = daily.copy()
    frame["month_name"] = frame["stay_date"].dt.strftime("%b")
    frame["weekday"] = frame["stay_date"].dt.day_name()
    pivot = frame.pivot_table(
        index="weekday", columns="month_name", values="occupancy_rate", aggfunc="mean"
    )
    pivot = pivot.reindex(index=[d for d in WEEKDAY_ORDER if d in pivot.index])
    pivot = pivot.reindex(columns=[m for m in MONTH_ORDER if m in pivot.columns])
    figure = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index,
        colorscale=[[0, "#F3EFE6"], [0.5, "#C9B896"], [1, PALETTE["ink"]]],
        hovertemplate="%{y} in %{x}<br>%{z:.0f}% full<extra></extra>",
        colorbar=dict(title="Full", ticksuffix="%", thickness=12, len=0.8, outlinewidth=0),
    ))
    figure.update_yaxes(title="")
    figure.update_xaxes(title="")
    return style_chart(figure, height=height)


def grouped_comparison(frame: pd.DataFrame, category: str, series: dict,
                       height: int = 320, prefix: str = "", suffix: str = "") -> go.Figure:
    figure = go.Figure()
    for index, (name, column) in enumerate(series.items()):
        figure.add_trace(go.Bar(
            x=frame[category], y=frame[column], name=name,
            marker=dict(color=CHART_COLORS[index % len(CHART_COLORS)]),
            hovertemplate="%{x}<br>" + name + ": " + prefix + "%{y:,.1f}" + suffix + "<extra></extra>",
        ))
    figure.update_layout(barmode="group")
    figure.update_yaxes(title="")
    return style_chart(figure, height=height, show_legend=True, margin_top=40)


def booking_volume(volume: pd.DataFrame, height: int = 330, date_format: str = "%d %b %Y") -> go.Figure:
    figure = go.Figure()
    dense = len(volume) > 90
    if dense:
        figure.add_trace(go.Scatter(
            x=volume["period"], y=volume["bookings"], mode="lines", name="Confirmed bookings",
            line=dict(color=PALETTE["ink"], width=1.6),
            fill="tozeroy", fillcolor="rgba(16,36,58,0.08)",
            hovertemplate="%{x|" + date_format + "}<br>%{y:,.0f} confirmed<extra></extra>",
        ))
        figure.add_trace(go.Scatter(
            x=volume["period"], y=volume["cancellations"], mode="lines", name="Cancelled bookings",
            line=dict(color=PALETTE["brass"], width=1.4),
            hovertemplate="%{x|" + date_format + "}<br>%{y:,.0f} cancelled<extra></extra>",
        ))
    else:
        figure.add_trace(go.Bar(
            x=volume["period"], y=volume["bookings"], name="Confirmed bookings",
            marker=dict(color=PALETTE["ink"]),
            hovertemplate="%{x|" + date_format + "}<br>%{y:,.0f} confirmed<extra></extra>",
        ))
        figure.add_trace(go.Bar(
            x=volume["period"], y=volume["cancellations"], name="Cancelled bookings",
            marker=dict(color=PALETTE["sand"]),
            hovertemplate="%{x|" + date_format + "}<br>%{y:,.0f} cancelled<extra></extra>",
        ))
        figure.update_layout(barmode="group")
    figure.update_yaxes(title="Bookings")
    figure.update_xaxes(tickformat=date_format)
    return style_chart(figure, height=height, show_legend=True, margin_top=40)


def lead_time_profile(lead: pd.DataFrame, height: int = 300) -> go.Figure:
    frame = lead.copy()
    frame["label"] = frame["lead_time_group"].astype(str)
    figure = go.Figure(go.Bar(
        x=frame["label"], y=frame["share"], marker=dict(color=PALETTE["slate"]),
        text=[f"{item:.0f}%" for item in frame["share"]],
        textposition="outside", cliponaxis=False,
        hovertemplate="%{x}<br>%{y:.0f}% of bookings<extra></extra>",
    ))
    figure.update_yaxes(title="", showticklabels=False,
                        range=[0, frame["share"].max() * 1.25 if len(frame) else 1])
    return style_chart(figure, height=height)


def cancellation_bars(frame: pd.DataFrame, category: str, height: int = 300) -> go.Figure:
    ordered = frame.sort_values("cancellation_rate")
    peak = ordered["cancellation_rate"].max() if len(ordered) else 0
    colours = [
        PALETTE["attention"] if item >= peak * 0.9 else
        PALETTE["warning"] if item >= peak * 0.65 else PALETTE["slate"]
        for item in ordered["cancellation_rate"]
    ]
    figure = go.Figure(go.Bar(
        x=ordered["cancellation_rate"], y=ordered[category].astype(str), orientation="h",
        marker=dict(color=colours),
        text=[f"{item:.1f}%" for item in ordered["cancellation_rate"]],
        textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>%{x:.1f}% cancelled<extra></extra>",
    ))
    figure.update_xaxes(title="", showticklabels=False, range=[0, peak * 1.25 if peak else 1])
    figure.update_yaxes(title="")
    return style_chart(figure, height=height)


def forecast_view(history: pd.DataFrame, forecast: pd.DataFrame, capacity: int,
                  height: int = 400) -> go.Figure:
    recent = history.tail(45)
    bridge_date = recent["stay_date"].iloc[-1] if len(recent) else forecast["stay_date"].iloc[0]
    bridge_value = recent["occupancy_rate"].iloc[-1] if len(recent) else forecast["occupancy_rate"].iloc[0]

    forecast_x = [bridge_date] + list(forecast["stay_date"])
    forecast_y = [bridge_value] + list(forecast["occupancy_rate"])

    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=recent["stay_date"], y=recent["occupancy_rate"], mode="lines",
        name="Rooms occupied so far", line=dict(color=PALETTE["ink"], width=2.6),
        fill="tozeroy", fillcolor="rgba(16,36,58,0.07)",
        hovertemplate="%{x|%d %b}<br>%{y:.0f}% full<extra></extra>",
    ))
    figure.add_trace(go.Scatter(
        x=forecast_x, y=forecast_y, mode="lines+markers", name="Expected occupancy",
        line=dict(color=PALETTE["brass"], width=2.8, dash="dot"),
        marker=dict(size=7, color=PALETTE["brass"]),
        hovertemplate="%{x|%d %b}<br>Expected %{y:.0f}% full<extra></extra>",
    ))
    figure.add_vline(x=bridge_date, line_width=1, line_dash="dash", line_color=PALETTE["muted"])
    figure.add_annotation(x=bridge_date, y=104, text="Today", showarrow=False,
                          font=dict(size=11, color=PALETTE["muted"]), xanchor="left", xshift=6)
    figure.update_yaxes(title="Rooms occupied", ticksuffix="%", range=[0, 110])
    return style_chart(figure, height=height, show_legend=True, margin_top=40)


def forecast_revenue_bars(forecast: pd.DataFrame, height: int = 300) -> go.Figure:
    colours = {
        "High": PALETTE["ink"],
        "Moderate": PALETTE["slate"],
        "Low": PALETTE["sand"],
    }
    figure = go.Figure(go.Bar(
        x=forecast["stay_date"], y=forecast["revenue"],
        marker=dict(color=[colours.get(level, PALETTE["slate"]) for level in forecast["demand_level"]]),
        customdata=forecast[["weekday", "demand_level", "occupancy_rate"]],
        hovertemplate="%{customdata[0]} %{x|%d %b}<br>Expected revenue $%{y:,.0f}"
                      "<br>%{customdata[2]:.0f}% full &middot; %{customdata[1]} demand<extra></extra>",
    ))
    figure.update_yaxes(title="Expected room revenue", tickprefix="$", separatethousands=True)
    figure.update_xaxes(tickformat="%d %b")
    return style_chart(figure, height=height)


def segment_bars(summary: pd.DataFrame, height: int = 320) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(go.Bar(
        x=summary["segment"].astype(str), y=summary["guest_share"], name="Share of guests",
        marker=dict(color=PALETTE["slate"]),
        hovertemplate="%{x}<br>%{y:.0f}% of guests<extra></extra>",
    ))
    figure.add_trace(go.Bar(
        x=summary["segment"].astype(str), y=summary["revenue_share"], name="Share of spending",
        marker=dict(color=PALETTE["brass"]),
        hovertemplate="%{x}<br>%{y:.0f}% of spending<extra></extra>",
    ))
    figure.update_layout(barmode="group")
    figure.update_yaxes(title="", ticksuffix="%")
    return style_chart(figure, height=height, show_legend=True, margin_top=40)

import pandas as pd
import plotly.graph_objects as go

from dashboard import business_logic

INK = "#16202B"
MUTED_INK = "#6B7A8C"
GRID = "#E6ECF2"
SURFACE = "rgba(0,0,0,0)"

DEEP_TEAL = "#0F4C5C"
TEAL = "#2A9D8F"
SLATE_BLUE = "#4C6EA5"
SAND = "#C9A227"

CATEGORY_COLOURS = {
    "Surgical Instruments": DEEP_TEAL,
    "Medical Supplies": TEAL,
}

STATUS_COLOURS = {
    business_logic.HEALTHY: "#2E9E71",
    business_logic.ATTENTION: "#E0A94A",
    business_logic.CRITICAL: "#D1495B",
    business_logic.OUT_OF_STOCK: "#8D99AE",
}

FONT_FAMILY = "Segoe UI, Inter, Helvetica Neue, sans-serif"


def base_layout(figure, height=340, show_legend=False):
    figure.update_layout(
        height=height,
        margin=dict(l=10, r=16, t=48, b=10),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family=FONT_FAMILY, size=13, color=INK),
        title=dict(
            text=figure.layout.title.text or "",
            font=dict(size=17, color=INK),
            x=0.0,
            xanchor="left",
            y=0.94,
        ),
        showlegend=show_legend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=12, color=MUTED_INK),
        ),
        hoverlabel=dict(font=dict(family=FONT_FAMILY, size=12), bgcolor="white"),
    )
    figure.update_xaxes(
        showgrid=False,
        linecolor=GRID,
        ticks="outside",
        tickcolor=GRID,
        tickfont=dict(color=MUTED_INK),
    )
    figure.update_yaxes(
        showgrid=True,
        gridcolor=GRID,
        zeroline=False,
        linecolor=SURFACE,
        tickfont=dict(color=MUTED_INK),
    )
    return figure


def category_colour(category):
    return CATEGORY_COLOURS.get(category, SLATE_BLUE)


def inventory_health_donut(status_summary):
    summary = status_summary[status_summary["products"] > 0]
    figure = go.Figure(
        go.Pie(
            labels=summary["status"],
            values=summary["products"],
            hole=0.62,
            sort=False,
            direction="clockwise",
            marker=dict(
                colors=[STATUS_COLOURS[status] for status in summary["status"]],
                line=dict(color="white", width=3),
            ),
            textinfo="label+value",
            textfont=dict(size=13),
            hovertemplate="%{label}: %{value} products (%{percent})<extra></extra>",
        )
    )
    total_products = int(status_summary["products"].sum())
    figure.add_annotation(
        text=f"<b>{total_products}</b><br><span style='font-size:12px'>products</span>",
        showarrow=False,
        font=dict(size=26, color=INK, family=FONT_FAMILY),
    )
    base_layout(figure, height=330)
    figure.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    return figure


def sales_trend_line(trend_frame, granularity):
    date_label = {
        "Daily": "%{x|%d %b %Y}",
        "Weekly": "Week ending %{x|%d %b %Y}",
        "Monthly": "%{x|%B %Y}",
    }.get(granularity, "%{x|%d %b %Y}")
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=trend_frame["period"],
            y=trend_frame["units_sold"],
            mode="lines",
            line=dict(color=DEEP_TEAL, width=2.4, shape="spline", smoothing=0.5),
            fill="tozeroy",
            fillcolor="rgba(15, 76, 92, 0.10)",
            hovertemplate=f"{date_label}<br>%{{y:,.0f}} units<extra></extra>",
            name="Units sold",
        )
    )
    figure.update_layout(title=f"{granularity} Sales")
    figure.update_yaxes(title_text="Units sold")
    return base_layout(figure, height=340)


def category_bar(category_frame):
    figure = go.Figure(
        go.Bar(
            x=category_frame["category"],
            y=category_frame["units_sold"],
            marker=dict(
                color=[category_colour(name) for name in category_frame["category"]],
                line=dict(width=0),
            ),
            text=[f"{value:,.0f}" for value in category_frame["units_sold"]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{x}<br>%{y:,.0f} units<extra></extra>",
            width=0.45,
        )
    )
    figure.update_layout(title="Sales by Category")
    figure.update_yaxes(
        title_text="Units sold", range=[0, category_frame["units_sold"].max() * 1.18]
    )
    return base_layout(figure, height=330)


def top_products_bar(product_frame, title="Best-Selling Products"):
    ordered = product_frame.sort_values("units_sold")
    figure = go.Figure(
        go.Bar(
            x=ordered["units_sold"],
            y=ordered["product_name"],
            orientation="h",
            marker=dict(
                color=[category_colour(name) for name in ordered["category"]],
                line=dict(width=0),
            ),
            customdata=ordered[["category", "unit_of_measure"]],
            text=[f"{value:,.0f}" for value in ordered["units_sold"]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>%{customdata[0]}<br>%{x:,.0f} %{customdata[1]}<extra></extra>",
        )
    )
    figure.update_layout(title=title)
    figure.update_xaxes(
        title_text="Units sold",
        showgrid=True,
        gridcolor=GRID,
        range=[0, ordered["units_sold"].max() * 1.16],
    )
    figure.update_yaxes(showgrid=False)
    height = max(280, 62 * len(ordered))
    return base_layout(figure, height=height)


def slow_moving_bar(product_frame):
    return top_products_bar(product_frame, title="Slow-Moving Products")


def weekday_pattern_bar(pattern_frame):
    values = pattern_frame["average_units"]
    peak = values.max() if len(values) else 0
    colours = [DEEP_TEAL if value == peak else "#9FC3C6" for value in values]
    figure = go.Figure(
        go.Bar(
            x=pattern_frame["weekday"].astype(str),
            y=values,
            marker=dict(color=colours, line=dict(width=0)),
            hovertemplate="%{x}<br>%{y:,.0f} units on an average day<extra></extra>",
            width=0.6,
        )
    )
    figure.update_layout(title="When Do Customers Usually Buy?")
    figure.update_yaxes(title_text="Average units per day")
    return base_layout(figure, height=330)


def demand_forecast_line(history_frame, forecast_frame, product_name, unit_of_measure):
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=history_frame["sale_date"],
            y=history_frame["units_sold"],
            mode="lines",
            name="Sales so far",
            line=dict(color=DEEP_TEAL, width=2.2),
            hovertemplate=f"%{{x|%d %b %Y}}<br>%{{y:,.0f}} {unit_of_measure}<extra></extra>",
        )
    )
    if not history_frame.empty and not forecast_frame.empty:
        bridge = pd.DataFrame(
            {
                "forecast_date": [history_frame["sale_date"].iloc[-1]],
                "expected_units": [history_frame["units_sold"].iloc[-1]],
            }
        )
        forecast_line = pd.concat([bridge, forecast_frame], ignore_index=True)
    else:
        forecast_line = forecast_frame
    figure.add_trace(
        go.Scatter(
            x=forecast_line["forecast_date"],
            y=forecast_line["expected_units"],
            mode="lines+markers",
            name="Expected demand",
            line=dict(color=SAND, width=2.6, dash="dot"),
            marker=dict(size=7, color=SAND),
            hovertemplate=(
                f"%{{x|%a %d %b}}<br>Expected %{{y:,.0f}} {unit_of_measure}<extra></extra>"
            ),
        )
    )
    if not history_frame.empty:
        boundary = history_frame["sale_date"].iloc[-1]
        figure.add_shape(
            type="line",
            x0=boundary,
            x1=boundary,
            yref="paper",
            y0=0,
            y1=1,
            line=dict(color=MUTED_INK, width=1, dash="dash"),
        )
        figure.add_annotation(
            x=boundary,
            yref="paper",
            y=1.02,
            text="Today",
            showarrow=False,
            font=dict(size=11, color=MUTED_INK),
            xanchor="left",
        )
    figure.update_layout(title=f"{product_name} — Sales History and Expected Demand")
    figure.update_yaxes(title_text=f"Units ({unit_of_measure})")
    return base_layout(figure, height=380, show_legend=True)


def expected_demand_bar(forecast_frame, unit_of_measure):
    labels = [
        f"{row.day_name[:3]} {row.forecast_date.strftime('%d %b')}"
        for row in forecast_frame.itertuples()
    ]
    figure = go.Figure(
        go.Bar(
            x=labels,
            y=forecast_frame["expected_units"],
            marker=dict(color=TEAL, line=dict(width=0)),
            text=[f"{value:,.0f}" for value in forecast_frame["expected_units"]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate=f"%{{x}}<br>%{{y:,.0f}} {unit_of_measure} expected<extra></extra>",
            width=0.6,
        )
    )
    figure.update_layout(title="Expected Demand, Next 7 Days")
    figure.update_yaxes(
        title_text=f"Expected units ({unit_of_measure})",
        range=[0, max(1.0, forecast_frame["expected_units"].max() * 1.18)],
    )
    return base_layout(figure, height=320)


def stock_versus_demand_bar(status_frame):
    ordered = status_frame.sort_values("coverage", ascending=False)
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=ordered["current_stock"],
            y=ordered["product_name"],
            orientation="h",
            name="Current stock",
            marker=dict(color=DEEP_TEAL, line=dict(width=0)),
            hovertemplate="%{y}<br>%{x:,.0f} in stock<extra></extra>",
        )
    )
    figure.add_trace(
        go.Bar(
            x=ordered["expected_demand"],
            y=ordered["product_name"],
            orientation="h",
            name="Expected demand (7 days)",
            marker=dict(color=SAND, line=dict(width=0)),
            hovertemplate="%{y}<br>%{x:,.0f} expected<extra></extra>",
        )
    )
    figure.update_layout(barmode="group", bargap=0.35)
    figure.update_xaxes(title_text="Units", showgrid=True, gridcolor=GRID)
    figure.update_yaxes(showgrid=False)
    height = max(300, 74 * len(ordered))
    return base_layout(figure, height=height, show_legend=True)


def stock_level_line(history_frame, product_name, unit_of_measure):
    figure = go.Figure(
        go.Scatter(
            x=history_frame["sale_date"],
            y=history_frame["stock_on_hand"],
            mode="lines",
            line=dict(color=SLATE_BLUE, width=2.2, shape="hv"),
            fill="tozeroy",
            fillcolor="rgba(76, 110, 165, 0.10)",
            hovertemplate=(
                f"%{{x|%d %b %Y}}<br>%{{y:,.0f}} {unit_of_measure} in stock<extra></extra>"
            ),
        )
    )
    figure.update_layout(title=f"{product_name} — Stock Level Over Time")
    figure.update_yaxes(title_text=f"Units in stock ({unit_of_measure})")
    return base_layout(figure, height=320)

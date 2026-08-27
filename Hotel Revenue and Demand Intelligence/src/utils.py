from __future__ import annotations

import math

import plotly.graph_objects as go

HOTEL_NAME = "Grand Horizon Hotel"
HOTEL_TAGLINE = "Revenue & Demand Intelligence"

PALETTE = {
    "ink": "#10243A",
    "body": "#42566B",
    "muted": "#8494A4",
    "background": "#F6F4EF",
    "surface": "#FFFFFF",
    "border": "#E4DED2",
    "brass": "#B08A47",
    "brass_soft": "#EFE4CE",
    "positive": "#2E7D64",
    "positive_soft": "#E1F0E9",
    "warning": "#C8871F",
    "warning_soft": "#FBEEDA",
    "attention": "#B4433A",
    "attention_soft": "#F9E4E1",
    "slate": "#6C7F92",
    "sand": "#C9B896",
}

CHART_COLORS = [
    PALETTE["ink"],
    PALETTE["brass"],
    PALETTE["positive"],
    PALETTE["slate"],
    PALETTE["sand"],
    PALETTE["warning"],
]

STATUS_STYLES = {
    "healthy": (PALETTE["positive"], PALETTE["positive_soft"], "Healthy"),
    "watch": (PALETTE["warning"], PALETTE["warning_soft"], "Watch"),
    "priority": (PALETTE["attention"], PALETTE["attention_soft"], "High Priority"),
    "neutral": (PALETTE["slate"], "#EEF1F4", "Neutral"),
}


def format_currency(value, decimals: int = 0) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "--"
    value = float(value)
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.2f}M"
    return f"${value:,.{decimals}f}"


def format_money(value, decimals: int = 0) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "--"
    return f"${float(value):,.{decimals}f}"


def format_number(value, decimals: int = 0) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "--"
    return f"{float(value):,.{decimals}f}"


def format_percent(value, decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "--"
    return f"{float(value):.{decimals}f}%"


def format_change(value, decimals: int = 1, lower_is_better: bool = False) -> tuple[str, str]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "No comparison available", PALETTE["muted"]
    if abs(value) < 0.05:
        return "In line with previous period", PALETTE["muted"]
    arrow = "\u2191" if value > 0 else "\u2193"
    improving = value < 0 if lower_is_better else value > 0
    colour = PALETTE["positive"] if improving else PALETTE["attention"]
    return f"{arrow} {abs(value):.{decimals}f}% vs previous period", colour


def style_chart(fig: go.Figure, height: int = 340, show_legend: bool = False,
                margin_top: int = 20) -> go.Figure:
    fig.update_layout(
        height=height,
        showlegend=show_legend,
        plot_bgcolor=PALETTE["surface"],
        paper_bgcolor=PALETTE["surface"],
        font=dict(family="Inter, Segoe UI, Helvetica, sans-serif", size=13, color=PALETTE["body"]),
        margin=dict(l=10, r=16, t=margin_top, b=10),
        hoverlabel=dict(bgcolor=PALETTE["ink"], font_size=12, font_color="white",
                        bordercolor=PALETTE["ink"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=12)),
        colorway=CHART_COLORS,
    )
    fig.update_xaxes(showgrid=False, linecolor=PALETTE["border"], ticks="outside",
                     tickcolor=PALETTE["border"], title_font=dict(size=12),
                     tickfont=dict(size=12, color=PALETTE["muted"]))
    fig.update_yaxes(showgrid=True, gridcolor="#EFEBE2", zeroline=False, linecolor="rgba(0,0,0,0)",
                     title_font=dict(size=12), tickfont=dict(size=12, color=PALETTE["muted"]))
    return fig

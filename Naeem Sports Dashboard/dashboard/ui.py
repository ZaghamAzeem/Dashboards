from __future__ import annotations

from html import escape

from dashboard import business_logic as rules
from dashboard.charts import category_color

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

TONE_COLORS = {
    "sales": "#2563EB",
    "favourite": "#F97316",
    "alert": "#EF4444",
    "forecast": "#8B5CF6",
    "neutral": "#64748B",
}

STYLES = """
<style>
:root {
    --ink: #0F172A;
    --muted: #64748B;
    --line: #E7EDF6;
    --surface: #FFFFFF;
    --canvas: #F5F7FB;
}

.stApp { background: var(--canvas); }

[data-testid="stHeader"] { background: transparent; }

.block-container {
    padding-top: 2.2rem;
    padding-bottom: 3.5rem;
    max-width: 1280px;
}

html, body, [class*="css"] {
    font-family: Inter, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

#MainMenu, footer { visibility: hidden; }

.shop-hero {
    position: relative;
    overflow: hidden;
    border-radius: 22px;
    padding: 34px 38px 30px 38px;
    background: linear-gradient(120deg, #0B1B3A 0%, #14306B 55%, #1D4ED8 100%);
    color: #FFFFFF;
    box-shadow: 0 18px 40px -24px rgba(15, 23, 42, 0.65);
    margin-bottom: 26px;
}

.shop-hero::after {
    content: "";
    position: absolute;
    right: -70px;
    top: -90px;
    width: 260px;
    height: 260px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(249, 115, 22, 0.45) 0%, rgba(249, 115, 22, 0) 68%);
}

.shop-hero .hero-eyebrow {
    display: inline-block;
    font-size: 0.74rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    font-weight: 700;
    color: #FDBA74;
    margin-bottom: 10px;
}

.shop-hero h1 {
    font-size: 2.35rem;
    font-weight: 800;
    line-height: 1.1;
    margin: 0 0 8px 0;
    color: #FFFFFF;
}

.shop-hero p {
    font-size: 1.02rem;
    color: #C7D6F2;
    margin: 0;
    max-width: 640px;
}

.hero-chips { margin-top: 20px; display: flex; flex-wrap: wrap; gap: 10px; }

.hero-chip {
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 999px;
    padding: 7px 15px;
    font-size: 0.86rem;
    font-weight: 500;
    color: #EAF1FF;
}

.section-head { margin: 34px 0 14px 0; }

.section-head h2 {
    font-size: 1.32rem;
    font-weight: 750;
    color: var(--ink);
    margin: 0 0 3px 0;
    letter-spacing: -0.01em;
}

.section-head p { font-size: 0.92rem; color: var(--muted); margin: 0; }

.snap-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 20px 20px 18px 20px;
    height: 100%;
    box-shadow: 0 2px 4px rgba(15, 23, 42, 0.03);
    border-top: 4px solid var(--accent, #2563EB);
}

.snap-card .snap-icon { font-size: 1.5rem; line-height: 1; }

.snap-card .snap-label {
    display: block;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 700;
    color: var(--muted);
    margin: 12px 0 6px 0;
}

.snap-card .snap-value {
    font-size: 1.72rem;
    font-weight: 800;
    color: var(--ink);
    line-height: 1.15;
    letter-spacing: -0.02em;
}

.snap-card .snap-caption {
    display: block;
    font-size: 0.86rem;
    color: var(--muted);
    margin-top: 7px;
    line-height: 1.4;
}

.story-panel {
    background: linear-gradient(135deg, #FFF7ED 0%, #FFFFFF 60%);
    border: 1px solid #FDE4CB;
    border-radius: 18px;
    padding: 24px 28px;
}

.story-panel .story-line {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 11px 0;
    border-bottom: 1px dashed #F3DCC4;
    font-size: 1.02rem;
    color: #1F2937;
    line-height: 1.5;
}

.story-panel .story-line:last-child { border-bottom: none; }
.story-panel .story-bullet { color: #F97316; font-weight: 800; }

.momentum-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    flex-wrap: wrap;
    background: var(--surface);
    border: 1px solid var(--line);
    border-left: 5px solid var(--accent, #2563EB);
    border-radius: 16px;
    padding: 18px 24px;
    margin-bottom: 14px;
}

.momentum-banner .momentum-title {
    font-size: 1.22rem;
    font-weight: 750;
    color: var(--ink);
}

.momentum-banner .momentum-detail { font-size: 0.92rem; color: var(--muted); margin-top: 3px; }

.momentum-banner .momentum-value {
    font-size: 1.5rem;
    font-weight: 800;
    color: var(--accent, #2563EB);
    white-space: nowrap;
}

.rank-card {
    display: flex;
    align-items: center;
    gap: 16px;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 15px;
    padding: 14px 18px;
    margin-bottom: 10px;
}

.rank-card .rank-badge {
    font-size: 1.35rem;
    min-width: 38px;
    text-align: center;
    font-weight: 800;
    color: var(--muted);
}

.rank-card .rank-body { flex: 1; min-width: 0; }

.rank-card .rank-name {
    font-size: 1.02rem;
    font-weight: 700;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.rank-card .rank-figure { text-align: right; white-space: nowrap; }
.rank-card .rank-units { font-size: 1.05rem; font-weight: 800; color: var(--ink); }
.rank-card .rank-money { font-size: 0.82rem; color: var(--muted); }

.podium-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 20px;
    padding: 24px 22px;
    text-align: center;
    border-top: 5px solid var(--accent, #F97316);
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
    height: 100%;
}

.podium-card .podium-medal { font-size: 2.4rem; }
.podium-card .podium-name {
    font-size: 1.14rem;
    font-weight: 750;
    color: var(--ink);
    margin: 10px 0 4px 0;
    line-height: 1.3;
}
.podium-card .podium-units { font-size: 1.6rem; font-weight: 800; color: var(--ink); }
.podium-card .podium-caption { font-size: 0.85rem; color: var(--muted); }

.sport-chip {
    display: inline-block;
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    padding: 3px 10px;
    border-radius: 999px;
    margin-top: 4px;
}

.status-chip {
    display: inline-block;
    font-size: 0.8rem;
    font-weight: 700;
    padding: 4px 12px;
    border-radius: 999px;
    white-space: nowrap;
}

.alert-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-left: 5px solid var(--accent, #EF4444);
    border-radius: 15px;
    padding: 15px 18px;
    margin-bottom: 10px;
}

.alert-card .alert-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}

.alert-card .alert-name { font-size: 1.02rem; font-weight: 700; color: var(--ink); }

.alert-card .alert-numbers {
    display: flex;
    gap: 26px;
    margin-top: 12px;
    flex-wrap: wrap;
}

.alert-card .alert-metric-label {
    display: block;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    font-weight: 700;
}

.alert-card .alert-metric-value { font-size: 1.12rem; font-weight: 800; color: var(--ink); }

.alert-card .alert-action {
    margin-top: 12px;
    font-size: 0.92rem;
    color: #334155;
    background: #F8FAFC;
    border-radius: 10px;
    padding: 9px 13px;
}

.status-tile {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 18px 20px;
    text-align: left;
    border-bottom: 4px solid var(--accent, #16A34A);
}

.status-tile .status-count {
    font-size: 2rem;
    font-weight: 800;
    color: var(--ink);
    line-height: 1.1;
}

.status-tile .status-name {
    font-size: 0.94rem;
    font-weight: 700;
    color: var(--ink);
    margin-top: 4px;
}

.status-tile .status-note {
    font-size: 0.82rem;
    color: var(--muted);
    margin-top: 6px;
    line-height: 1.45;
}

.insight-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 18px 20px;
    height: 100%;
    margin-bottom: 12px;
}

.insight-card .insight-title {
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    font-weight: 800;
    color: #F97316;
    margin: 8px 0 6px 0;
}

.insight-card .insight-text { font-size: 0.95rem; color: #334155; line-height: 1.55; }

.explain-note {
    background: #F1F5F9;
    border-radius: 12px;
    padding: 12px 16px;
    font-size: 0.92rem;
    color: #475569;
    line-height: 1.5;
    margin-top: 6px;
}

.buy-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 18px 22px;
    margin-bottom: 12px;
    border-left: 6px solid var(--accent, #EF4444);
}

.buy-card .buy-head {
    display: flex;
    justify-content: space-between;
    gap: 14px;
    align-items: baseline;
    flex-wrap: wrap;
}

.buy-card .buy-name { font-size: 1.1rem; font-weight: 750; color: var(--ink); }
.buy-card .buy-grid { display: flex; gap: 32px; margin-top: 12px; flex-wrap: wrap; }
.buy-card .buy-label {
    display: block;
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
    font-weight: 700;
}
.buy-card .buy-value { font-size: 1.15rem; font-weight: 800; color: var(--ink); }
.buy-card .buy-action { margin-top: 12px; font-weight: 700; color: var(--accent, #EF4444); }

.detail-metric {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 15px;
    padding: 16px 18px;
    height: 100%;
}
.detail-metric .detail-label {
    display: block;
    font-size: 0.74rem;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    font-weight: 700;
    color: var(--muted);
}
.detail-metric .detail-value {
    font-size: 1.45rem;
    font-weight: 800;
    color: var(--ink);
    margin-top: 6px;
    line-height: 1.2;
}
.detail-metric .detail-caption { font-size: 0.82rem; color: var(--muted); margin-top: 4px; }

[data-testid="stSidebar"] {
    background: #0B1B3A;
    border-right: none;
}

[data-testid="stSidebar"] * { color: #DCE7FF; }

[data-testid="stSidebar"] .sidebar-brand {
    padding: 6px 4px 18px 4px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.12);
    margin-bottom: 16px;
}

[data-testid="stSidebar"] .sidebar-brand .brand-name {
    font-size: 1.1rem;
    font-weight: 800;
    color: #FFFFFF;
    line-height: 1.25;
}

[data-testid="stSidebar"] .sidebar-brand .brand-tag {
    font-size: 0.78rem;
    color: #9DB6E8;
    margin-top: 3px;
}

[data-testid="stSidebar"] .sidebar-label {
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    font-weight: 800;
    color: #7E9AD4;
    margin: 18px 0 6px 2px;
}

[data-testid="stSidebar"] [role="radiogroup"] label {
    padding: 7px 10px;
    border-radius: 10px;
    margin-bottom: 2px;
}

[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: rgba(255, 255, 255, 0.07); }

[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.16);
}

[data-testid="stSidebar"] .stButton button {
    width: 100%;
    background: #F97316;
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    font-weight: 700;
    padding: 9px 0;
}

[data-testid="stSidebar"] .stButton button:hover { background: #EA6A0C; color: #FFFFFF; }

.shop-footer {
    margin-top: 46px;
    padding-top: 18px;
    border-top: 1px solid var(--line);
    font-size: 0.83rem;
    color: #94A3B8;
    display: flex;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
}

div[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; }
</style>
"""


def hero(title, subtitle, eyebrow, chips):
    chip_html = "".join(f'<span class="hero-chip">{escape(chip)}</span>' for chip in chips)
    return f"""
<div class="shop-hero">
    <span class="hero-eyebrow">{escape(eyebrow)}</span>
    <h1>{escape(title)}</h1>
    <p>{escape(subtitle)}</p>
    <div class="hero-chips">{chip_html}</div>
</div>
"""


def section_head(icon, title, subtitle=""):
    caption = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    return f"""
<div class="section-head">
    <h2>{icon} {escape(title)}</h2>
    {caption}
</div>
"""


def snapshot_card(icon, label, value, caption, tone="sales"):
    accent = TONE_COLORS.get(tone, TONE_COLORS["neutral"])
    return f"""
<div class="snap-card" style="--accent: {accent};">
    <span class="snap-icon">{icon}</span>
    <span class="snap-label">{escape(label)}</span>
    <div class="snap-value">{escape(str(value))}</div>
    <span class="snap-caption">{escape(caption)}</span>
</div>
"""


def story_panel(lines):
    body = "".join(
        f'<div class="story-line"><span class="story-bullet">&#9679;</span>'
        f"<span>{escape(line)}</span></div>"
        for line in lines
    )
    return f'<div class="story-panel">{body}</div>'


def momentum_banner(headline, detail, change_text, positive):
    accent = "#16A34A" if positive else "#EF4444"
    return f"""
<div class="momentum-banner" style="--accent: {accent};">
    <div>
        <div class="momentum-title">{escape(headline)}</div>
        <div class="momentum-detail">{escape(detail)}</div>
    </div>
    <div class="momentum-value">{escape(change_text)}</div>
</div>
"""


def sport_chip(category):
    color = category_color(category)
    return (
        f'<span class="sport-chip" style="background:{color}1A;color:{color};">'
        f"{escape(category)}</span>"
    )


def status_chip(status):
    color = rules.STATUS_COLOR[status]
    badge = rules.STATUS_BADGE[status]
    return (
        f'<span class="status-chip" style="background:{color}1A;color:{color};">'
        f"{badge} {escape(status)}</span>"
    )


def rank_card(rank, product_name, category, units, caption):
    badge = MEDALS.get(rank, f"{rank}")
    return f"""
<div class="rank-card">
    <div class="rank-badge">{badge}</div>
    <div class="rank-body">
        <div class="rank-name">{escape(product_name)}</div>
        {sport_chip(category)}
    </div>
    <div class="rank-figure">
        <div class="rank-units">{rules.format_units(units)}</div>
        <div class="rank-money">{escape(caption)}</div>
    </div>
</div>
"""


def podium_card(rank, product_name, category, units, revenue):
    accents = {1: "#F59E0B", 2: "#94A3B8", 3: "#C2724B"}
    return f"""
<div class="podium-card" style="--accent: {accents.get(rank, '#F97316')};">
    <div class="podium-medal">{MEDALS.get(rank, rank)}</div>
    <div class="podium-name">{escape(product_name)}</div>
    {sport_chip(category)}
    <div class="podium-units" style="margin-top:12px;">{rules.format_units(units)}</div>
    <div class="podium-caption">units sold &middot; {rules.format_currency(revenue)}</div>
</div>
"""


def alert_card(product_name, category, status, current_stock, expected_demand, action):
    color = rules.STATUS_COLOR[status]
    return f"""
<div class="alert-card" style="--accent: {color};">
    <div class="alert-top">
        <div>
            <div class="alert-name">{escape(product_name)}</div>
            {sport_chip(category)}
        </div>
        {status_chip(status)}
    </div>
    <div class="alert-numbers">
        <div>
            <span class="alert-metric-label">Current Stock</span>
            <span class="alert-metric-value">{rules.format_units(current_stock)}</span>
        </div>
        <div>
            <span class="alert-metric-label">Expected 7-Day Demand</span>
            <span class="alert-metric-value">{rules.format_units(expected_demand)}</span>
        </div>
    </div>
    <div class="alert-action"><strong>Suggested action:</strong> {escape(action)}</div>
</div>
"""


def momentum_card(product_name, category, previous_units, recent_units, label, change_text):
    return f"""
<div class="alert-card" style="--accent: #F97316;">
    <div class="alert-top">
        <div>
            <div class="alert-name">{escape(product_name)}</div>
            {sport_chip(category)}
        </div>
        <span class="status-chip" style="background:#F973161A;color:#F97316;">
            🔥 {escape(label)}
        </span>
    </div>
    <div class="alert-numbers">
        <div>
            <span class="alert-metric-label">Earlier Four Weeks</span>
            <span class="alert-metric-value">{rules.format_units(previous_units)}</span>
        </div>
        <div>
            <span class="alert-metric-label">Recent Four Weeks</span>
            <span class="alert-metric-value">{rules.format_units(recent_units)}</span>
        </div>
        <div>
            <span class="alert-metric-label">Change</span>
            <span class="alert-metric-value" style="color:#16A34A;">{escape(change_text)}</span>
        </div>
    </div>
</div>
"""


def status_tile(status, count):
    color = rules.STATUS_COLOR[status]
    return f"""
<div class="status-tile" style="--accent: {color};">
    <div class="status-count">{count}</div>
    <div class="status-name">{rules.STATUS_BADGE[status]} {escape(status)}</div>
    <div class="status-note">{escape(rules.STATUS_NOTE[status])}</div>
</div>
"""


def insight_card(icon, title, text):
    return f"""
<div class="insight-card">
    <div style="font-size:1.4rem;">{icon}</div>
    <div class="insight-title">{escape(title)}</div>
    <div class="insight-text">{escape(text)}</div>
</div>
"""


def explain_note(text):
    return f'<div class="explain-note">{escape(text)}</div>'


def buy_card(product_name, category, status, current_stock, expected_demand, action, cover_text):
    color = rules.STATUS_COLOR[status]
    return f"""
<div class="buy-card" style="--accent: {color};">
    <div class="buy-head">
        <div>
            <div class="buy-name">{escape(product_name)}</div>
            {sport_chip(category)}
        </div>
        {status_chip(status)}
    </div>
    <div class="buy-grid">
        <div>
            <span class="buy-label">Current Stock</span>
            <span class="buy-value">{rules.format_units(current_stock)}</span>
        </div>
        <div>
            <span class="buy-label">Expected 7-Day Demand</span>
            <span class="buy-value">{rules.format_units(expected_demand)}</span>
        </div>
        <div>
            <span class="buy-label">Stock Will Last</span>
            <span class="buy-value" style="font-size:0.98rem;">{escape(cover_text)}</span>
        </div>
    </div>
    <div class="buy-action">Action: {escape(action)}</div>
</div>
"""


def detail_metric(label, value, caption=""):
    note = f'<div class="detail-caption">{escape(caption)}</div>' if caption else ""
    return f"""
<div class="detail-metric">
    <span class="detail-label">{escape(label)}</span>
    <div class="detail-value">{escape(str(value))}</div>
    {note}
</div>
"""


def footer(updated_text, period_text):
    return f"""
<div class="shop-footer">
    <span>Naeem Sports Goods Shop &middot; Shop Intelligence Dashboard</span>
    <span>{escape(period_text)} &middot; {escape(updated_text)}</span>
</div>
"""

from __future__ import annotations

import html

import streamlit as st

from src.utils import (
    HOTEL_NAME,
    HOTEL_TAGLINE,
    PALETTE,
    STATUS_STYLES,
    format_change,
)

BASE_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {{ font-family: 'Inter', 'Segoe UI', sans-serif; }}
#MainMenu, footer {{ visibility: hidden; }}

.stApp {{ background: {PALETTE['background']}; }}
.block-container {{ padding-top: 2.4rem; padding-bottom: 3.5rem; max-width: 1320px; }}

h1, h2, h3, h4 {{ color: {PALETTE['ink']}; }}

section[data-testid="stSidebar"] {{ background: {PALETTE['ink']}; }}
section[data-testid="stSidebar"] * {{ color: #E8EDF2; }}
section[data-testid="stSidebar"] [data-baseweb="select"] > div,
section[data-testid="stSidebar"] .stDateInput input {{
    background: rgba(255,255,255,0.07);
    border-color: rgba(255,255,255,0.18);
    color: #E8EDF2;
}}

.gh-header {{
    background: linear-gradient(115deg, {PALETTE['ink']} 0%, #1C3B58 62%, #2A536F 100%);
    border-radius: 18px;
    padding: 30px 34px 26px 34px;
    margin-bottom: 26px;
    box-shadow: 0 14px 34px rgba(16,36,58,0.18);
}}
.gh-header .gh-brandline {{
    font-size: 0.72rem; letter-spacing: 0.22em; text-transform: uppercase;
    color: {PALETTE['sand']}; margin-bottom: 10px; font-weight: 600;
}}
.gh-header h1 {{
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 2.9rem; line-height: 1.05; color: #FFFFFF; margin: 0 0 6px 0;
    font-weight: 600; letter-spacing: 0.01em;
}}
.gh-header p {{ color: #C6D3DE; font-size: 1.02rem; margin: 0; }}
.gh-header .gh-context {{
    margin-top: 16px; padding-top: 14px; border-top: 1px solid rgba(255,255,255,0.14);
    color: #9FB3C4; font-size: 0.85rem;
}}

.gh-section {{ margin: 30px 0 14px 0; }}
.gh-section h2 {{
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 1.75rem; font-weight: 600; margin: 0 0 4px 0; color: {PALETTE['ink']};
}}
.gh-section p {{ color: {PALETTE['muted']}; font-size: 0.92rem; margin: 0; }}

.gh-kpi {{
    background: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 14px;
    padding: 18px 20px 16px 20px;
    height: 100%;
    min-height: 126px;
    box-shadow: 0 2px 10px rgba(16,36,58,0.05);
}}
.gh-kpi .gh-kpi-label {{
    font-size: 0.72rem; letter-spacing: 0.14em; text-transform: uppercase;
    color: {PALETTE['muted']}; font-weight: 600; margin-bottom: 8px;
}}
.gh-kpi .gh-kpi-value {{
    font-size: 1.85rem; font-weight: 600; color: {PALETTE['ink']}; line-height: 1.1;
    letter-spacing: -0.01em;
}}
.gh-kpi .gh-kpi-delta {{ font-size: 0.83rem; margin-top: 8px; font-weight: 500; }}
.gh-kpi .gh-kpi-note {{ font-size: 0.8rem; color: {PALETTE['muted']}; margin-top: 6px; }}

.gh-card {{
    background: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 14px;
    padding: 18px 20px;
    box-shadow: 0 2px 10px rgba(16,36,58,0.05);
    height: 100%;
}}

.gh-story {{
    background: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-left: 4px solid {PALETTE['brass']};
    border-radius: 12px;
    padding: 15px 18px;
    margin-bottom: 12px;
    box-shadow: 0 2px 8px rgba(16,36,58,0.04);
}}
.gh-story .gh-story-title {{
    font-size: 0.72rem; letter-spacing: 0.14em; text-transform: uppercase;
    font-weight: 700; margin-bottom: 6px;
}}
.gh-story .gh-story-text {{ color: {PALETTE['body']}; font-size: 0.95rem; line-height: 1.55; }}

.gh-badge {{
    display: inline-block; padding: 3px 11px; border-radius: 999px;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em;
}}

.gh-rec {{
    background: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 14px;
    box-shadow: 0 2px 10px rgba(16,36,58,0.05);
}}
.gh-rec h4 {{ margin: 10px 0 8px 0; font-size: 1.12rem; font-weight: 600; }}
.gh-rec .gh-rec-body {{ color: {PALETTE['body']}; font-size: 0.95rem; line-height: 1.6; }}
.gh-rec .gh-rec-action {{
    margin-top: 12px; padding-top: 12px; border-top: 1px dashed {PALETTE['border']};
    color: {PALETTE['ink']}; font-size: 0.9rem; font-weight: 500;
}}

.gh-question {{
    background: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 14px;
    padding: 18px 20px 16px 20px;
    height: 100%;
    min-height: 176px;
    box-shadow: 0 2px 10px rgba(16,36,58,0.05);
}}
.gh-question .gh-q-title {{ font-size: 1.05rem; font-weight: 600; color: {PALETTE['ink']}; }}
.gh-question .gh-q-answer {{
    color: {PALETTE['body']}; font-size: 0.92rem; line-height: 1.55; margin-top: 8px;
}}
.gh-question .gh-q-where {{
    margin-top: 12px; font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase;
    color: {PALETTE['brass']}; font-weight: 700;
}}

.gh-alert {{ border-radius: 14px; padding: 22px 24px; margin-bottom: 8px; border: 1px solid transparent; }}
.gh-alert .gh-alert-title {{ font-size: 1.25rem; font-weight: 700; margin-bottom: 6px; }}
.gh-alert .gh-alert-text {{ font-size: 0.96rem; line-height: 1.55; }}

.gh-note {{ color: {PALETTE['muted']}; font-size: 0.85rem; margin-top: 6px; line-height: 1.5; }}

.stButton > button {{
    width: 100%;
    border-radius: 10px;
    border: 1px solid {PALETTE['border']};
    background: {PALETTE['surface']};
    color: {PALETTE['ink']};
    font-weight: 600;
    font-size: 0.85rem;
    padding: 9px 14px;
    transition: all 0.15s ease;
}}
.stButton > button:hover {{
    border-color: {PALETTE['brass']};
    color: {PALETTE['brass']};
    background: {PALETTE['surface']};
}}
.stButton > button:focus:not(:active) {{
    border-color: {PALETTE['brass']};
    color: {PALETTE['brass']};
}}

[data-testid="stSidebarNav"]::before {{
    content: "Grand Horizon Hotel";
    display: block;
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 1.6rem;
    font-weight: 600;
    color: #FFFFFF;
    padding: 4px 0 10px 12px;
    letter-spacing: 0.01em;
}}
[data-testid="stSidebarNav"] {{ padding-top: 10px; }}
[data-testid="stSidebarNavItems"] {{ max-height: none !important; padding-bottom: 4px; }}
[data-testid="stSidebarNavViewButton"] {{ display: none !important; }}
[data-testid="stSidebarNavSeparator"] {{ border-color: rgba(255,255,255,0.14); }}
[data-testid="stSidebarNavItems"] li a {{ border-radius: 8px; }}

hr {{ border-color: {PALETTE['border']}; }}
</style>
"""


def inject_theme() -> None:
    st.markdown(BASE_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str, context: str | None = None) -> None:
    context_block = f'<div class="gh-context">{html.escape(context)}</div>' if context else ""
    st.markdown(
        f"""
        <div class="gh-header">
            <div class="gh-brandline">{html.escape(HOTEL_NAME)} &nbsp;&middot;&nbsp; {html.escape(HOTEL_TAGLINE)}</div>
            <h1>{html.escape(title)}</h1>
            <p>{html.escape(subtitle)}</p>
            {context_block}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, subtitle: str = "") -> None:
    subtitle_block = f"<p>{html.escape(subtitle)}</p>" if subtitle else ""
    st.markdown(
        f'<div class="gh-section"><h2>{html.escape(title)}</h2>{subtitle_block}</div>',
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, change=None, note: str | None = None,
             lower_is_better: bool = False) -> None:
    if change is not None:
        text, colour = format_change(change, lower_is_better=lower_is_better)
        delta = f'<div class="gh-kpi-delta" style="color:{colour};">{text}</div>'
    elif note:
        delta = f'<div class="gh-kpi-note">{html.escape(note)}</div>'
    else:
        delta = ""
    st.markdown(
        f"""
        <div class="gh-kpi">
            <div class="gh-kpi-label">{html.escape(label)}</div>
            <div class="gh-kpi-value">{html.escape(value)}</div>
            {delta}
        </div>
        """,
        unsafe_allow_html=True,
    )


def story_card(title: str, text: str, tone: str = "neutral") -> None:
    colour = STATUS_STYLES.get(tone, STATUS_STYLES["neutral"])[0]
    st.markdown(
        f"""
        <div class="gh-story" style="border-left-color:{colour};">
            <div class="gh-story-title" style="color:{colour};">{html.escape(title)}</div>
            <div class="gh-story-text">{html.escape(text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(tone: str, label: str | None = None) -> str:
    colour, soft, default_label = STATUS_STYLES.get(tone, STATUS_STYLES["neutral"])
    return (
        f'<span class="gh-badge" style="background:{soft};color:{colour};">'
        f"{html.escape(label or default_label)}</span>"
    )


def recommendation_card(category: str, title: str, body: str, action: str, tone: str) -> None:
    st.markdown(
        f"""
        <div class="gh-rec">
            {status_badge(tone)}
            <span class="gh-badge" style="background:{PALETTE['brass_soft']};color:{PALETTE['brass']};margin-left:8px;">{html.escape(category)}</span>
            <h4>{html.escape(title)}</h4>
            <div class="gh-rec-body">{html.escape(body)}</div>
            <div class="gh-rec-action">Suggested next step &nbsp;&middot;&nbsp; {html.escape(action)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def alert_banner(tone: str, title: str, text: str) -> None:
    colour, soft, _ = STATUS_STYLES.get(tone, STATUS_STYLES["neutral"])
    st.markdown(
        f"""
        <div class="gh-alert" style="background:{soft};border-color:{colour}33;">
            <div class="gh-alert-title" style="color:{colour};">{html.escape(title)}</div>
            <div class="gh-alert-text" style="color:{PALETTE['body']};">{html.escape(text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def question_card(question: str, answer: str, destination: str) -> None:
    st.markdown(
        f"""
        <div class="gh-question">
            <div class="gh-q-title">{html.escape(question)}</div>
            <div class="gh-q-answer">{html.escape(answer)}</div>
            <div class="gh-q-where">Open &middot; {html.escape(destination)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def caption(text: str) -> None:
    st.markdown(f'<div class="gh-note">{html.escape(text)}</div>', unsafe_allow_html=True)


def friendly_error(message: str) -> None:
    st.markdown(
        f"""
        <div class="gh-alert" style="background:{PALETTE['warning_soft']};border-color:{PALETTE['warning']}33;">
            <div class="gh-alert-title" style="color:{PALETTE['warning']};">This section is not available right now</div>
            <div class="gh-alert-text" style="color:{PALETTE['body']};">{html.escape(message)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

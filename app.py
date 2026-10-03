# app.py
"""Nexomate MVP — Main Streamlit Application."""

import streamlit as st
from pathlib import Path
from database.database import engine, Base
from database import models  # noqa: F401 — registers models with Base

# ── Create tables on first run ───────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── Run migrations for existing databases ────────────────────────────────────
try:
    from database.migrations import run_migrations
    run_migrations()
except Exception:
    pass  # Migrations are best-effort — new DBs already have correct schema

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nexomate",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS — Noir Press (Midnight Newsprint Edition) ───────────────────
st.markdown("""
<style>
    /* Google Fonts: Playfair Display (Serif display), Lora (Editorial body), JetBrains Mono (Terminal metadata), Inter (UI) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Lora:ital,wght@0,400;0,500;0,600;1,400&family=Playfair+Display:ital,wght@0,600;0,700;0,900;1,600&display=swap');

    :root {
        --noir-bg: #0A0A0A;
        --noir-surface: #121212;
        --noir-fg: #F3F3EF;
        --noir-muted: #1E1E1E;
        --noir-border: #333333;
        --noir-accent: #FF3333;
        --noir-text-muted: #888888;
    }

    /* Absolute 0px Radius Everywhere */
    *, *::before, *::after,
    .stApp, .stButton, button, input, select, textarea, div,
    [data-testid="stMetric"], .metric-card, .stDataFrame,
    [data-baseweb="tab-list"], [data-baseweb="tab"],
    .stSelectbox, .stTextInput, .stTextArea {
        border-radius: 0px !important;
    }

    /* Global Nocturnal Environment */
    html, body, [class*="css"] {
        font-family: 'Lora', Georgia, serif;
        color: #F3F3EF;
    }
    .stApp {
        background-color: #0A0A0A;
        background-image: radial-gradient(#262626 1px, transparent 1px);
        background-size: 16px 16px;
        color: #F3F3EF;
    }

    /* Headings in Editorial Serif */
    h1, h2, h3, h4, .font-serif {
        font-family: 'Playfair Display', Georgia, serif !important;
        letter-spacing: -0.5px;
        color: #F3F3EF !important;
    }

    /* Monospace Metadata & UI controls */
    .font-mono, .metric-label, .badge, [data-testid="stSidebar"] .stRadio label {
        font-family: 'JetBrains Mono', 'Courier New', monospace !important;
    }

    /* Sidebar — Nocturnal Broadsheet Drawer */
    [data-testid="stSidebar"] {
        background-color: #080808 !important;
        border-right: 1px solid #262626 !important;
        padding-top: 1rem;
    }
    [data-testid="stSidebar"] * {
        color: #F3F3EF !important;
    }
    .sidebar-masthead {
        border-top: 3px double #333333;
        border-bottom: 3px double #333333;
        padding: 0.8rem 0.5rem;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .sidebar-masthead-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.45rem;
        font-weight: 900;
        letter-spacing: 2px;
        color: #F3F3EF;
        text-transform: uppercase;
    }
    .sidebar-masthead-sub {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        letter-spacing: 2px;
        color: #888888;
        text-transform: uppercase;
        margin-top: 0.3rem;
    }
    [data-testid="stSidebar"] .stRadio label {
        padding: 0.65rem 1rem;
        border: 1px solid transparent;
        transition: all 150ms ease;
        text-transform: uppercase;
        font-size: 0.8rem;
        letter-spacing: 1px;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background-color: #161616;
        border-color: #333333;
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] [aria-checked="true"] {
        background-color: #1E1E1E !important;
        border-left: 3px solid #FF3333 !important;
        font-weight: 700;
    }

    /* Broadsheet Masthead Header Banner */
    .editorial-masthead {
        border-top: 3px double #333333;
        border-bottom: 3px double #333333;
        padding: 1.25rem 0.5rem;
        margin-bottom: 2rem;
        background: #0D0D0D;
    }
    .masthead-meta-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #888888;
        border-bottom: 1px solid #222222;
        padding-bottom: 0.5rem;
        margin-bottom: 0.8rem;
    }
    .masthead-main-title {
        font-family: 'Playfair Display', serif;
        font-size: 2.8rem;
        font-weight: 900;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #F3F3EF;
        margin: 0;
        line-height: 1;
    }
    .masthead-sub-rule {
        text-align: center;
        font-family: 'Lora', serif;
        font-style: italic;
        font-size: 1.05rem;
        color: #AAAAAA;
        margin-top: 0.5rem;
    }

    /* Section Headers */
    .section-header {
        font-family: 'Playfair Display', serif !important;
        font-size: 1.35rem !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        color: #F3F3EF !important;
        margin: 1.8rem 0 1rem 0;
        padding-bottom: 0.4rem;
        border-bottom: 2px solid #333333;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    /* Cards & Editorial Blocks */
    .metric-card, .noir-card {
        background: #121212 !important;
        border: 1px solid #333333 !important;
        padding: 1.5rem;
        color: #F3F3EF !important;
        transition: transform 150ms ease, box-shadow 150ms ease, border-color 150ms ease;
    }
    .metric-card:hover, .noir-card:hover {
        border-color: #F3F3EF !important;
        box-shadow: 4px 4px 0px 0px #F3F3EF;
        transform: translate(-2px, -2px);
    }
    .metric-value {
        font-family: 'Playfair Display', serif;
        font-size: 2.4rem;
        font-weight: 900;
        color: #F3F3EF;
        line-height: 1.05;
    }
    .metric-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        font-weight: 600;
        color: #888888;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-top: 0.5rem;
    }

    /* Badges in Monospace Brutalism */
    .badge-high {
        background-color: #122818;
        color: #4ADE80;
        border: 1px solid #22C55E;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 3px 8px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .badge-medium {
        background-color: #2D2305;
        color: #FACC15;
        border: 1px solid #EAB308;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 3px 8px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .badge-low {
        background-color: #2D1214;
        color: #F87171;
        border: 1px solid #EF4444;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 3px 8px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .badge-crimson {
        background-color: #FF3333;
        color: #0A0A0A;
        border: 1px solid #FF3333;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        font-weight: 800;
        padding: 3px 8px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .badge-bone {
        background-color: #F3F3EF;
        color: #0A0A0A;
        border: 1px solid #F3F3EF;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        font-weight: 800;
        padding: 3px 8px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Buttons — Brutalist High-Contrast */
    .stButton > button {
        background-color: #121212 !important;
        color: #F3F3EF !important;
        border: 1px solid #333333 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.8rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        padding: 0.65rem 1.4rem !important;
        transition: all 150ms ease !important;
    }
    .stButton > button:hover {
        background-color: #F3F3EF !important;
        color: #0A0A0A !important;
        border-color: #F3F3EF !important;
        box-shadow: 4px 4px 0px 0px #FF3333 !important;
        transform: translate(-2px, -2px) !important;
    }
    .stButton > button:active {
        transform: translate(0, 0) !important;
        box-shadow: none !important;
    }

    /* Form Inputs & Selects */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {
        background-color: #121212 !important;
        color: #F3F3EF !important;
        border: 1px solid #333333 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.85rem !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #FF3333 !important;
        box-shadow: 0 0 0 1px #FF3333 !important;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0A0A0A !important;
        border-bottom: 2px solid #333333 !important;
        gap: 6px !important;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #121212 !important;
        color: #888888 !important;
        border: 1px solid #333333 !important;
        border-bottom: none !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.78rem !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        padding: 0.7rem 1.4rem !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E1E1E !important;
        color: #F3F3EF !important;
        border-color: #F3F3EF !important;
        border-bottom: 2px solid #FF3333 !important;
        font-weight: 700 !important;
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #121212 !important;
        color: #F3F3EF !important;
        border: 1px solid #333333 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.85rem !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }
    [data-testid="stExpander"] {
        border: none !important;
    }

    /* Tables & DataFrames */
    .stDataFrame {
        border: 1px solid #333333 !important;
        background-color: #121212 !important;
    }

    /* Hide default streamlit branding but keep sidebar toggle visible */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {background: transparent !important;}
</style>
""", unsafe_allow_html=True)


# ── Sidebar Navigation ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-masthead">
        <div class="sidebar-masthead-title">◈ NEXOMATE</div>
        <div class="sidebar-masthead-sub">Nocturnal Wire Edition</div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        [
            "▣ Overview",
            "◎ Find Leads",
            "◉ Leads",
            "✉ Outreach",
            "↩ Inbox",
            "💬 WhatsApp AI",
            "▤ Campaigns",
            "📊 Analytics",
            "📁 Excel",
            "⚙ Settings",
        ],
        label_visibility="collapsed",
    )

    st.markdown("""
    <div style="margin-top: 3rem; border-top: 1px solid #222222; padding-top: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #666666; text-transform: uppercase; letter-spacing: 1.5px; text-align: center;">
        VOL. I · WIRE TERMINAL<br>
        200 VERIFIED PROSPECTS
    </div>
    """, unsafe_allow_html=True)

# ── Page Routing ─────────────────────────────────────────────────────────────
if page == "▣ Overview":
    from dashboard.overview import overview_page
    overview_page()

elif page == "◎ Find Leads":
    from dashboard.sourcing import sourcing_page
    sourcing_page()

elif page == "◉ Leads":
    from dashboard.leads import leads_page
    leads_page()

elif page == "✉ Outreach":
    from dashboard.outreach_page import outreach_page
    outreach_page()

elif page == "↩ Inbox":
    from dashboard.inbox import inbox_page
    inbox_page()

elif page == "💬 WhatsApp AI":
    from dashboard.whatsapp_page import whatsapp_page
    whatsapp_page()

elif page == "▤ Campaigns":
    from dashboard.campaigns import campaigns_page
    campaigns_page()

elif page == "📊 Analytics":
    from dashboard.analytics import analytics_page
    analytics_page()

elif page == "📁 Excel":
    from dashboard.excel_page import excel_page
    excel_page()

elif page == "⚙ Settings":
    from dashboard.settings import settings_page
    settings_page()

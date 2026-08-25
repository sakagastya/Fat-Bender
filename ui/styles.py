from string import Template

import streamlit as st

CUT_TOKENS = {
    "goal_mode": "cut",
    "label": "Fat Loss · Cut",
    "chip": "CUT",
    "ACCENT": "#22D3EE",
    "STRONG": "#0EA5B7",
    "DIM": "rgba(34,211,238,0.40)",
    "SOFT": "rgba(34,211,238,0.10)",
    "SURFACE": "#101B2B",
    "ON_ACCENT": "#04252B",
}

BULK_TOKENS = {
    "goal_mode": "bulk",
    "label": "Fat Gain · Bulk",
    "chip": "BULK",
    "ACCENT": "#FB923C",
    "STRONG": "#F97316",
    "DIM": "rgba(251,146,60,0.40)",
    "SOFT": "rgba(251,146,60,0.10)",
    "SURFACE": "#1D1620",
    "ON_ACCENT": "#2B1204",
}

CSS_TEMPLATE = Template("""
[data-testid="stHeader"], [data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"], #MainMenu, footer,
[data-testid="stStatusWidget"] {display: none !important;}
.block-container {padding: .8rem .85rem 5rem; max-width: 520px; margin: 0 auto;}
h1 {font-size: 1.5rem !important; letter-spacing: -.02em; margin-bottom: .15rem !important;}
p {margin-bottom: .35rem;}
.fb-chip {display: inline-flex; align-items: center; padding: 3px 12px; border-radius: 999px;
  font-size: .68rem; font-weight: 800; letter-spacing: .09em; text-transform: uppercase;
  color: $ACCENT; border: 1px solid $DIM; background: $SOFT;}
.fb-sub {color: #8FA3BF; font-size: .78rem; margin-top: 2px;}
.fb-card {border: 1px solid $DIM; background: $SURFACE; border-radius: 16px;
  padding: 14px 15px; margin: 6px 0 14px;}
.fb-card h4 {margin: 0 0 8px; font-size: .95rem;}
.fb-quote {border-left: 3px solid $ACCENT; padding: 8px 12px; border-radius: 10px;
  background: $SOFT; font-size: .88rem; color: #C7D4E8;}
.fb-row {display: flex; justify-content: space-between; align-items: center;
  padding: 5px 0; border-bottom: 1px dashed rgba(255,255,255,.07); font-size: .86rem;}
.fb-row:last-child {border-bottom: none;}
.fb-row b {font-variant-numeric: tabular-nums;}
.fb-delta {color: $ACCENT; font-weight: 800; margin-left: 8px; font-size: .8rem;}
.fb-pill {display: inline-flex; align-items: center; gap: 8px; padding: 6px 13px;
  border-radius: 999px; background: $SOFT; border: 1px solid $DIM;
  color: #C7D4E8; font-size: .8rem;}
.fb-badge {display: inline-block; padding: 2px 9px; margin: 0 5px 4px 0; border-radius: 999px;
  border: 1px solid $DIM; background: rgba(255,255,255,.04); color: #C7D4E8;
  font-size: .68rem; font-weight: 700; letter-spacing: .02em;}
.fb-dial {max-width: 330px; margin: 2px auto 6px;}
.fb-day {border-radius: 12px; padding: 7px 2px; text-align: center;
  border: 1px solid rgba(255,255,255,.08); background: $SURFACE;}
.fb-dow {font-size: .6rem; letter-spacing: .08em; color: #8FA3BF; text-transform: uppercase;}
.fb-kcal {font-size: .82rem; font-weight: 800; color: #EAF2FB; margin-top: 2px;
  font-variant-numeric: tabular-nums;}
.fb-goal {font-size: .58rem; color: #8FA3BF;}
.fb-day.ok {border-color: rgba(52,211,153,.55); background: rgba(52,211,153,.10);}
.fb-day.warn {border-color: rgba(251,191,36,.55); background: rgba(251,191,36,.10);}
.fb-day.bad {border-color: rgba(248,113,113,.55); background: rgba(248,113,113,.10);}
.fb-alert {border: 1px solid rgba(251,191,36,.5); background: rgba(251,191,36,.08);
  border-radius: 16px; padding: 12px 14px; margin: 6px 0 12px; font-size: .88rem;}
.stButton > button {width: 100%; border-radius: 12px; font-weight: 600;
  border: 1px solid $DIM; background: $SURFACE; color: #E8EEF7; padding: .5rem .8rem;}
.stButton > button:hover {border-color: $ACCENT; color: $ACCENT;}
button[kind="primary"] {background: $ACCENT !important; border-color: $ACCENT !important;
  color: $ON_ACCENT !important;}
button[kind="primary"]:hover {filter: brightness(1.08); color: $ON_ACCENT !important;}
[data-baseweb="tab-list"] {gap: 4px; border-bottom-color: $DIM;}
[data-baseweb="tab"] {flex: 1 1 0; justify-content: center; padding: 8px 4px; font-size: .85rem;}
[data-baseweb="tab-highlight"] {background-color: $ACCENT; height: 3px;}
[data-testid="stVerticalBlockBorderWrapper"] {border-color: $DIM !important;
  border-radius: 16px !important; background: $SURFACE;}
input, textarea {background-color: $SURFACE !important; font-size: .95rem !important;}
[data-baseweb="base-input"] {border-color: $DIM;}
[data-baseweb="base-input"]:focus-within {border-color: $ACCENT !important;
  box-shadow: 0 0 0 1px $DIM !important;}
[data-testid="stMetricValue"] {font-size: 1.3rem; font-weight: 700;
  font-variant-numeric: tabular-nums;}
[data-testid="stMetricLabel"] p {font-size: .7rem; text-transform: uppercase;
  letter-spacing: .06em; color: #8FA3BF;}
hr {border-color: $DIM; margin: .6rem 0;}
""")


def build_tokens(profile):
    mode = (profile or {}).get("goal_mode")
    return dict(BULK_TOKENS if mode == "bulk" else CUT_TOKENS)


def inject_theme(tokens):
    st.markdown(
        f"<style>{CSS_TEMPLATE.substitute(tokens)}</style>",
        unsafe_allow_html=True,
    )

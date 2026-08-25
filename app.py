import streamlit as st

import database
from ui.i18n import language_selector, tr
from ui.onboarding import render_onboarding
from ui.state import init_session_state, refresh_active_date
from ui.styles import build_tokens, inject_theme
from ui.tabs.coach import render_coach
from ui.tabs.setup import render_setup
from ui.tabs.today import render_today

st.set_page_config(
    page_title="Fat Bender",
    layout="centered",
    initial_sidebar_state="collapsed",
)

init_session_state()
refresh_active_date()

profile = database.get_profile()
tokens = build_tokens(profile)
st.session_state.theme_tokens = tokens
inject_theme(tokens)

lang_row = st.columns([4, 1])
with lang_row[1]:
    language_selector()

chip = f'<span class="fb-chip">{tokens["chip"]} · {tokens["label"]}</span>' if profile else ""
st.markdown(
    f'<div style="display:flex;align-items:center;gap:10px;">'
    f"<h1 style=\"margin:0;\">Fat Bender</h1>{chip}</div>"
    f'<div class="fb-sub">{tr("active_date", date=st.session_state.active_date)}</div>',
    unsafe_allow_html=True,
)
st.write("")

if not profile:
    render_onboarding()
else:
    tab_today, tab_coach, tab_setup = st.tabs(
        [tr("tab_today"), tr("tab_coach"), tr("tab_setup")]
    )
    with tab_today:
        render_today(profile)
    with tab_coach:
        render_coach(profile)
    with tab_setup:
        render_setup(profile)

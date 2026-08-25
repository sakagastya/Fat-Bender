from datetime import date

import streamlit as st

STATE_DEFAULTS = {
    "app_language": "en",
    "user_gemini_key": "",
    "key_verified": False,
    "ob_step": 1,
    "ob_goal_mode": "cut",
    "ob_bio": None,
    "ob_plan": None,
    "active_date": date.today().isoformat(),
    "meal_review_buffer": None,
    "review_gen": 0,
    "confirm_delete_id": None,
    "theme_tokens": None,
    "pending_switch": None,
    "pending_recalc": None,
}


def init_session_state():
    for key, value in STATE_DEFAULTS.items():
        st.session_state.setdefault(key, value)


def refresh_active_date():
    today = date.today().isoformat()
    if st.session_state.active_date != today:
        st.session_state.active_date = today


def clear_onboarding_state():
    for key in ("ob_step", "ob_goal_mode", "ob_bio", "ob_plan"):
        st.session_state.pop(key, None)

from datetime import date

import streamlit as st

import ai
import database
from database.profile import PROFILE_FIELDS
from ui.analytics import STATUS_TITLES, SUGGESTED_ADJUSTMENT, detect_trend
from ui.styles import build_tokens

STATUS_CLASS = {"On-Target": "ok", "Minor Drift": "warn", "Off-Target": "bad"}


def _adherence_strip():
    week = database.get_adherence_week()
    target = week["target_calories"]
    st.subheader("Last 7 Days")
    cols = st.columns(7)
    for col, day in zip(cols, week["days"]):
        dow = date.fromisoformat(day["date"]).strftime("%a")
        status = day["status"]
        cls = STATUS_CLASS.get(status, "")
        goal_text = f"/ {target:.0f}" if target else "/ —"
        title = status or "No target set"
        col.markdown(
            f"<div class='fb-day {cls}' title='{title}'>"
            f"<div class='fb-dow'>{dow}</div>"
            f"<div class='fb-kcal'>{day['total_calories']:.0f}</div>"
            f"<div class='fb-goal'>{goal_text} kcal</div></div>",
            unsafe_allow_html=True,
        )


def build_trend_figure(history, tokens, target_weight=None):
    import pandas as pd
    import plotly.graph_objects as go

    frame = pd.DataFrame(history)
    frame["date"] = pd.to_datetime(frame["date"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=frame["date"], y=frame["weight_kg"], mode="markers",
        name="Weigh-ins",
        marker=dict(color="#8FA3BF", size=6, opacity=0.85),
    ))
    fig.add_trace(go.Scatter(
        x=frame["date"], y=frame["rolling_avg_7d"], mode="lines",
        name="7-day average",
        line=dict(color=tokens["ACCENT"], width=3, shape="spline", smoothing=0.8),
        hovertemplate="%{y:.2f} kg<extra>7-day avg</extra>",
    ))
    if target_weight and target_weight > 0:
        fig.add_hline(
            y=target_weight, line_dash="dash", line_color="#F87171", line_width=1.5,
            annotation_text=f"Goal {target_weight:.0f} kg",
            annotation_font=dict(size=9, color="#F87171"),
        )
    return fig


def _trend_section(profile, tokens):
    st.subheader("Scale Trend")
    history = database.get_weight_history()
    if len(history) < 2:
        st.markdown(
            f"<div class='fb-quote'>Only {len(history)} check-in"
            f"{'s' if len(history) != 1 else ''} so far. Consistent morning weigh-ins "
            "unlock your true trend line — the raw spikes are mostly water and glycogen.</div>",
            unsafe_allow_html=True,
        )
        return
    target_weight = float(profile.get("target_weight_kg") or 0)
    fig = build_trend_figure(history, tokens, target_weight)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#C7D4E8", size=11, family="sans-serif"),
        margin=dict(l=6, r=6, t=26, b=4), height=280,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(tickformat="%d %b", gridcolor="rgba(255,255,255,.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,.07)", zeroline=False,
                   ticksuffix=" kg"),
    )
    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": False})
    st.caption(f"Trend across {len(history)} weigh-ins · goal {target_weight:.0f} kg")


def _calibration_drawer(profile, tokens):
    trend = detect_trend(profile, database.get_weight_history())
    if trend["status"] == "insufficient":
        st.markdown(
            "<div class='fb-quote'>Calibration unlocks after about a week of consistent "
            "morning weigh-ins.</div>",
            unsafe_allow_html=True,
        )
        return
    if trend["status"] == "healthy":
        st.markdown("<div class='fb-pill'>Trend looks on-track · no calibration needed</div>",
                    unsafe_allow_html=True)
        return

    title = STATUS_TITLES[trend["status"]]
    suggestion = SUGGESTED_ADJUSTMENT[trend["status"]]
    rate = trend["rate"]
    delta_text = f"{rate['weekly_delta']:+.1f} kg this week" if rate else ""
    st.markdown(
        f"<div class='fb-alert'><b>Calibration Drawer · {title}</b><br/>"
        f"{trend['message']} <small>({delta_text})</small></div>",
        unsafe_allow_html=True,
    )

    adjustment = st.slider("Daily calorie adjustment (kcal)", -250, 250,
                           value=int(suggestion), step=25, key="cal_slider")

    current_target = float(profile.get("target_calories") or 0)
    weight = float(profile.get("current_weight_kg") or 0)
    plan = ai.calibrate_plan(profile.get("tdee_baseline"), current_target,
                             adjustment, weight, profile.get("goal_mode"))

    new_target = plan["target_calories"]
    shift = new_target - current_target
    sign = "+" if shift >= 0 else "\u2212"
    rows = (
        f"<div class='fb-row'><span>Daily calories</span>"
        f"<span>{current_target:.0f} → <b style='color:{tokens['ACCENT']};'>{new_target:.0f}</b>"
        f"<span class='fb-delta'>{sign}{abs(shift):.0f}</span></span></div>"
        f"<div class='fb-row'><span>Protein</span><b>{plan['protein_target_g']:.0f} g</b></div>"
        f"<div class='fb-row'><span>Carbs</span><b>{plan['carbs_target_g']:.0f} g</b></div>"
        f"<div class='fb-row'><span>Fat</span><b>{plan['fat_target_g']:.0f} g</b></div>"
    )
    st.markdown(f"<div class='fb-card'>{rows}</div>", unsafe_allow_html=True)

    if st.button("Confirm & Apply Calibration", type="primary", key="cal_apply"):
        merged = {field: profile.get(field) for field in PROFILE_FIELDS}
        merged.update({
            "target_calories": float(plan["target_calories"]),
            "protein_target_g": float(plan["protein_target_g"]),
            "carbs_target_g": float(plan["carbs_target_g"]),
            "fat_target_g": float(plan["fat_target_g"]),
        })
        database.save_profile(**merged)
        st.toast("Targets calibrated across your engine.")
        st.rerun()


def render_coach(profile):
    if not profile:
        return
    tokens = build_tokens(profile)
    _adherence_strip()
    st.divider()
    _trend_section(profile, tokens)
    st.divider()
    _calibration_drawer(profile, tokens)

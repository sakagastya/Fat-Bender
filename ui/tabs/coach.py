from datetime import date

import streamlit as st

import ai
import database
from database.profile import PROFILE_FIELDS
from ui.analytics import SUGGESTED_ADJUSTMENT, detect_trend
from ui.i18n import tr
from ui.styles import build_tokens

STATUS_CLASS = {"On-Target": "ok", "Minor Drift": "warn", "Off-Target": "bad"}
STATUS_KEY = {"cut_plateau": "t_cut_plateau", "bulk_fast": "t_bulk_fast",
              "bulk_stall": "t_bulk_stall"}
MESSAGE_KEY = {"cut_plateau": "msg_cut_plateau", "bulk_fast": "msg_bulk_fast",
               "bulk_stall": "msg_bulk_stall"}


def _adherence_strip():
    week = database.get_adherence_week()
    target = week["target_calories"]
    st.subheader(tr("last7"))
    cols = st.columns(7)
    for col, day in zip(cols, week["days"]):
        dow = date.fromisoformat(day["date"]).strftime("%a")
        status = day["status"]
        cls = STATUS_CLASS.get(status, "")
        goal_text = f"/ {target:.0f}" if target else "/ —"
        title = status or "—"
        col.markdown(
            f"<div class='fb-day {cls}' title='{title}'>"
            f"<div class='fb-dow'>{dow}</div>"
            f"<div class='fb-kcal'>{day['total_calories']:.0f}</div>"
            f"<div class='fb-goal'>{goal_text} kcal</div></div>",
            unsafe_allow_html=True,
        )


def build_trend_figure(history, tokens, target_weight=None, labels=None):
    import pandas as pd
    import plotly.graph_objects as go

    L = {"raw": "Weigh-ins", "avg": "7-day average", "goal": "Goal {g} kg",
         **(labels or {})}
    frame = pd.DataFrame(history)
    frame["date"] = pd.to_datetime(frame["date"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=frame["date"], y=frame["weight_kg"], mode="markers",
        name=L["raw"],
        marker=dict(color="#8FA3BF", size=6, opacity=0.85),
    ))
    fig.add_trace(go.Scatter(
        x=frame["date"], y=frame["rolling_avg_7d"], mode="lines",
        name=L["avg"],
        line=dict(color=tokens["ACCENT"], width=3, shape="spline", smoothing=0.8),
        hovertemplate="%{y:.2f} kg<extra></extra>",
    ))
    if target_weight and target_weight > 0:
        fig.add_hline(
            y=target_weight, line_dash="dash", line_color="#F87171", line_width=1.5,
            annotation_text=L["goal"].format(g=f"{target_weight:.0f}"),
            annotation_font=dict(size=9, color="#F87171"),
        )
    return fig


def _trend_section(profile, tokens):
    st.subheader(tr("trend_h"))
    history = database.get_weight_history()
    if len(history) < 2:
        n = len(history)
        st.markdown(
            f"<div class='fb-quote'>{tr('sparse', n=n, s='' if n == 1 else 's')}</div>",
            unsafe_allow_html=True,
        )
        return
    target_weight = float(profile.get("target_weight_kg") or 0)
    labels = {"raw": tr("legend_raw"), "avg": tr("legend_avg"),
              "goal": tr("goal_line", g="{g}")}
    fig = build_trend_figure(history, tokens, target_weight, labels)
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
    st.caption(tr("trend_cap", n=len(history), g=f"{target_weight:.0f}"))


def _calibration_drawer(profile, tokens):
    trend = detect_trend(profile, database.get_weight_history())
    if trend["status"] == "insufficient":
        st.markdown(f"<div class='fb-quote'>{tr('calib_unlock')}</div>",
                    unsafe_allow_html=True)
        return
    if trend["status"] == "healthy":
        st.markdown(f"<div class='fb-pill'>{tr('healthy_pill')}</div>",
                    unsafe_allow_html=True)
        return

    rate = trend["rate"]
    delta_text = f"{rate['weekly_delta']:+.1f} kg" if rate else ""
    message = tr(
        MESSAGE_KEY[trend["status"]],
        last=f"{rate['last_rolling']:.1f}" if rate else "—",
        delta=delta_text,
    )
    st.markdown(
        f"<div class='fb-alert'><b>{tr('drawer_title', t=tr(STATUS_KEY[trend['status']]))}</b><br/>"
        f"{message} <small>({delta_text})</small></div>",
        unsafe_allow_html=True,
    )

    adjustment = st.slider(tr("slider_cal"), -250, 250,
                           value=int(SUGGESTED_ADJUSTMENT[trend["status"]]),
                           step=25, key="cal_slider")

    current_target = float(profile.get("target_calories") or 0)
    weight = float(profile.get("current_weight_kg") or 0)
    plan = ai.calibrate_plan(profile.get("tdee_baseline"), current_target,
                             adjustment, weight, profile.get("goal_mode"))

    new_target = plan["target_calories"]
    shift = new_target - current_target
    sign = "+" if shift >= 0 else "\u2212"
    rows = (
        f"<div class='fb-row'><span>{tr('r_calories')}</span>"
        f"<span>{current_target:.0f} → <b style='color:{tokens['ACCENT']};'>{new_target:.0f}</b>"
        f"<span class='fb-delta'>{sign}{abs(shift):.0f}</span></span></div>"
        f"<div class='fb-row'><span>{tr('m_protein')}</span><b>{plan['protein_target_g']:.0f} g</b></div>"
        f"<div class='fb-row'><span>{tr('m_carbs')}</span><b>{plan['carbs_target_g']:.0f} g</b></div>"
        f"<div class='fb-row'><span>{tr('m_fat')}</span><b>{plan['fat_target_g']:.0f} g</b></div>"
    )
    st.markdown(f"<div class='fb-card'>{rows}</div>", unsafe_allow_html=True)

    if st.button(tr("apply_cal"), type="primary", key="cal_apply"):
        merged = {field: profile.get(field) for field in PROFILE_FIELDS}
        merged.update({
            "target_calories": float(plan["target_calories"]),
            "protein_target_g": float(plan["protein_target_g"]),
            "carbs_target_g": float(plan["carbs_target_g"]),
            "fat_target_g": float(plan["fat_target_g"]),
        })
        database.save_profile(**merged)
        st.toast(tr("toast_cal"))
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

import streamlit as st

import ai
import database
from database.profile import PROFILE_FIELDS
from ui.styles import build_tokens

GOAL_LABELS = {"Fat Loss (Cut)": "cut", "Fat Gain (Bulk)": "bulk"}
SEX_LABELS = {"Male": "male", "Female": "female"}


def _merge_profile(profile, edits):
    merged = {field: profile.get(field) for field in PROFILE_FIELDS}
    merged.update(edits)
    return merged


def _masked_hint(key):
    if not key:
        return "No key stored in this session yet."
    tail = key[-4:] if len(key) >= 8 else "****"
    return f"Stored key ends with ...{tail}"


def _api_section():
    st.subheader("API Access")
    st.text_input("Gemini API key", type="password", key="setup_key",
                  placeholder="Paste a new key to replace the current one")
    st.markdown(f'<div class="fb-sub">{_masked_hint(st.session_state.user_gemini_key)}</div>',
                unsafe_allow_html=True)
    row = st.columns(2)
    if row[0].button("Save Key", key="setup_save"):
        candidate = st.session_state.setup_key.strip()
        if not candidate:
            st.error("Nothing to save — enter a key first.")
        else:
            st.session_state.user_gemini_key = candidate
            st.session_state.key_verified = False
            st.toast("API key stored for this session.")
            st.rerun()
    if row[1].button("Test Connection", type="primary", key="setup_test"):
        candidate = st.session_state.setup_key.strip() or st.session_state.user_gemini_key
        if not candidate:
            st.error("No API key available to test.")
        else:
            ok, message = ai.validate_api_key(candidate)
            st.session_state.key_verified = ok
            if ok:
                st.success(message)
            else:
                st.error(f"Connection failed: {message}")


def _biometrics_section(profile):
    st.subheader("Biometrics & Daily Targets")
    a, b = st.columns(2)
    a.number_input("Age", 13, 90, value=int(profile.get("age") or 28), key="su_age")
    current_sex = profile.get("gender") if profile.get("gender") in SEX_LABELS.values() else "male"
    b.radio("Biological sex", list(SEX_LABELS),
            index=list(SEX_LABELS.values()).index(current_sex),
            key="su_sex", horizontal=True)
    c, d = st.columns(2)
    c.number_input("Height (cm)", 120.0, 250.0,
                   value=float(profile.get("height_cm") or 175.0),
                   step=0.5, format="%.1f", key="su_height")
    d.number_input("Current weight (kg)", 30.0, 300.0,
                   value=float(profile.get("current_weight_kg") or 80.0),
                   step=0.1, format="%.1f", key="su_weight")
    e, f = st.columns(2)
    e.number_input("Target weight (kg)", 30.0, 300.0,
                   value=float(profile.get("target_weight_kg") or 72.0),
                   step=0.1, format="%.1f", key="su_target_w")
    f.write("")
    st.text_area("Daily activity in your own words",
                 value=str(profile.get("activity_description") or ""),
                 height=70, key="su_activity")

    pending = st.session_state.pending_recalc
    row = st.columns(2)
    if row[0].button("Save Biometrics", key="su_savebio"):
        merged = _merge_profile(profile, _collect_edits())
        database.save_profile(**merged)
        st.toast("Biometrics saved.")
        st.rerun()
    if row[1].button("Recalculate via AI", type="primary", key="su_recalc"):
        key = st.session_state.user_gemini_key
        if not key:
            st.error("Store a Gemini API key above before recalculating.")
        else:
            edits = _collect_edits()
            merged = _merge_profile(profile, edits)
            with st.spinner("Estimating fresh targets..."):
                result = ai.estimate_plan(
                    key, merged["age"], merged["gender"], merged["height_cm"],
                    merged["current_weight_kg"], merged["activity_description"],
                    merged["goal_mode"],
                )
            if result["ok"]:
                st.session_state.pending_recalc = {"merged": merged,
                                                   "plan": result["plan"]}
                st.rerun()
            else:
                st.error(f"Recalculation failed: {result['error']}")

    if pending:
        plan = pending["plan"]
        st.markdown("**Proposed recalibration**")
        m1, m2 = st.columns(2)
        m1.metric("Baseline TDEE", f"{plan['tdee_baseline']:.0f} kcal")
        m2.metric("Daily Target", f"{plan['target_calories']:.0f} kcal")
        p, c2, f3 = st.columns(3)
        p.metric("Protein", f"{plan['protein_target_g']:.0f} g")
        c2.metric("Carbs", f"{plan['carbs_target_g']:.0f} g")
        f3.metric("Fat", f"{plan['fat_target_g']:.0f} g")
        if plan.get("rationale"):
            st.markdown(f'<div class="fb-quote">{plan["rationale"]}</div>',
                        unsafe_allow_html=True)
        apply_row = st.columns(2)
        if apply_row[0].button("Apply Updated Targets", type="primary", key="su_apply"):
            final = dict(pending["merged"])
            final.update({
                "tdee_baseline": float(plan["tdee_baseline"]),
                "target_calories": float(plan["target_calories"]),
                "protein_target_g": float(plan["protein_target_g"]),
                "carbs_target_g": float(plan["carbs_target_g"]),
                "fat_target_g": float(plan["fat_target_g"]),
            })
            database.save_profile(**final)
            st.session_state.pending_recalc = None
            st.toast("Targets updated.")
            st.rerun()
        if apply_row[1].button("Discard", key="su_discard"):
            st.session_state.pending_recalc = None
            st.rerun()


def _collect_edits():
    return {
        "age": int(st.session_state.su_age),
        "gender": SEX_LABELS[st.session_state.su_sex],
        "height_cm": float(st.session_state.su_height),
        "current_weight_kg": float(st.session_state.su_weight),
        "target_weight_kg": float(st.session_state.su_target_w),
        "activity_description": str(st.session_state.su_activity or "").strip(),
    }


def _plan_rows(base, proposed=None, accent="#22D3EE"):
    keys = [
        ("Calories", "target_calories"),
        ("Protein", "protein_target_g"),
        ("Carbs", "carbs_target_g"),
        ("Fat", "fat_target_g"),
    ]
    rows = []
    for label, field in keys:
        b_value = float(base.get(field) or 0)
        cell = f"<span><b>{b_value:.0f}</b></span>"
        if proposed is not None:
            p_value = float(proposed.get(field) or 0)
            delta = p_value - b_value
            sign = "+" if delta >= 0 else "\u2212"
            cell = (f"<span><b>{p_value:.0f}</b>"
                    f"<span class='fb-delta'>{sign}{abs(delta):.0f}</span></span>")
        rows.append(
            f"<div class='fb-row'><span>{label}"
            + (f" <small>(was {b_value:.0f})</small>" if proposed is not None else "")
            + f"</span>{cell}</div>"
        )
    return "".join(rows)


def _phase_section(profile):
    st.subheader("Phase Switcher")
    tokens = build_tokens(profile)
    current = profile.get("goal_mode") or "cut"
    options = list(GOAL_LABELS)
    st.radio("Active phase", options,
             index=options.index("Fat Gain (Bulk)") if current == "bulk" else 0,
             key="sw_mode", horizontal=True)
    selected = GOAL_LABELS[st.session_state.sw_mode]

    if selected == current:
        st.session_state.pending_switch = None
        st.markdown(
            f'<div class="fb-quote">You are already running '
            f'<b>{tokens["label"]}</b>. Switch phases to preview a new macro engine.</div>',
            unsafe_allow_html=True,
        )
        return

    if st.button("Preview Phase Switch", type="primary", key="sw_preview"):
        tdee = profile.get("tdee_baseline")
        weight = float(profile.get("current_weight_kg") or 0)
        if not tdee or weight <= 0:
            st.warning("Baseline TDEE missing — recalculate targets via AI first.")
        else:
            st.session_state.pending_switch = {
                "from": current,
                "to": selected,
                "plan": ai.compute_plan(tdee, weight, selected),
            }
            st.rerun()

    pending = st.session_state.pending_switch
    if not pending or pending["to"] != selected:
        return

    target_tokens = build_tokens({"goal_mode": pending["to"]})
    guidance = (
        "A cut phase runs a 400 kcal deficit with high protein for muscle retention."
        if pending["to"] == "cut"
        else "A bulk phase runs a 350 kcal surplus with carbs prioritized for training fuel."
    )
    left, right = st.columns(2)
    with left:
        st.markdown(
            f"<div class='fb-card'><h4>Current · {pending['from'].upper()}</h4>"
            f"{_plan_rows(profile)}</div>",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f"<div class='fb-card' style='border-color:{target_tokens['ACCENT']};'>"
            f"<h4 style='color:{target_tokens['ACCENT']};'>Proposed · {pending['to'].upper()}</h4>"
            f"{_plan_rows(profile, pending['plan'])}</div>",
            unsafe_allow_html=True,
        )
    st.markdown(f'<div class="fb-quote">Guided transition: {guidance} '
                f"Apply only when you are ready to switch immediately.</div>",
                unsafe_allow_html=True)

    confirm_row = st.columns(2)
    if confirm_row[0].button("Confirm & Apply Phase Switch", type="primary",
                             key="sw_confirm"):
        final = _merge_profile(profile, {"goal_mode": pending["to"]})
        plan = pending["plan"]
        final.update({
            "target_calories": float(plan["target_calories"]),
            "protein_target_g": float(plan["protein_target_g"]),
            "carbs_target_g": float(plan["carbs_target_g"]),
            "fat_target_g": float(plan["fat_target_g"]),
        })
        database.save_profile(**final)
        st.session_state.pending_switch = None
        st.toast(f"Phase switched to {target_tokens['label']}.")
        st.rerun()
    if confirm_row[1].button("Cancel", key="sw_cancel"):
        st.session_state.pending_switch = None
        st.rerun()


def render_setup(profile):
    if not profile:
        return
    _api_section()
    st.divider()
    _biometrics_section(profile)
    st.divider()
    _phase_section(profile)

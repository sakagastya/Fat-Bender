import streamlit as st

import ai
import database
from database.profile import PROFILE_FIELDS
from ui.i18n import goal_choices, sex_choices, tr
from ui.styles import build_tokens


def _merge_profile(profile, edits):
    merged = {field: profile.get(field) for field in PROFILE_FIELDS}
    merged.update(edits)
    return merged


def _masked_hint(key):
    if not key:
        return tr("no_key")
    tail = key[-4:] if len(key) >= 8 else "****"
    return tr("stored_tail", tail=tail)


def _api_section():
    st.subheader(tr("api_h"))
    st.text_input(tr("ob_key_label"), type="password", key="setup_key",
                  placeholder=tr("setup_key_ph"))
    st.markdown(f'<div class="fb-sub">{_masked_hint(st.session_state.user_gemini_key)}</div>',
                unsafe_allow_html=True)
    row = st.columns(2)
    if row[0].button(tr("save_key"), key="setup_save"):
        candidate = st.session_state.setup_key.strip()
        if not candidate:
            st.error(tr("err_nothing"))
        else:
            st.session_state.user_gemini_key = candidate
            st.session_state.key_verified = False
            st.toast(tr("toast_key"))
            st.rerun()
    if row[1].button(tr("test_conn"), type="primary", key="setup_test"):
        candidate = st.session_state.setup_key.strip() or st.session_state.user_gemini_key
        if not candidate:
            st.error(tr("err_no_key_test"))
        else:
            ok, message = ai.validate_api_key(candidate)
            st.session_state.key_verified = ok
            if ok:
                st.success(message)
            else:
                st.error(message)


def _collect_edits():
    return {
        "age": int(st.session_state.su_age),
        "gender": dict(sex_choices())[st.session_state.su_sex],
        "height_cm": float(st.session_state.su_height),
        "current_weight_kg": float(st.session_state.su_weight),
        "target_weight_kg": float(st.session_state.su_target_w),
        "activity_description": str(st.session_state.su_activity or "").strip(),
    }


def _biometrics_section(profile):
    st.subheader(tr("bio_h"))
    a, b = st.columns(2)
    a.number_input(tr("f_age"), 13, 90, value=int(profile.get("age") or 28), key="su_age")
    current_sex = profile.get("gender") if profile.get("gender") in ("male", "female") else "male"
    b.radio(tr("f_sex"), [label for label, _ in sex_choices()],
            index=[value for _, value in sex_choices()].index(current_sex),
            key="su_sex", horizontal=True)
    c, d = st.columns(2)
    c.number_input(tr("f_height"), 120.0, 250.0,
                   value=float(profile.get("height_cm") or 175.0),
                   step=0.5, format="%.1f", key="su_height")
    d.number_input(tr("f_weight"), 30.0, 300.0,
                   value=float(profile.get("current_weight_kg") or 80.0),
                   step=0.1, format="%.1f", key="su_weight")
    e, f = st.columns(2)
    e.number_input(tr("f_target_w"), 30.0, 300.0,
                   value=float(profile.get("target_weight_kg") or 72.0),
                   step=0.1, format="%.1f", key="su_target_w")
    f.write("")
    st.text_area(tr("f_activity"),
                 value=str(profile.get("activity_description") or ""),
                 height=70, key="su_activity")

    pending = st.session_state.pending_recalc
    row = st.columns(2)
    if row[0].button(tr("save_bio"), key="su_savebio"):
        merged = _merge_profile(profile, _collect_edits())
        database.save_profile(**merged)
        st.toast(tr("toast_bio"))
        st.rerun()
    if row[1].button(tr("recalc"), type="primary", key="su_recalc"):
        key = st.session_state.user_gemini_key
        if not key:
            st.error(tr("err_need_key"))
        else:
            edits = _collect_edits()
            merged = _merge_profile(profile, edits)
            with st.spinner(tr("spinner_recalc")):
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
                st.error(tr("err_recalc", msg=result["error"]))

    if pending:
        plan = pending["plan"]
        st.markdown(f"**{tr('proposed')}**")
        m1, m2 = st.columns(2)
        m1.metric(tr("m_tdee"), f"{plan['tdee_baseline']:.0f} kcal")
        m2.metric(tr("m_target"), f"{plan['target_calories']:.0f} kcal")
        p, c2, f3 = st.columns(3)
        p.metric(tr("m_protein"), f"{plan['protein_target_g']:.0f} g")
        c2.metric(tr("m_carbs"), f"{plan['carbs_target_g']:.0f} g")
        f3.metric(tr("m_fat"), f"{plan['fat_target_g']:.0f} g")
        if plan.get("rationale"):
            st.markdown(f'<div class="fb-quote">{plan["rationale"]}</div>',
                        unsafe_allow_html=True)
        apply_row = st.columns(2)
        if apply_row[0].button(tr("apply_targets"), type="primary", key="su_apply"):
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
            st.toast(tr("toast_targets"))
            st.rerun()
        if apply_row[1].button(tr("discard"), key="su_discard"):
            st.session_state.pending_recalc = None
            st.rerun()


def _plan_rows(base, proposed=None, accent="#22D3EE"):
    keys = [
        ("r_calories", "target_calories"),
        ("m_protein", "protein_target_g"),
        ("m_carbs", "carbs_target_g"),
        ("m_fat", "fat_target_g"),
    ]
    rows = []
    for label_key, field in keys:
        b_value = float(base.get(field) or 0)
        cell = f"<span><b>{b_value:.0f}</b></span>"
        if proposed is not None:
            p_value = float(proposed.get(field) or 0)
            delta = p_value - b_value
            sign = "+" if delta >= 0 else "\u2212"
            cell = (f"<span><b>{p_value:.0f}</b>"
                    f"<span class='fb-delta'>{sign}{abs(delta):.0f}</span></span>")
        was = (f" <small>{tr('was', v=f'{b_value:.0f}')}</small>"
               if proposed is not None else "")
        rows.append(
            f"<div class='fb-row'><span>{tr(label_key)}{was}</span>{cell}</div>"
        )
    return "".join(rows)


def _phase_section(profile):
    st.subheader(tr("phase_h"))
    tokens = build_tokens(profile)
    current = profile.get("goal_mode") or "cut"
    choices = goal_choices()
    st.radio(tr("phase_active"), [label for label, _ in choices],
             index=[value for _, value in choices].index(current),
             key="sw_mode", horizontal=True)
    selected = dict(choices)[st.session_state.sw_mode]

    if selected == current:
        st.session_state.pending_switch = None
        st.markdown(
            f"<div class='fb-quote'>{tr('already_phase', label=tokens['label'])}</div>",
            unsafe_allow_html=True,
        )
        return

    if st.button(tr("preview_switch"), type="primary", key="sw_preview"):
        tdee = profile.get("tdee_baseline")
        weight = float(profile.get("current_weight_kg") or 0)
        if not tdee or weight <= 0:
            st.warning(tr("warn_need_tdee"))
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
    guidance = tr("guide_cut") if pending["to"] == "cut" else tr("guide_bulk")
    left, right = st.columns(2)
    with left:
        st.markdown(
            f"<div class='fb-card'><h4>{tr('cur_card', m=pending['from'].upper())}</h4>"
            f"{_plan_rows(profile)}</div>",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f"<div class='fb-card' style='border-color:{target_tokens['ACCENT']};'>"
            f"<h4 style='color:{target_tokens['ACCENT']};'>"
            f"{tr('prop_card', m=pending['to'].upper())}</h4>"
            f"{_plan_rows(profile, pending['plan'])}</div>",
            unsafe_allow_html=True,
        )
    st.markdown(f'<div class="fb-quote">{tr("guided", g=guidance)}</div>',
                unsafe_allow_html=True)

    confirm_row = st.columns(2)
    if confirm_row[0].button(tr("confirm_switch"), type="primary",
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
        st.toast(tr("toast_switch", label=target_tokens["label"]))
        st.rerun()
    if confirm_row[1].button(tr("cancel"), key="sw_cancel"):
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

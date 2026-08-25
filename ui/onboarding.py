import streamlit as st

import ai
import database
from ui.i18n import goal_choices, sex_choices, tr
from ui.state import clear_onboarding_state


def _card_open(title, subtitle=""):
    st.markdown(
        f'<div class="fb-card"><h4>{title}</h4>'
        f'<div class="fb-sub">{subtitle}</div></div>',
        unsafe_allow_html=True,
    )


def _step1_key():
    _card_open(tr("ob_key_card"), tr("ob_key_sub"))
    st.text_input(tr("ob_key_label"), type="password", key="ob_key",
                  placeholder=tr("ob_key_ph"))
    st.markdown(f'<div class="fb-sub">{tr("ob_key_hint")}</div>',
                unsafe_allow_html=True)
    if st.button(tr("ob_validate"), type="primary", key="ob_validate"):
        candidate = st.session_state.ob_key.strip()
        if not candidate:
            st.error(tr("err_key_empty"))
            return
        ok, message = ai.validate_api_key(candidate)
        if not ok:
            st.error(tr("err_key_rejected", msg=message))
            return
        st.session_state.user_gemini_key = candidate
        st.session_state.key_verified = True
        st.session_state.ob_step = 2
        st.rerun()


def _radio_choice(widget_key, label_key, choices, current_value):
    index = [value for _, value in choices].index(current_value)
    picked = st.radio(tr(label_key), [label for label, _ in choices],
                      index=index, key=widget_key, horizontal=True)
    return dict(choices)[picked]


def _step2_goal():
    _card_open(tr("ob_phase_card"), tr("ob_phase_sub"))
    mode = _radio_choice("ob_goal", "ob_phase_card", goal_choices(),
                         st.session_state.ob_goal_mode)
    row = st.columns(2)
    if row[0].button(tr("btn_back"), key="ob_back2"):
        st.session_state.ob_step = 1
        st.rerun()
    if row[1].button(tr("btn_continue"), type="primary", key="ob_next2"):
        st.session_state.ob_goal_mode = mode
        st.session_state.ob_step = 3
        st.rerun()


def _step3_biometrics():
    _card_open(tr("ob_bio_card"), tr("ob_bio_sub"))
    a, b = st.columns(2)
    a.number_input(tr("f_age"), 13, 90, value=28, key="ob_age")
    b.radio(tr("f_sex"), [label for label, _ in sex_choices()],
            index=0 if st.session_state.get("ob_sex") in (None, "Male") else 1,
            key="ob_sex", horizontal=True)
    c, d = st.columns(2)
    c.number_input(tr("f_height"), 120.0, 250.0, value=175.0, step=0.5,
                   format="%.1f", key="ob_height")
    d.number_input(tr("f_weight"), 30.0, 300.0, value=80.0, step=0.1,
                   format="%.1f", key="ob_weight")
    e, f = st.columns(2)
    e.number_input(tr("f_target_w"), 30.0, 300.0, value=72.0, step=0.1,
                   format="%.1f", key="ob_target_w")
    f.write("")
    st.text_area(tr("f_activity"), key="ob_activity",
                 placeholder=tr("f_activity_ph"), height=70)
    row = st.columns(2)
    if row[0].button(tr("btn_back"), key="ob_back3"):
        st.session_state.ob_step = 2
        st.rerun()
    if row[1].button(tr("btn_continue"), type="primary", key="ob_next3"):
        bio = {
            "age": int(st.session_state.ob_age),
            "gender": dict(sex_choices())[st.session_state.ob_sex],
            "height_cm": float(st.session_state.ob_height),
            "current_weight_kg": float(st.session_state.ob_weight),
            "target_weight_kg": float(st.session_state.ob_target_w),
            "activity_description": str(st.session_state.ob_activity or "").strip(),
        }
        if not bio["activity_description"]:
            st.error(tr("err_activity"))
            return
        if bio["target_weight_kg"] >= bio["current_weight_kg"] and \
                st.session_state.ob_goal_mode == "cut":
            st.warning(tr("warn_cut_target"))
        st.session_state.ob_bio = bio
        st.session_state.ob_plan = None
        st.session_state.ob_step = 4
        st.rerun()


def _step4_preview():
    bio = st.session_state.ob_bio
    if not bio:
        st.session_state.ob_step = 3
        st.rerun()
        return
    mode = st.session_state.ob_goal_mode
    plan = st.session_state.ob_plan
    if plan is None:
        if st.button(tr("ob_run"), type="primary", key="ob_run"):
            with st.spinner(tr("spinner_estimate")):
                result = ai.estimate_plan(
                    st.session_state.user_gemini_key,
                    bio["age"], bio["gender"], bio["height_cm"],
                    bio["current_weight_kg"], bio["activity_description"],
                    mode,
                )
            if result["ok"]:
                st.session_state.ob_plan = result["plan"]
                st.rerun()
            else:
                st.error(tr("err_estimate", msg=result["error"]))
        row = st.columns(2)
        if row[0].button(tr("btn_back"), key="ob_back4"):
            st.session_state.ob_step = 3
            st.rerun()
        return

    m1, m2 = st.columns(2)
    m1.metric(tr("m_tdee"), f"{plan['tdee_baseline']:.0f} kcal")
    delta = -400 if mode == "cut" else 350
    m2.metric(tr("m_target"), f"{plan['target_calories']:.0f} kcal",
              delta=f"{delta:+d}")
    p, c, f_ = st.columns(3)
    p.metric(tr("m_protein"), f"{plan['protein_target_g']:.0f} g")
    c.metric(tr("m_carbs"), f"{plan['carbs_target_g']:.0f} g")
    f_.metric(tr("m_fat"), f"{plan['fat_target_g']:.0f} g")
    if plan.get("rationale"):
        st.markdown(f'<div class="fb-quote">{plan["rationale"]}</div>',
                    unsafe_allow_html=True)

    with st.expander(tr("ob_tune")):
        g1, g2 = st.columns(2)
        plan["target_calories"] = float(g1.number_input(
            tr("f_cal"), 1000.0, 6000.0, value=float(plan["target_calories"]),
            step=10.0, format="%.0f", key="ob_ft_cal"))
        plan["protein_target_g"] = float(g2.number_input(
            tr("f_protein_g"), 20.0, 400.0, value=float(plan["protein_target_g"]),
            step=1.0, format="%.0f", key="ob_ft_p"))
        h1, h2 = st.columns(2)
        plan["carbs_target_g"] = float(h1.number_input(
            tr("f_carbs_g"), 0.0, 800.0, value=float(plan["carbs_target_g"]),
            step=5.0, format="%.0f", key="ob_ft_c"))
        plan["fat_target_g"] = float(h2.number_input(
            tr("f_fat_g"), 10.0, 300.0, value=float(plan["fat_target_g"]),
            step=1.0, format="%.0f", key="ob_ft_f"))

    if st.button(tr("ob_save"), type="primary", key="ob_save"):
        database.save_profile(
            age=bio["age"],
            gender=bio["gender"],
            height_cm=bio["height_cm"],
            current_weight_kg=bio["current_weight_kg"],
            target_weight_kg=bio["target_weight_kg"],
            activity_description=bio["activity_description"],
            goal_mode=mode,
            tdee_baseline=float(plan["tdee_baseline"]),
            target_calories=float(plan["target_calories"]),
            protein_target_g=float(plan["protein_target_g"]),
            carbs_target_g=float(plan["carbs_target_g"]),
            fat_target_g=float(plan["fat_target_g"]),
        )
        clear_onboarding_state()
        st.toast(tr("toast_initialized"))
        st.rerun()


def render_onboarding():
    step = int(st.session_state.ob_step)
    title = tr(f"ob_s{step}_title")
    st.progress(step / 4, text=tr("ob_step_of", step=step, title=title))
    {1: _step1_key, 2: _step2_goal, 3: _step3_biometrics, 4: _step4_preview}[step]()

import streamlit as st

import ai
import database
from ui.state import clear_onboarding_state

GOAL_LABELS = {"Fat Loss (Cut)": "cut", "Fat Gain (Bulk)": "bulk"}
SEX_LABELS = {"Male": "male", "Female": "female"}

STEP_TITLES = {
    1: "Connect your Gemini engine",
    2: "Choose your phase",
    3: "Your biometrics",
    4: "Engine preview",
}


def _card_open(title, subtitle=""):
    st.markdown(
        f'<div class="fb-card"><h4>{title}</h4>'
        f'<div class="fb-sub">{subtitle}</div></div>',
        unsafe_allow_html=True,
    )


def _step1_key():
    _card_open("Gemini API key", "Bring your own key from Google AI Studio. Stored only in this session.")
    st.text_input("Gemini API key", type="password", key="ob_key",
                  placeholder="Paste your key here")
    st.markdown('<div class="fb-sub">Free keys: aistudio.google.com/apikey</div>',
                unsafe_allow_html=True)
    if st.button("Validate & Continue", type="primary", key="ob_validate"):
        candidate = st.session_state.ob_key.strip()
        if not candidate:
            st.error("Enter an API key to continue.")
            return
        ok, message = ai.validate_api_key(candidate)
        if not ok:
            st.error(f"Key rejected: {message}")
            return
        st.session_state.user_gemini_key = candidate
        st.session_state.key_verified = True
        st.session_state.ob_step = 2
        st.rerun()


def _step2_goal():
    _card_open("Active phase", "Drives calorie targets, macro split and app accent.")
    st.radio("Goal phase", list(GOAL_LABELS), key="ob_goal",
             index=0 if st.session_state.ob_goal_mode == "cut" else 1,
             horizontal=True)
    row = st.columns(2)
    if row[0].button("Back", key="ob_back2"):
        st.session_state.ob_step = 1
        st.rerun()
    if row[1].button("Continue", type="primary", key="ob_next2"):
        st.session_state.ob_goal_mode = GOAL_LABELS[st.session_state.ob_goal]
        st.session_state.ob_step = 3
        st.rerun()


def _step3_biometrics():
    _card_open("Biometrics", "Used for TDEE estimation and macro math.")
    a, b = st.columns(2)
    a.number_input("Age", 13, 90, value=28, key="ob_age")
    b.radio("Biological sex", list(SEX_LABELS), key="ob_sex", horizontal=True)
    c, d = st.columns(2)
    c.number_input("Height (cm)", 120.0, 250.0, value=175.0, step=0.5,
                   format="%.1f", key="ob_height")
    d.number_input("Current weight (kg)", 30.0, 300.0, value=80.0, step=0.1,
                   format="%.1f", key="ob_weight")
    e, f = st.columns(2)
    e.number_input("Target weight (kg)", 30.0, 300.0, value=72.0, step=0.1,
                   format="%.1f", key="ob_target_w")
    f.write("")
    st.text_area("Daily activity in your own words", key="ob_activity",
                 placeholder="e.g. desk job, gym 4x per week, weekend cycling",
                 height=70)
    row = st.columns(2)
    if row[0].button("Back", key="ob_back3"):
        st.session_state.ob_step = 2
        st.rerun()
    if row[1].button("Continue", type="primary", key="ob_next3"):
        bio = {
            "age": int(st.session_state.ob_age),
            "gender": SEX_LABELS[st.session_state.ob_sex],
            "height_cm": float(st.session_state.ob_height),
            "current_weight_kg": float(st.session_state.ob_weight),
            "target_weight_kg": float(st.session_state.ob_target_w),
            "activity_description": str(st.session_state.ob_activity or "").strip(),
        }
        if not bio["activity_description"]:
            st.error("Describe your daily activity so the AI can calibrate TDEE.")
            return
        if bio["target_weight_kg"] >= bio["current_weight_kg"] and \
                st.session_state.ob_goal_mode == "cut":
            st.warning("Target weight is above current weight while cutting — double-check on the next step.")
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
        if st.button("Run AI Estimation", type="primary", key="ob_run"):
            with st.spinner("Estimating your engine targets..."):
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
                st.error(f"Estimation failed: {result['error']}")
        row = st.columns(2)
        if row[0].button("Back", key="ob_back4"):
            st.session_state.ob_step = 3
            st.rerun()
        return

    m1, m2 = st.columns(2)
    m1.metric("Baseline TDEE", f"{plan['tdee_baseline']:.0f} kcal")
    delta = -400 if mode == "cut" else 350
    m2.metric("Daily Target", f"{plan['target_calories']:.0f} kcal",
              delta=f"{delta:+d}")
    p, c, f_ = st.columns(3)
    p.metric("Protein", f"{plan['protein_target_g']:.0f} g")
    c.metric("Carbs", f"{plan['carbs_target_g']:.0f} g")
    f_.metric("Fat", f"{plan['fat_target_g']:.0f} g")
    if plan.get("rationale"):
        st.markdown(f'<div class="fb-quote">{plan["rationale"]}</div>',
                    unsafe_allow_html=True)

    with st.expander("Fine-tune before saving"):
        g1, g2 = st.columns(2)
        plan["target_calories"] = float(g1.number_input(
            "Calories", 1000.0, 6000.0, value=float(plan["target_calories"]),
            step=10.0, format="%.0f", key="ob_ft_cal"))
        plan["protein_target_g"] = float(g2.number_input(
            "Protein g", 20.0, 400.0, value=float(plan["protein_target_g"]),
            step=1.0, format="%.0f", key="ob_ft_p"))
        h1, h2 = st.columns(2)
        plan["carbs_target_g"] = float(h1.number_input(
            "Carbs g", 0.0, 800.0, value=float(plan["carbs_target_g"]),
            step=5.0, format="%.0f", key="ob_ft_c"))
        plan["fat_target_g"] = float(h2.number_input(
            "Fat g", 10.0, 300.0, value=float(plan["fat_target_g"]),
            step=1.0, format="%.0f", key="ob_ft_f"))

    if st.button("Save & Initialize Engine", type="primary", key="ob_save"):
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
        st.toast("Engine initialized. Welcome aboard.")
        st.rerun()


def render_onboarding():
    step = int(st.session_state.ob_step)
    st.progress(step / 4, text=f"Step {step} of 4 — {STEP_TITLES[step]}")
    {1: _step1_key, 2: _step2_goal, 3: _step3_biometrics, 4: _step4_preview}[step]()

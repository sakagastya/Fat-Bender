import streamlit as st

import ai
import database
from ui.dial import build_dial
from ui.styles import build_tokens

PACE_SPLITS = [("Breakfast", 0.25), ("Lunch", 0.40), ("Dinner", 0.35)]


def _date_navigation():
    import datetime

    chosen = st.date_input(
        "Viewing date",
        value=datetime.date.fromisoformat(st.session_state.active_date),
        key="nav_date",
        format="YYYY-MM-DD",
    )
    st.session_state.active_date = chosen.isoformat()


def _weigh_banner(day):
    entry = database.get_weight_for_date(day)
    if entry:
        avg = entry.get("rolling_avg_7d")
        avg_text = f" · 7-day avg {avg:.1f} kg" if avg else ""
        st.markdown(
            f'<div class="fb-pill">Scale Weight ({day}): '
            f"<b>{entry['weight_kg']:.1f} kg</b>{avg_text}</div>",
            unsafe_allow_html=True,
        )
        return
    with st.expander("⚖️ Log Today's Weight"):
        st.number_input("Bodyweight (kg)", 30.0, 300.0, step=0.1,
                        format="%.1f", key=f"wi_weight_{day}")
        if st.button("Save Weigh-in", type="primary", key=f"wi_save_{day}"):
            value = float(st.session_state[f"wi_weight_{day}"])
            rolling = database.log_weight(value, day)
            note = f" · 7-day avg {rolling:.2f} kg" if rolling else ""
            st.toast(f"Weigh-in saved{note}")
            st.rerun()


def _hero_dial(profile, tokens, total, meals):
    html = build_dial(
        tokens["goal_mode"],
        total,
        profile.get("target_calories"),
        sum(m["protein_g"] for m in meals), profile.get("protein_target_g"),
        sum(m["carbs_g"] for m in meals), profile.get("carbs_target_g"),
        sum(m["fat_g"] for m in meals), profile.get("fat_target_g"),
        maintenance=profile.get("tdee_baseline"),
    )
    st.html(html)


def _pacing_card(profile):
    target = float(profile.get("target_calories") or 0)
    rows = "".join(
        f"<div class='fb-row'><span>{label}</span>"
        f"<b>~{round(target * pct / 10) * 10 if target else '—'} kcal</b></div>"
        for label, pct in PACE_SPLITS
    )
    hint = ("Suggested meal pacing to spread today's target evenly."
            if target else "Set your targets via the AI planner to unlock pacing.")
    st.markdown(
        f'<div class="fb-card"><h4>Fresh Day · Pacing Roadmap</h4>{rows}'
        f"<div class='fb-sub' style='margin-top:8px;'>{hint}</div></div>",
        unsafe_allow_html=True,
    )


def _analyze_meal():
    description = str(st.session_state.nl_meal or "").strip()
    if not description:
        st.warning("Describe what you ate before analyzing.")
        return
    with st.spinner("Analyzing meal..."):
        result = ai.parse_meal(st.session_state.user_gemini_key, description)
    buffer = result["meal"]
    buffer["meta"] = {"error": None if result["ok"] else result["error"]}
    st.session_state.meal_review_buffer = buffer
    st.session_state.review_gen += 1
    st.session_state.confirm_delete_id = None
    st.rerun()


def _refine_meal(buffer, gen):
    instruction = str(st.session_state[f"rv_refine_{gen}"] or "").strip()
    if not instruction:
        st.warning("Tell the coach what to change, e.g. 'ganti ke 2 centong nasi'.")
        return
    with st.spinner("Refining..."):
        result = ai.refine_meal(
            st.session_state.user_gemini_key,
            {"title": buffer["title"], "items": buffer["items"],
             "totals": buffer["totals"]},
            instruction,
        )
    updated = result["meal"]
    updated["meta"] = {"error": None if result["ok"] else result["error"]}
    st.session_state.meal_review_buffer = updated
    st.session_state.review_gen += 1
    st.rerun()


def _review_card(profile, day):
    buffer = st.session_state.meal_review_buffer
    if not buffer:
        return
    gen = int(st.session_state.review_gen)
    meta_error = (buffer.get("meta") or {}).get("error")
    if meta_error:
        st.warning(f"AI parsing unavailable — enter macros manually. ({meta_error[:140]})")

    title = buffer["title"] or "Manual entry"
    item_rows = "".join(
        f"<div class='fb-row'><span>{item['name']}"
        + (f" <small>({item['portion']})</small>" if item["portion"] else "")
        + f"</span><b>{item['calories']:.0f} kcal"
        + f" <small>P{item['protein_g']:.0f} C{item['carbs_g']:.0f} F{item['fat_g']:.0f}</small></b></div>"
        for item in buffer["items"]
    ) or "<div class='fb-sub'>No AI items — fill the numbers below.</div>"
    st.markdown(
        f"<div class='fb-card'><h4>AI Review · {title}</h4>{item_rows}</div>",
        unsafe_allow_html=True,
    )

    r_col, b_col = st.columns([3, 1])
    r_col.text_input("Refine meal", key=f"rv_refine_{gen}",
                     placeholder="ganti ke 2 centong nasi atau kurangi minyak",
                     label_visibility="collapsed")
    if b_col.button("Refine", key=f"rv_refine_btn_{gen}"):
        _refine_meal(buffer, gen)

    totals = buffer["totals"]
    a1, a2 = st.columns(2)
    manual_cal = a1.number_input("Calories", 0.0, 5000.0,
                                 value=float(totals.get("calories") or 0),
                                 step=5.0, format="%.0f", key=f"rv_cal_{gen}")
    manual_p = a2.number_input("Protein g", 0.0, 400.0,
                               value=float(totals.get("protein_g") or 0),
                               step=1.0, format="%.0f", key=f"rv_p_{gen}")
    b1, b2 = st.columns(2)
    manual_c = b1.number_input("Carbs g", 0.0, 800.0,
                               value=float(totals.get("carbs_g") or 0),
                               step=1.0, format="%.0f", key=f"rv_c_{gen}")
    manual_f = b2.number_input("Fat g", 0.0, 300.0,
                               value=float(totals.get("fat_g") or 0),
                               step=1.0, format="%.0f", key=f"rv_f_{gen}")

    row = st.columns(2)
    if row[0].button("Confirm & Log", type="primary", key=f"rv_confirm_{gen}"):
        database.add_meal(
            day,
            title,
            buffer["items"],
            total_calories=float(manual_cal),
            protein_g=float(manual_p),
            carbs_g=float(manual_c),
            fat_g=float(manual_f),
        )
        st.session_state.meal_review_buffer = None
        st.session_state.nl_reset = True
        st.toast("Meal logged.")
        st.rerun()
    if row[1].button("Discard", key=f"rv_discard_{gen}"):
        st.session_state.meal_review_buffer = None
        st.rerun()


def _meal_intake_section(profile, day):
    st.subheader("Log a Meal")
    st.text_area(
        "What did you eat?",
        key="nl_meal",
        height=80,
        placeholder=("1 porsi nasi padang ayam bakar dada, "
                     "1 sdm sambal terasi, 2 keping kerupuk"),
    )
    if st.button("Analyze Meal", type="primary", key="analyze_btn"):
        _analyze_meal()
    _review_card(profile, day)


def _delete_flow(meal_id):
    if st.session_state.confirm_delete_id == meal_id:
        st.warning("Remove this meal permanently?")
        yes, no = st.columns(2)
        if yes.button("Yes, delete", type="primary", key=f"delyes_{meal_id}"):
            database.delete_meal(meal_id)
            st.session_state.confirm_delete_id = None
            st.toast("Meal removed.")
            st.rerun()
        if no.button("Keep it", key=f"delno_{meal_id}"):
            st.session_state.confirm_delete_id = None
            st.rerun()
    else:
        if st.button("🗑️ Delete meal", key=f"del_{meal_id}"):
            st.session_state.confirm_delete_id = meal_id
            st.rerun()


def _meal_feed(meals):
    st.subheader(f"Timeline · {len(meals)} meal{'s' if len(meals) != 1 else ''}")
    for meal in meals:
        mid = meal["id"]
        timestamp = (meal["logged_at"] or "")[11:16]
        header = f"{meal['meal_name']} · {meal['total_calories']:.0f} kcal"
        with st.expander(header):
            st.markdown(f'<div class="fb-sub">Logged at {timestamp} · {meal["date"]}</div>',
                        unsafe_allow_html=True)
            badges = (
                f"<span class='fb-badge'>{meal['total_calories']:.0f} kcal</span>"
                f"<span class='fb-badge'>P {meal['protein_g']:.0f}g</span>"
                f"<span class='fb-badge'>C {meal['carbs_g']:.0f}g</span>"
                f"<span class='fb-badge'>F {meal['fat_g']:.0f}g</span>"
            )
            st.markdown(badges, unsafe_allow_html=True)
            rows = "".join(
                f"<div class='fb-row'><span>{item['name']}"
                + (f" <small>({item['portion']})</small>" if item["portion"] else "")
                + f"</span><b>{item['calories']:.0f} kcal</b></div>"
                for item in meal["items"]
            ) or "<div class='fb-sub'>Manually logged — no itemized breakdown.</div>"
            st.markdown(f"<div class='fb-card'>{rows}</div>", unsafe_allow_html=True)
            _delete_flow(mid)


def render_today(profile):
    if not profile:
        return
    if st.session_state.pop("nl_reset", False):
        st.session_state.nl_meal = ""
    tokens = build_tokens(profile)
    _date_navigation()
    day = st.session_state.active_date
    _weigh_banner(day)
    total = database.get_daily_total(day)
    meals = database.get_meals_for_date(day)
    _hero_dial(profile, tokens, total, meals)
    _meal_intake_section(profile, day)
    if not meals:
        _pacing_card(profile)
    _meal_feed(meals)

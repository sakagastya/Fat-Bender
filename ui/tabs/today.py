import streamlit as st

import ai
import database
from ui.dial import build_dial
from ui.i18n import tr
from ui.styles import build_tokens

PACE_SPLITS = [("pace_b", 0.25), ("pace_l", 0.40), ("pace_d", 0.35)]


def _date_navigation():
    import datetime

    chosen = st.date_input(
        tr("viewing_date"),
        value=datetime.date.fromisoformat(st.session_state.active_date),
        key="nav_date",
        format="YYYY-MM-DD",
    )
    st.session_state.active_date = chosen.isoformat()


def _weigh_banner(day):
    entry = database.get_weight_for_date(day)
    if entry:
        avg = entry.get("rolling_avg_7d")
        avg_text = tr("avg_short", avg=f"{avg:.1f}") if avg else ""
        st.markdown(
            f'<div class="fb-pill">{tr("pill_scale", day=day)}'
            f"<b>{entry['weight_kg']:.1f} kg</b>{avg_text}</div>",
            unsafe_allow_html=True,
        )
        return
    with st.expander(tr("weigh_cta")):
        st.number_input(tr("f_bodyweight"), 30.0, 300.0, step=0.1,
                        format="%.1f", key=f"wi_weight_{day}")
        if st.button(tr("weigh_save"), type="primary", key=f"wi_save_{day}"):
            value = float(st.session_state[f"wi_weight_{day}"])
            rolling = database.log_weight(value, day)
            note = tr("avg_short", avg=f"{rolling:.2f}") if rolling else ""
            st.toast(tr("toast_weigh", avg=note))
            st.rerun()


def _dial_labels():
    return {
        "remaining": tr("dial_remaining"),
        "needed": tr("dial_needed"),
        "cut_in": tr("dial_cut_in"),
        "cut_over": tr("dial_cut_over"),
        "bulk_ok": tr("dial_bulk_ok"),
        "bulk_low": tr("dial_bulk_low"),
        "protein": tr("m_protein"),
        "carbs": tr("m_carbs"),
        "fat": tr("m_fat"),
    }


def _hero_dial(profile, tokens, total, meals):
    html = build_dial(
        tokens["goal_mode"],
        total,
        profile.get("target_calories"),
        sum(m["protein_g"] for m in meals), profile.get("protein_target_g"),
        sum(m["carbs_g"] for m in meals), profile.get("carbs_target_g"),
        sum(m["fat_g"] for m in meals), profile.get("fat_target_g"),
        maintenance=profile.get("tdee_baseline"),
        labels=_dial_labels(),
    )
    st.html(html)


def _pacing_card(profile):
    target = float(profile.get("target_calories") or 0)
    rows = "".join(
        f"<div class='fb-row'><span>{tr(key)}</span>"
        f"<b>~{round(target * pct / 10) * 10 if target else '—'} kcal</b></div>"
        for key, pct in PACE_SPLITS
    )
    hint = tr("pace_hint") if target else tr("pace_hint0")
    st.markdown(
        f'<div class="fb-card"><h4>{tr("pacing_title")}</h4>{rows}'
        f"<div class='fb-sub' style='margin-top:8px;'>{hint}</div></div>",
        unsafe_allow_html=True,
    )


def _analyze_meal():
    description = str(st.session_state.nl_meal or "").strip()
    if not description:
        st.warning(tr("warn_meal_empty"))
        return
    with st.spinner(tr("spinner_parse")):
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
        st.warning(tr("warn_refine_empty"))
        return
    with st.spinner(tr("spinner_refine")):
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
        st.warning(tr("warn_ai_fail", msg=meta_error[:140]))

    title = buffer["title"] or tr("manual_entry")
    item_rows = "".join(
        f"<div class='fb-row'><span>{item['name']}"
        + (f" <small>({item['portion']})</small>" if item["portion"] else "")
        + f"</span><b>{item['calories']:.0f} kcal"
        + f" <small>P{item['protein_g']:.0f} C{item['carbs_g']:.0f} F{item['fat_g']:.0f}</small></b></div>"
        for item in buffer["items"]
    ) or f"<div class='fb-sub'>{tr('no_items')}</div>"
    st.markdown(
        f"<div class='fb-card'><h4>{tr('review_title', title=title)}</h4>{item_rows}</div>",
        unsafe_allow_html=True,
    )

    r_col, b_col = st.columns([3, 1])
    r_col.text_input(tr("refine_label"), key=f"rv_refine_{gen}",
                     placeholder=tr("refine_ph"),
                     label_visibility="collapsed")
    if b_col.button(tr("refine_btn"), key=f"rv_refine_btn_{gen}"):
        _refine_meal(buffer, gen)

    totals = buffer["totals"]
    a1, a2 = st.columns(2)
    manual_cal = a1.number_input(tr("f_cal"), 0.0, 5000.0,
                                 value=float(totals.get("calories") or 0),
                                 step=5.0, format="%.0f", key=f"rv_cal_{gen}")
    manual_p = a2.number_input(tr("f_protein_g"), 0.0, 400.0,
                               value=float(totals.get("protein_g") or 0),
                               step=1.0, format="%.0f", key=f"rv_p_{gen}")
    b1, b2 = st.columns(2)
    manual_c = b1.number_input(tr("f_carbs_g"), 0.0, 800.0,
                               value=float(totals.get("carbs_g") or 0),
                               step=1.0, format="%.0f", key=f"rv_c_{gen}")
    manual_f = b2.number_input(tr("f_fat_g"), 0.0, 300.0,
                               value=float(totals.get("fat_g") or 0),
                               step=1.0, format="%.0f", key=f"rv_f_{gen}")

    row = st.columns(2)
    if row[0].button(tr("confirm_log"), type="primary", key=f"rv_confirm_{gen}"):
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
        st.toast(tr("toast_meal"))
        st.rerun()
    if row[1].button(tr("discard"), key=f"rv_discard_{gen}"):
        st.session_state.meal_review_buffer = None
        st.rerun()


def _meal_intake_section(profile, day):
    st.subheader(tr("log_meal_h"))
    st.text_area(
        tr("meal_label"),
        key="nl_meal",
        height=80,
        placeholder=tr("meal_ph"),
    )
    if st.button(tr("analyze"), type="primary", key="analyze_btn"):
        _analyze_meal()
    _review_card(profile, day)


def _delete_flow(meal_id):
    if st.session_state.confirm_delete_id == meal_id:
        st.warning(tr("del_confirm"))
        yes, no = st.columns(2)
        if yes.button(tr("del_yes"), type="primary", key=f"delyes_{meal_id}"):
            database.delete_meal(meal_id)
            st.session_state.confirm_delete_id = None
            st.toast(tr("toast_deleted"))
            st.rerun()
        if no.button(tr("del_no"), key=f"delno_{meal_id}"):
            st.session_state.confirm_delete_id = None
            st.rerun()
    else:
        if st.button(tr("del_meal"), key=f"del_{meal_id}"):
            st.session_state.confirm_delete_id = meal_id
            st.rerun()


def _meal_feed(meals):
    suffix = "" if len(meals) == 1 else "s"
    st.subheader(tr("timeline_h", n=len(meals), s=suffix))
    for meal in meals:
        mid = meal["id"]
        timestamp = (meal["logged_at"] or "")[11:16]
        header = f"{meal['meal_name']} · {meal['total_calories']:.0f} kcal"
        with st.expander(header):
            st.markdown(
                f"<div class='fb-sub'>{tr('logged_at', t=timestamp, d=meal['date'])}</div>",
                unsafe_allow_html=True,
            )
            badges = (
                f"<span class='fb-badge'>{meal['total_calories']:.0f} kcal</span>"
                f"<span class='fb-badge'>{tr('m_protein')} {meal['protein_g']:.0f}g</span>"
                f"<span class='fb-badge'>{tr('m_carbs')} {meal['carbs_g']:.0f}g</span>"
                f"<span class='fb-badge'>{tr('m_fat')} {meal['fat_g']:.0f}g</span>"
            )
            st.markdown(badges, unsafe_allow_html=True)
            rows = "".join(
                f"<div class='fb-row'><span>{item['name']}"
                + (f" <small>({item['portion']})</small>" if item["portion"] else "")
                + f"</span><b>{item['calories']:.0f} kcal</b></div>"
                for item in meal["items"]
            ) or "<div class='fb-sub'>—</div>"
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

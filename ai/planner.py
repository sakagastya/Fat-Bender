from .generation import request_json
from .prompts import PLANNER_SYSTEM, build_planner_prompt
from .schemas import zero_plan

TDEE_RANGE = (800.0, 6000.0)
CALORIE_FLOOR = 1200.0
GOAL_ADJUSTMENT = {"cut": -400.0, "bulk": 350.0}
PROTEIN_PER_KG = {"cut": 2.2, "bulk": 1.8}
FAT_SHARE_OF_REMAINDER = {"cut": 0.30, "bulk": 0.20}


def calibrate_plan(tdee_baseline, base_target, adjustment, weight_kg, goal_mode):
    mode = str(goal_mode).lower()
    if mode not in GOAL_ADJUSTMENT:
        raise ValueError("goal_mode must be 'cut' or 'bulk'")
    tdee = float(tdee_baseline)
    weight = float(weight_kg)
    target = max(float(base_target) + float(adjustment), CALORIE_FLOOR)
    protein = round(PROTEIN_PER_KG[mode] * weight)
    remaining = max(target - protein * 4.0, 0.0)
    fat = round(remaining * FAT_SHARE_OF_REMAINDER[mode] / 9.0)
    carbs = round(max(remaining - fat * 9.0, 0.0) / 4.0)
    return {
        "tdee_baseline": round(tdee, 1),
        "target_calories": round(target, 1),
        "protein_target_g": float(protein),
        "carbs_target_g": float(carbs),
        "fat_target_g": float(fat),
    }


def compute_plan(tdee, weight_kg, goal_mode):
    mode = str(goal_mode).lower()
    if mode not in GOAL_ADJUSTMENT:
        raise ValueError("goal_mode must be 'cut' or 'bulk'")
    tdee_f = float(tdee)
    return calibrate_plan(tdee_f, tdee_f, GOAL_ADJUSTMENT[mode], weight_kg, mode)


def _template_rationale(plan, goal_mode):
    direction = "deficit" if goal_mode == "cut" else "surplus"
    adjustment = abs(GOAL_ADJUSTMENT[goal_mode])
    return (
        f"TDEE estimated at {plan['tdee_baseline']:.0f} kcal with a {adjustment:.0f} kcal "
        f"{direction} applied for your {'cut' if goal_mode == 'cut' else 'bulk'} phase. "
        f"Protein is set to {plan['protein_target_g']:.0f} g per day to match this goal."
    )


def estimate_plan(api_key, age, gender, height_cm, weight_kg,
                  activity_description, goal_mode):
    mode = str(goal_mode or "").lower()
    if mode not in GOAL_ADJUSTMENT:
        return {"ok": False, "plan": zero_plan(), "error": "Active goal mode must be 'cut' or 'bulk'."}
    try:
        weight = float(weight_kg)
    except (TypeError, ValueError):
        weight = 0.0
    if weight <= 0:
        return {"ok": False, "plan": zero_plan(), "error": "Current bodyweight is required."}
    key = (api_key or "").strip()
    if not key:
        return {"ok": False, "plan": zero_plan(), "error": "Gemini API key is required."}
    prompt = build_planner_prompt(age, gender, height_cm, weight,
                                  activity_description, mode)
    data, error = request_json(key, system=PLANNER_SYSTEM, prompt=prompt,
                               temperature=0.2, max_output_tokens=400)
    if data is None:
        return {"ok": False, "plan": zero_plan(), "error": error}
    try:
        tdee = float(data.get("tdee_kcal"))
    except (TypeError, ValueError):
        return {"ok": False, "plan": zero_plan(), "error": "AI returned an unusable TDEE value."}
    if not TDEE_RANGE[0] <= tdee <= TDEE_RANGE[1]:
        return {"ok": False, "plan": zero_plan(), "error": "AI returned a TDEE outside a plausible range."}
    plan = compute_plan(tdee, weight, mode)
    rationale = str(data.get("rationale") or "").strip()
    plan["rationale"] = rationale[:320] if rationale else _template_rationale(plan, mode)
    return {"ok": True, "plan": plan, "error": None}

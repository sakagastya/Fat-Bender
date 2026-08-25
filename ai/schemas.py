TOTAL_KEYS = ("calories", "protein_g", "carbs_g", "fat_g")

NUMBER_ALIASES = {
    "calories": ("calories", "kcal", "cal"),
    "protein_g": ("protein_g", "protein"),
    "carbs_g": ("carbs_g", "carbs", "carbohydrates"),
    "fat_g": ("fat_g", "fat"),
}

PLAN_NUMBER_KEYS = ("tdee_baseline", "target_calories", "protein_target_g",
                    "carbs_target_g", "fat_target_g")


def _number(source, canonical):
    for key in NUMBER_ALIASES[canonical]:
        if key in source:
            try:
                return max(float(source[key]), 0.0)
            except (TypeError, ValueError):
                continue
    return 0.0


def zero_meal():
    return {"title": "", "items": [], "totals": {key: 0.0 for key in TOTAL_KEYS}}


def zero_plan():
    plan = {key: 0.0 for key in PLAN_NUMBER_KEYS}
    plan["rationale"] = ""
    return plan


def normalize_item(raw):
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or raw.get("item") or raw.get("component") or "").strip()
    if not name:
        return None
    portion = str(raw.get("portion") or raw.get("amount") or raw.get("size") or "").strip()
    item = {"name": name[:120], "portion": portion[:80]}
    item.update({key: round(_number(raw, key), 1) for key in TOTAL_KEYS})
    return item


def compute_totals(items):
    return {key: round(sum(item[key] for item in items), 1) for key in TOTAL_KEYS}


def normalize_meal(raw):
    if not isinstance(raw, dict):
        return zero_meal()
    title = str(raw.get("title") or raw.get("meal_name") or raw.get("name") or "").strip()[:160]
    entries = raw.get("items")
    entries = entries if isinstance(entries, list) else []
    items = [item for item in (normalize_item(entry) for entry in entries) if item]
    if not items:
        raw_totals = raw.get("totals") if isinstance(raw.get("totals"), dict) else {}
        recovered = {key: _number(raw_totals, key) for key in TOTAL_KEYS}
        if any(value > 0 for value in recovered.values()):
            items = [{
                "name": title or "Unspecified item",
                "portion": "",
                **{key: round(recovered[key], 1) for key in TOTAL_KEYS},
            }]
    items = items[:50]
    return {"title": title, "items": items, "totals": compute_totals(items)}

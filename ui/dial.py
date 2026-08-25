import math

PALETTES = {
    "cut": {
        "calories": "#00F2FE",
        "protein": "#8B5CFF",
        "cf": "#93A5BE",
        "glow": "rgba(0,242,254,0.45)",
        "off_glow": "rgba(255,107,107,0.60)",
        "off_color": "#FF6B6B",
    },
    "bulk": {
        "calories": "#FF9F43",
        "protein": "#3DDC84",
        "cf": "#93A5BE",
        "glow": "rgba(255,159,67,0.45)",
        "off_glow": "rgba(46,51,63,0.90)",
        "off_color": "#3A4150",
    },
}

TEXT_MAIN = "#EAF2FB"
TEXT_DIM = "#8FA3BF"
TEXT_SOFT = "#C7D4E8"

DEFAULT_LABELS = {
    "remaining": "REMAINING KCALS",
    "needed": "KCALS NEEDED",
    "cut_in": "Inside deficit window",
    "cut_over": "Deficit ceiling passed",
    "bulk_ok": "Surplus locked in",
    "bulk_low": "Fill the surplus",
    "protein": "Protein",
    "carbs": "Carbs",
    "fat": "Fat",
}


def _ring(radius, color, ratio, glow, width=13):
    circumference = 2 * math.pi * radius
    clamped = max(min(ratio, 1.0), 0.0)
    dash = f"{clamped * circumference:.1f} {circumference:.1f}"
    return (
        f'<circle cx="160" cy="160" r="{radius}" fill="none" '
        f'stroke="rgba(255,255,255,0.06)" stroke-width="{width}"/>'
        f'<circle cx="160" cy="160" r="{radius}" fill="none" stroke="{color}" '
        f'stroke-width="{width}" stroke-linecap="round" stroke-dasharray="{dash}" '
        f'transform="rotate(-90 160 160)" '
        f'style="filter:drop-shadow(0 0 6px {glow});transition:all .6s ease;"/>'
    )


def _ratio(part, whole):
    if whole and whole > 0:
        return max(min(float(part) / float(whole), 1.0), 0.0)
    return 0.0


def build_dial(goal_mode, consumed, target, protein, protein_target,
               carbs, carbs_target, fat, fat_target, maintenance=None,
               labels=None):
    palette = PALETTES.get(goal_mode, PALETTES["cut"])
    L = {**DEFAULT_LABELS, **(labels or {})}
    consumed = max(float(consumed or 0), 0.0)
    target = float(target or 0)
    maintenance = float(maintenance) if maintenance else None

    if goal_mode == "bulk":
        over_limit = False
        under_floor = maintenance is not None and consumed < maintenance
        center_label = L["needed"]
        status = L["bulk_ok"] if consumed >= target else L["bulk_low"]
    else:
        over_limit = target > 0 and consumed > target
        under_floor = False
        center_label = L["remaining"]
        status = L["cut_over"] if over_limit else L["cut_in"]

    off_plan = over_limit or under_floor
    glow = palette["off_glow"] if off_plan else palette["glow"]
    accent = palette["off_color"] if off_plan else palette["calories"]
    center_value = int(max(target - consumed, 0))

    calories_ratio = _ratio(consumed, target)
    protein_ratio = _ratio(protein, protein_target)
    cf_whole = (carbs_target or 0) + (fat_target or 0)
    cf_ratio = _ratio((carbs or 0) + (fat or 0), cf_whole)

    rings = "".join([
        _ring(142, palette["calories"], calories_ratio, glow),
        _ring(115, palette["protein"], protein_ratio, glow),
        _ring(88, palette["cf"], cf_ratio, glow),
    ])

    def target_line(label, value, goal):
        return (
            f'<text x="160" y="{goal[1]}" text-anchor="middle" font-size="11.5" '
            f'fill="{TEXT_SOFT}" font-family="sans-serif">{label}: '
            f'<tspan font-weight="700" fill="{TEXT_MAIN}">{value:.0f}</tspan> / {goal[0]:.0f}g</text>'
        )

    lines = [
        target_line(L["protein"], protein, (protein_target, 196)),
        target_line(L["carbs"], carbs, (carbs_target, 215)),
        target_line(L["fat"], fat, (fat_target, 234)),
    ]

    svg = (
        f'<svg viewBox="0 0 320 320" role="img" style="width:100%;height:auto;display:block;">'
        f"{rings}"
        f'<text x="160" y="140" text-anchor="middle" font-size="44" font-weight="800" '
        f'fill="{TEXT_MAIN}" font-family="sans-serif" '
        f'style="filter:drop-shadow(0 0 10px {glow});">{center_value}</text>'
        f'<text x="160" y="161" text-anchor="middle" font-size="11" letter-spacing="2.5" '
        f'fill="{TEXT_DIM}" font-family="sans-serif">{center_label}</text>'
        f'<line x1="118" y1="172" x2="202" y2="172" stroke="rgba(255,255,255,0.10)" stroke-width="1"/>'
        f'<text x="160" y="181" text-anchor="middle" font-size="9.5" letter-spacing="1.5" '
        f'fill="{accent}" font-family="sans-serif">{status.upper()}</text>'
        + "".join(lines)
        + "</svg>"
    )
    return f'<div class="fb-dial">{svg}</div>'

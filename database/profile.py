from .connection import get_connection

PROFILE_FIELDS = (
    "age",
    "gender",
    "height_cm",
    "current_weight_kg",
    "target_weight_kg",
    "activity_description",
    "goal_mode",
    "tdee_baseline",
    "target_calories",
    "protein_target_g",
    "carbs_target_g",
    "fat_target_g",
)


def get_profile():
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM user_profile WHERE id = 1").fetchone()
    return dict(row) if row else None


def save_profile(**fields):
    unknown = set(fields) - set(PROFILE_FIELDS)
    if unknown:
        raise ValueError(f"Unknown profile fields: {sorted(unknown)}")
    goal_mode = fields.get("goal_mode")
    if goal_mode is not None and goal_mode not in ("cut", "bulk"):
        raise ValueError("goal_mode must be 'cut' or 'bulk'")
    values = tuple(fields.get(name) for name in PROFILE_FIELDS)
    columns = ", ".join(PROFILE_FIELDS)
    placeholders = ", ".join("?" for _ in PROFILE_FIELDS)
    updates = ", ".join(f"{name} = excluded.{name}" for name in PROFILE_FIELDS)
    with get_connection() as conn:
        conn.execute(
            f"INSERT INTO user_profile (id, {columns}) VALUES (1, {placeholders}) "
            f"ON CONFLICT(id) DO UPDATE SET {updates}, "
            "updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now')",
            values,
        )


def update_targets(goal_mode=None, target_calories=None, protein_target_g=None,
                   carbs_target_g=None, fat_target_g=None):
    changes = {
        "goal_mode": goal_mode,
        "target_calories": target_calories,
        "protein_target_g": protein_target_g,
        "carbs_target_g": carbs_target_g,
        "fat_target_g": fat_target_g,
    }
    changes = {name: value for name, value in changes.items() if value is not None}
    if not changes:
        return False
    if "goal_mode" in changes and changes["goal_mode"] not in ("cut", "bulk"):
        raise ValueError("goal_mode must be 'cut' or 'bulk'")
    assignments = ", ".join(f"{name} = ?" for name in changes)
    with get_connection() as conn:
        cursor = conn.execute(
            f"UPDATE user_profile SET {assignments}, "
            "updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now') WHERE id = 1",
            tuple(changes.values()),
        )
        return cursor.rowcount > 0

import json

from .connection import get_connection
from .utils import normalize_date


def add_meal(date, meal_name, items, total_calories, protein_g=0.0, carbs_g=0.0, fat_g=0.0):
    items_json = items if isinstance(items, str) else json.dumps(items, ensure_ascii=False)
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO meal_logs (date, meal_name, items_json, total_calories, "
            "protein_g, carbs_g, fat_g) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                normalize_date(date),
                str(meal_name),
                items_json,
                float(total_calories),
                float(protein_g),
                float(carbs_g),
                float(fat_g),
            ),
        )
        return cursor.lastrowid


def get_meals_for_date(date):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM meal_logs WHERE date = ? ORDER BY id",
            (normalize_date(date),),
        ).fetchall()
    meals = []
    for row in rows:
        meal = dict(row)
        try:
            meal["items"] = json.loads(meal.pop("items_json"))
        except (TypeError, ValueError):
            meal["items"] = []
        meals.append(meal)
    return meals


def delete_meal(meal_id):
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM meal_logs WHERE id = ?", (int(meal_id),))
        return cursor.rowcount > 0


def get_daily_total(date):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(total_calories), 0) AS total FROM meal_logs WHERE date = ?",
            (normalize_date(date),),
        ).fetchone()
    return float(row["total"])

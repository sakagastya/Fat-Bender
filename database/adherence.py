from datetime import date, timedelta

from .connection import get_connection
from .profile import get_profile

ON_TARGET_MAX_DELTA = 100.0
MINOR_DRIFT_MAX_DELTA = 250.0


def _status_for(total_calories, target_calories):
    if target_calories is None or target_calories <= 0:
        return None, None
    delta = total_calories - target_calories
    drift = abs(delta)
    if drift <= ON_TARGET_MAX_DELTA:
        return "On-Target", delta
    if drift <= MINOR_DRIFT_MAX_DELTA:
        return "Minor Drift", delta
    return "Off-Target", delta


def get_adherence_week(target_date=None):
    end_day = date.fromisoformat(str(target_date)) if target_date else date.today()
    days = [end_day - timedelta(offset) for offset in range(6, -1, -1)]
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT date, SUM(total_calories) AS total FROM meal_logs "
            "WHERE date BETWEEN ? AND ? GROUP BY date",
            (days[0].isoformat(), days[-1].isoformat()),
        ).fetchall()
    totals = {row["date"]: float(row["total"]) for row in rows}
    profile = get_profile()
    raw_target = profile.get("target_calories") if profile else None
    target = float(raw_target) if raw_target is not None else None
    history = []
    for day in days:
        total = totals.get(day.isoformat(), 0.0)
        status, delta = _status_for(total, target)
        history.append({
            "date": day.isoformat(),
            "total_calories": total,
            "target_calories": target,
            "delta_calories": delta,
            "status": status,
        })
    return {
        "target_calories": target,
        "week_average_calories": sum(d["total_calories"] for d in history) / len(history),
        "days": history,
    }

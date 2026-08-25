import pandas as pd

from .connection import get_connection
from .utils import normalize_date


def log_weight(weight_kg, date=None):
    day = normalize_date(date)
    weight_kg = float(weight_kg)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO weight_logs (date, weight_kg) VALUES (?, ?) "
            "ON CONFLICT(date) DO UPDATE SET weight_kg = excluded.weight_kg",
            (day, weight_kg),
        )
        rows = conn.execute("SELECT date, weight_kg FROM weight_logs ORDER BY date").fetchall()
        frame = pd.DataFrame([{"date": r["date"], "weight_kg": r["weight_kg"]} for r in rows])
        frame["rolling_avg_7d"] = (
            frame["weight_kg"].rolling(window=7, min_periods=1).mean().round(2)
        )
        stale = frame[frame["date"] >= day]
        conn.executemany(
            "UPDATE weight_logs SET rolling_avg_7d = ? WHERE date = ?",
            [(float(avg), row_date) for row_date, avg in zip(stale["date"], stale["rolling_avg_7d"])],
        )
        current = frame.loc[frame["date"] == day, "rolling_avg_7d"]
        return float(current.iloc[0]) if len(current) else None


def get_weight_for_date(date=None):
    day = normalize_date(date)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT date, weight_kg, rolling_avg_7d FROM weight_logs WHERE date = ?",
            (day,),
        ).fetchone()
    return dict(row) if row else None


def get_weight_history():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT date, weight_kg, rolling_avg_7d FROM weight_logs ORDER BY date"
        ).fetchall()
    return [dict(row) for row in rows]

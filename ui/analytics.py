from datetime import date, timedelta

PLATEAU_LOSS_THRESHOLD = -0.2
BULK_MAX_GAIN_RATE = 0.005
BULK_STALL_MIN_GAIN = 0.1
MIN_SPAN_DAYS = 7

STATUS_TITLES = {
    "cut_plateau": "Cut plateau",
    "bulk_fast": "Bulk too fast",
    "bulk_stall": "Bulk stall",
}

SUGGESTED_ADJUSTMENT = {
    "cut_plateau": -150,
    "bulk_fast": -150,
    "bulk_stall": 150,
}


def weekly_rate(history):
    rows = [r for r in history if r.get("rolling_avg_7d") is not None]
    if len(rows) < 2:
        return None
    last = rows[-1]
    last_day = date.fromisoformat(last["date"])
    cutoff = last_day - timedelta(days=MIN_SPAN_DAYS)
    prior = [r for r in rows if date.fromisoformat(r["date"]) <= cutoff]
    base = prior[-1] if prior else rows[0]
    if base["date"] == last["date"]:
        return None
    return {
        "weekly_delta": float(last["rolling_avg_7d"]) - float(base["rolling_avg_7d"]),
        "last_rolling": float(last["rolling_avg_7d"]),
        "span_days": (last_day - date.fromisoformat(base["date"])).days,
    }


def detect_trend(profile, history):
    mode = str(profile.get("goal_mode") or "cut").lower()
    weight = float(profile.get("current_weight_kg") or 0)
    rate = weekly_rate(history)
    if rate is None or rate["span_days"] < MIN_SPAN_DAYS:
        return {"status": "insufficient", "message": "", "rate": None}
    delta = rate["weekly_delta"]
    if mode == "cut":
        stalled = delta >= PLATEAU_LOSS_THRESHOLD
        status = "cut_plateau" if stalled else "healthy"
        message = (
            f"Your 7-day average has been holding near {rate['last_rolling']:.1f} kg "
            f"({delta:+.1f} kg this week). Plateaus are a normal adaptive response — "
            "a gentle calorie trim usually restarts progress."
            if stalled else ""
        )
        return {"status": status, "message": message, "rate": rate}
    too_fast = weight > 0 and delta > BULK_MAX_GAIN_RATE * weight
    stalled = delta < BULK_STALL_MIN_GAIN
    if too_fast:
        message = (
            f"You are averaging {delta:+.1f} kg this week — a touch faster than the "
            "lean-gain sweet spot. Trimming a few calories favors muscle over fat storage."
        )
        status = "bulk_fast"
    elif stalled:
        message = (
            f"The scale has barely moved this week ({delta:+.1f} kg). A small surplus "
            "bump should resume steady growth."
        )
        status = "bulk_stall"
    else:
        message = ""
        status = "healthy"
    return {"status": status, "message": message, "rate": rate}

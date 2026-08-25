MEAL_UNITS = [
    "centong", "porsi", "potong", "butir", "sdm", "sdt", "mangkok", "mangkuk",
    "bungkus", "tusuk", "gelas", "iris", "keping", "batang", "gram",
]

MEAL_SCHEMA_EXAMPLE = (
    '{"title": "...", '
    '"items": [{"name": "...", "portion": "2 centong", '
    '"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}], '
    '"totals": {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}}'
)

PLANNER_SYSTEM = (
    "You are a precise clinical nutrition calculator. Estimate total daily energy "
    "expenditure from the given biometrics and lifestyle description using standard "
    "methods such as Mifflin-St Jeor with an appropriate activity multiplier. "
    "Respond ONLY with JSON matching exactly: "
    '{"tdee_kcal": <number>, "rationale": "<concise coaching note, maximum 2 sentences>"}'
)

PARSER_SYSTEM = (
    "You are a food recognition engine fluent in informal Indonesian and international "
    "culinary language. Break any meal description into every distinct component. Detect "
    "regional dishes such as nasi goreng, ayam geprek, gado-gado, sate, rendang, pecel and "
    "estimate realistic macros for typical local preparations. Express each portion "
    "numerically with an appropriate unit such as: " + ", ".join(MEAL_UNITS) + ". "
    "Respond ONLY with JSON matching exactly this schema: " + MEAL_SCHEMA_EXAMPLE
)

REFINE_SYSTEM = (
    "You edit structured meal records based on conversational instructions that may be "
    "informal Indonesian, for example 'ganti jadi 2 centong nasi', 'tambah 1 butir telur "
    "dadar', or 'kurangi sambalnya'. Apply the requested change precisely to the affected "
    "items and return the COMPLETE updated record. Respond ONLY with JSON matching exactly "
    "this schema: " + MEAL_SCHEMA_EXAMPLE
)


def build_planner_prompt(age, gender, height_cm, weight_kg, activity_description, goal_mode):
    intent = "fat loss (cut)" if goal_mode == "cut" else "lean muscle gain (bulk)"
    return (
        f"Age: {age} years\n"
        f"Gender: {gender}\n"
        f"Height: {height_cm} cm\n"
        f"Current weight: {weight_kg} kg\n"
        f"Activity level description: {activity_description}\n"
        f"Goal mode: {intent}\n"
        "Estimate this person's TDEE in kcal."
    )


def build_parser_prompt(description):
    return f"Meal description: {description}"


def build_refine_prompt(current_json, instruction):
    return f"Current record: {current_json}\nRequested change: {instruction}"

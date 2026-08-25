import json

from .generation import request_json
from .prompts import PARSER_SYSTEM, REFINE_SYSTEM, build_parser_prompt, build_refine_prompt
from .schemas import normalize_meal, zero_meal


def parse_meal(api_key, description):
    key = (api_key or "").strip()
    text = str(description or "").strip()
    if not text:
        return {"ok": False, "meal": zero_meal(), "error": "Describe the meal to parse."}
    if not key:
        return {"ok": False, "meal": zero_meal(), "error": "Gemini API key is required."}
    data, error = request_json(key, system=PARSER_SYSTEM, prompt=build_parser_prompt(text))
    if data is None:
        return {"ok": False, "meal": zero_meal(), "error": error}
    return {"ok": True, "meal": normalize_meal(data), "error": None}


def refine_meal(api_key, meal, instruction):
    key = (api_key or "").strip()
    change = str(instruction or "").strip()
    if not change:
        return {"ok": False, "meal": zero_meal(), "error": "Provide a refinement instruction."}
    if not key:
        return {"ok": False, "meal": zero_meal(), "error": "Gemini API key is required."}
    current = json.dumps(normalize_meal(meal), ensure_ascii=False)
    data, error = request_json(key, system=REFINE_SYSTEM,
                               prompt=build_refine_prompt(current, change))
    if data is None:
        return {"ok": False, "meal": zero_meal(), "error": error}
    return {"ok": True, "meal": normalize_meal(data), "error": None}

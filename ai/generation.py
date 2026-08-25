import json
import re

from google.genai import types

from .client import (MODEL_DEFAULT, MODEL_FALLBACK, get_client, is_auth_error,
                     model_retired, sanitize_error, thinking_level_for)


def _strip_fences(text):
    body = text.strip()
    if body.startswith("```"):
        body = body.strip("`")
        if body[:4].lower() == "json":
            body = body[4:]
    return body.strip()


def _repair_truncated(text):
    start = text.find("{")
    if start == -1:
        return None
    fragment = text[start:]
    in_string = False
    escape = False
    stack = []
    for ch in fragment:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if stack:
                stack.pop()
    repaired = fragment.rstrip().rstrip(",")
    if in_string:
        repaired += '"'
    changed = True
    while changed:
        changed = False
        stripped = re.sub(r',?\s*"(?:[^"\\]|\\.)*"\s*:\s*$', "", repaired)
        if stripped != repaired:
            repaired = stripped.rstrip().rstrip(",")
            changed = True
        stripped = re.sub(r',?\s*"(?:[^"\\]|\\.)*"$', "", repaired)
        if stripped != repaired:
            repaired = stripped.rstrip().rstrip(",")
            changed = True
    repaired += "".join(reversed(stack))
    return repaired


def _extract_json(text):
    body = _strip_fences(text)
    candidates = []
    for source in (text, body):
        start = source.find("{")
        end = source.rfind("}")
        if start != -1 and end > start:
            candidates.append(source[start:end + 1])
    repaired = _repair_truncated(body)
    if repaired:
        candidates.append(repaired)
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(data, dict):
            return data
    return None


def request_json(api_key, *, system, prompt, temperature=0.1,
                 max_output_tokens=2500, timeout_ms=45000):
    client = get_client(api_key, timeout_ms)
    last_error = "AI request failed."
    model = MODEL_DEFAULT
    budget = max_output_tokens
    tried_fallback = False
    tried_thinking = False
    tried_bare_big = False
    use_thinking = False
    while True:
        kwargs = dict(
            system_instruction=system,
            response_mime_type="application/json",
            temperature=temperature,
            max_output_tokens=budget,
        )
        level = thinking_level_for(model)
        if use_thinking and level:
            kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=level)
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(**kwargs),
            )
        except Exception as exc:
            message = sanitize_error(exc, api_key)
            if is_auth_error(message):
                return None, message
            if model_retired(message) and not tried_fallback:
                tried_fallback = True
                use_thinking = False
                model = MODEL_FALLBACK
                continue
            if use_thinking and not tried_bare_big:
                tried_bare_big = True
                use_thinking = False
                budget *= 2
                continue
            return None, message
        raw = getattr(response, "text", None)
        raw = str(raw).strip() if raw else ""
        if raw:
            data = _extract_json(raw)
            if data is not None:
                return data, None
            symptom = "AI response was not parseable JSON. Please try again."
        else:
            symptom = "AI returned an empty response. Please try again."
        last_error = symptom
        if not tried_thinking and level:
            tried_thinking = True
            use_thinking = True
            budget *= 2
            continue
        if use_thinking:
            use_thinking = False
            budget *= 2
            continue
        return None, last_error

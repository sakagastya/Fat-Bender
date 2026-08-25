import json
import re

from google.genai import types

from .client import (MODEL_DEFAULT, MODEL_FALLBACK, get_client, invalid_argument,
                     model_retired, sanitize_error, thinking_config_for)


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
    queue = [(MODEL_DEFAULT, True, max_output_tokens)]
    last_error = "AI request failed."
    while queue:
        model, minimize_thinking, budget = queue.pop(0)
        kwargs = dict(
            system_instruction=system,
            response_mime_type="application/json",
            temperature=temperature,
            max_output_tokens=budget,
        )
        thinking = thinking_config_for(model) if minimize_thinking else None
        if thinking is not None:
            kwargs["thinking_config"] = thinking
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(**kwargs),
            )
        except Exception as exc:
            message = sanitize_error(exc, api_key)
            last_error = message
            if thinking is not None and invalid_argument(message):
                queue.append((model, False, budget * 2))
            elif model_retired(message) and model != MODEL_FALLBACK:
                queue.append((MODEL_FALLBACK, minimize_thinking, budget))
            continue
        raw = getattr(response, "text", None)
        if not raw or not str(raw).strip():
            return None, "AI returned an empty response. Please try again."
        data = _extract_json(str(raw))
        if data is None:
            return None, "AI response was not parseable JSON. Please try again."
        return data, None
    return None, last_error

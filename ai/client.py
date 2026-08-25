import os

from google import genai
from google.genai import types

MODEL_DEFAULT = os.environ.get("FAT_BENDER_MODEL", "gemini-3.6-flash")
MODEL_FALLBACK = "gemini-flash-latest"


def sanitize_error(error, api_key):
    text = str(error)
    if api_key:
        text = text.replace(api_key, "[REDACTED]")
    return text[:500]


def model_retired(message):
    lowered = str(message).lower()
    return "no longer available" in lowered or ("404" in lowered and "not_found" in lowered)


def invalid_argument(message):
    lowered = str(message).lower()
    if "api_key" in lowered or "api key" in lowered:
        return False
    return "invalid_argument" in lowered or "invalid argument" in lowered or "thinking" in lowered


def thinking_config_for(model):
    name = str(model or "").lower()
    try:
        if name.startswith("gemini-2"):
            return types.ThinkingConfig(thinking_budget=0)
        if name.startswith("gemini-3"):
            return types.ThinkingConfig(thinking_level="low")
    except (TypeError, ValueError):
        return None
    return None


def get_client(api_key, timeout_ms=45000):
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=int(timeout_ms)),
    )


def validate_api_key(api_key):
    key = (api_key or "").strip()
    if not key:
        return False, "API key is required."
    client = get_client(key, timeout_ms=15000)
    queue = [(MODEL_DEFAULT, True)]
    last_error = "Key rejected."
    while queue:
        model, minimize_thinking = queue.pop(0)
        kwargs = dict(temperature=0.0, max_output_tokens=16)
        thinking = thinking_config_for(model) if minimize_thinking else None
        if thinking is not None:
            kwargs["thinking_config"] = thinking
        try:
            client.models.generate_content(
                model=model,
                contents="Reply with the single word OK.",
                config=types.GenerateContentConfig(**kwargs),
            )
        except Exception as exc:
            message = sanitize_error(exc, key)
            last_error = message
            if thinking is not None and invalid_argument(message):
                queue.append((model, False))
            elif model_retired(message) and model != MODEL_FALLBACK:
                queue.append((MODEL_FALLBACK, minimize_thinking))
            continue
        return True, "Connection verified."
    return False, last_error

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
        model, disable_thinking = queue.pop(0)
        kwargs = dict(temperature=0.0, max_output_tokens=16)
        if disable_thinking:
            kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        try:
            client.models.generate_content(
                model=model,
                contents="Reply with the single word OK.",
                config=types.GenerateContentConfig(**kwargs),
            )
        except Exception as exc:
            message = sanitize_error(exc, key)
            last_error = message
            lowered = message.lower()
            if "thinking" in lowered and disable_thinking:
                queue.append((model, False))
            elif model_retired(message) and model != MODEL_FALLBACK:
                queue.append((MODEL_FALLBACK, disable_thinking))
            continue
        return True, "Connection verified."
    return False, last_error

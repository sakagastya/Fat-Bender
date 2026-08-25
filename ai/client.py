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


def is_auth_error(message):
    lowered = str(message).lower()
    return ("api_key" in lowered or "api key" in lowered
            or "unauthenticated" in lowered or "permission" in lowered)


def is_auth_error(message):
    lowered = str(message).lower()
    return ("api_key" in lowered or "api key" in lowered
            or "unauthenticated" in lowered or "permission" in lowered)


def thinking_level_for(model):
    if str(model or "").lower().startswith("gemini-3"):
        return "low"
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
    models = [MODEL_DEFAULT]
    last_error = "Key rejected."
    while models:
        model = models.pop(0)
        try:
            client.models.generate_content(
                model=model,
                contents="Reply with the single word OK.",
                config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=16),
            )
        except Exception as exc:
            message = sanitize_error(exc, key)
            last_error = message
            if is_auth_error(message):
                return False, message
            if model_retired(message) and model != MODEL_FALLBACK:
                models.append(MODEL_FALLBACK)
            continue
        return True, "Connection verified."
    return False, last_error

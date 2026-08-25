from google import genai
from google.genai import types

MODEL_DEFAULT = "gemini-2.5-flash"


def sanitize_error(error, api_key):
    text = str(error)
    if api_key:
        text = text.replace(api_key, "[REDACTED]")
    return text[:500]


def get_client(api_key, timeout_ms=45000):
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=int(timeout_ms)),
    )


def validate_api_key(api_key):
    key = (api_key or "").strip()
    if not key:
        return False, "API key is required."
    try:
        client = get_client(key, timeout_ms=15000)
        client.models.generate_content(
            model=MODEL_DEFAULT,
            contents="Reply with the single word OK.",
            config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=16),
        )
    except Exception as exc:
        return False, sanitize_error(exc, key)
    return True, "Connection verified."

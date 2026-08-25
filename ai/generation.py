import json

from google.genai import types

from .client import MODEL_DEFAULT, get_client, sanitize_error


def _extract_json(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def request_json(api_key, *, system, prompt, temperature=0.1,
                 max_output_tokens=2500, timeout_ms=45000):
    client = get_client(api_key, timeout_ms)
    try:
        response = client.models.generate_content(
            model=MODEL_DEFAULT,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )
    except Exception as exc:
        return None, sanitize_error(exc, api_key)
    raw = getattr(response, "text", None)
    if not raw or not str(raw).strip():
        return None, "AI returned an empty response."
    data = _extract_json(str(raw))
    if data is None:
        return None, "AI response was not parseable JSON."
    return data, None

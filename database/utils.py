from datetime import date


def normalize_date(value=None):
    if value is None:
        return date.today().isoformat()
    return date.fromisoformat(str(value)).isoformat()

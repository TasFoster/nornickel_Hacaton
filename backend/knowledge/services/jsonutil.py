"""Извлечение JSON-объекта из свободного текста ответа модели (устойчиво к обёрткам)."""
import json


def extract_json(raw: str) -> dict | None:
    """Прямой парс; иначе — первый сбалансированный {…} блок; иначе None."""
    if not isinstance(raw, str):
        return None
    raw = raw.strip()
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except (ValueError, json.JSONDecodeError):
        pass
    start, end = raw.find('{'), raw.rfind('}')
    if start != -1 and end > start:
        try:
            parsed = json.loads(raw[start:end + 1])
            return parsed if isinstance(parsed, dict) else None
        except (ValueError, json.JSONDecodeError):
            return None
    return None

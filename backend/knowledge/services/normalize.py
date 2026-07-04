"""
Нормализация терминов и единиц измерения.
Приводит синонимы к канону («electrowinning» → «электроэкстракция», «ПВП» →
«печь взвешенной плавки») и конвертирует единицы к базовым, чтобы числовые фильтры
работали корректно независимо от того, как записан исходник.
"""
import json
from functools import lru_cache
from pathlib import Path

# data/ontology/ лежит в корне репозитория (backend/../data/ontology).
ONTOLOGY_DIR = Path(__file__).resolve().parents[3] / 'data' / 'ontology'


@lru_cache(maxsize=1)
def _synonym_index() -> dict[str, str]:
    """Обратный индекс: любой синоним (в нижнем регистре) → канон."""
    data = _load_json('synonyms.json')
    index: dict[str, str] = {}
    for canon, alts in data.items():
        index[canon.lower()] = canon
        for alt in alts:
            index[alt.lower()] = canon
    return index


@lru_cache(maxsize=1)
def _units() -> dict:
    return _load_json('units.json')


def canonicalize_term(term: str) -> str:
    """Привести название сущности к каноническому виду."""
    return _synonym_index().get(term.strip().lower(), term.strip())


def normalize_unit(value: float, unit: str) -> tuple[float, str]:
    """Конвертировать значение к базовой единице (напр. мг/дм3 → мг/л)."""
    u = _units().get(unit.strip().lower())
    if not u or not isinstance(u, dict):
        return value, unit  # единица неизвестна — не теряем, оставляем как есть
    return value * u['factor'], u['base']


def _load_json(name: str) -> dict:
    try:
        return json.loads((ONTOLOGY_DIR / name).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}

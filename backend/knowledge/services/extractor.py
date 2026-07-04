"""
Слой извлечения знаний. Класс `Extractor` абстрагирует способ извлечения, чтобы
LLM-реализацию можно было заменить на spaCy/ruBERT без правки графа и API
(осознанный компромисс, см. README §"стек").

Числовые ограничения (концентрации, температуры, скорости) извлекаются строго —
по НФТ кейса ошибки в них недопустимы.
"""
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from knowledge.ontology import ENTITY_TYPES, RELATION_TYPES
from knowledge.services.jsonutil import extract_json
from knowledge.services.llm import get_llm


@dataclass
class ExtractionResult:
    entities: list[dict] = field(default_factory=list)   # {type, name, props}
    relations: list[dict] = field(default_factory=list)  # {type, from, to, props}
    conditions: list[dict] = field(default_factory=list) # {param, op, value, value2, unit}


SYSTEM_PROMPT = f"""Ты извлекаешь структурированные знания из горно-металлургических
текстов (RU/EN) для графа знаний R&D.
Типы сущностей: {', '.join(ENTITY_TYPES)}.
Типы связей: {', '.join(RELATION_TYPES)}.
Требования:
- числовые ограничения (концентрации, температуры, скорости) извлекай строго: param, op, value, unit;
- сохраняй единицы измерения как в тексте, конвертацию делает слой нормализации;
- не выдумывай факты, которых нет в тексте.
Верни ТОЛЬКО JSON вида {{"entities": [], "relations": [], "conditions": []}}."""


class LlmExtractor:
    """Извлечение через провайдер-агностичный LLM-слой (по умолчанию YandexGPT)."""

    def extract(self, text: str, source_ref: str, lang: str = 'auto') -> ExtractionResult:
        raw = get_llm().chat(
            system=SYSTEM_PROMPT,
            user=f'Источник: {source_ref}\nЯзык: {lang}\n\nТекст:\n{text}',
            max_tokens=4096,
        )
        return _safe_parse(raw)


# --- Строгие схемы валидации вывода модели (устойчивость к смене LLM) ---
# Числа и единицы проверяются жёстко: по НФТ кейса ошибки в концентрациях/температурах
# недопустимы, поэтому некорректные элементы отбрасываются, а не попадают в граф «как есть».

class _EntityModel(BaseModel):
    model_config = ConfigDict(extra='ignore')
    type: str
    name: str
    props: dict = Field(default_factory=dict)


class _RelationModel(BaseModel):
    model_config = ConfigDict(extra='ignore', populate_by_name=True)
    type: str
    from_: str = Field(alias='from')
    to: str
    props: dict = Field(default_factory=dict)


class _ConditionModel(BaseModel):
    model_config = ConfigDict(extra='ignore')
    param: str
    op: str
    value: float                      # строго число; "≤300" не пройдёт → элемент отброшен
    value2: float | None = None
    unit: str

    def valid_op(self) -> bool:
        return self.op in ('<=', '>=', '=', 'range')


def _safe_parse(raw: str) -> ExtractionResult:
    data = extract_json(raw)
    if not isinstance(data, dict):
        return ExtractionResult()

    entities, relations, conditions = [], [], []
    for item in data.get('entities') or []:
        try:
            entities.append(_EntityModel(**item).model_dump())
        except (ValidationError, TypeError):
            continue
    for item in data.get('relations') or []:
        try:
            relations.append(_RelationModel(**item).model_dump(by_alias=True))
        except (ValidationError, TypeError):
            continue
    for item in data.get('conditions') or []:
        try:
            c = _ConditionModel(**item)
        except (ValidationError, TypeError):
            continue
        if c.valid_op():
            conditions.append(c.model_dump())
    return ExtractionResult(entities=entities, relations=relations, conditions=conditions)

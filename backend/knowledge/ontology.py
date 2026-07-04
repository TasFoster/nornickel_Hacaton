"""
Онтология предметной области как код: единый источник правды о типах сущностей
и связей. Используется при извлечении (промпт LLM), NL→Cypher и валидации.
"""
from dataclasses import dataclass
from typing import Literal

# Типы сущностей (метки узлов Neo4j)
ENTITY_TYPES = [
    'Material',            # материалы и вещества (никель, сульфаты, гипс, угольные отходы)
    'Process',            # процессы (выщелачивание, электроэкстракция, обессоливание)
    'Equipment',          # оборудование (ванны ЭЭ, печь взвешенной плавки, очистка газов)
    'Property',           # измеряемое свойство (концентрация, температура, скорость)
    'Condition',          # условие/ограничение (сульфаты ≤ 300 мг/л, климат: холодный)
    'Experiment',         # опыт/протокол
    'Publication',        # статья / отчёт / патент / диссертация
    'Expert',             # автор / носитель компетенции
    'Facility',           # лаборатория / установка / предприятие
    'Finding',            # вывод / рекомендация
    'GeoContext',         # география (страна, регион, отеч./зарубеж.)
    'EconomicIndicator',  # технико-экономический показатель
]

# Типы связей (рёбра)
RELATION_TYPES = [
    'USES_MATERIAL',
    'APPLIED_FOR',
    'OPERATES_AT_CONDITION',
    'HAS_PROPERTY',
    'PRODUCES_OUTPUT',
    'USES_EQUIPMENT',
    'SHOWED',
    'DESCRIBED_IN',
    'VALIDATED_BY',
    'CONTRADICTS',
    'SUPERSEDES',
    'EXPERT_IN',
    'CONDUCTED_AT',
    'AUTHORED',
    'HAS_GEO',
    'HAS_ECONOMICS',
]


@dataclass
class Provenance:
    """Метаданные верификации, которыми размечается каждый извлечённый факт."""
    source_ref: str                                  # откуда взят факт (DOI/файл/id)
    confidence: Literal['high', 'medium', 'low']     # уровень достоверности
    evidence_count: int                              # число подтверждающих источников
    actualized_at: str                               # ISO-дата актуализации
    extraction: Literal['llm', 'manual', 'spacy']    # как получен
    curated_by: str | None = None                    # кто подтвердил вручную

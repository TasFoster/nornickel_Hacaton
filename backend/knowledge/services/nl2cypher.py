"""
NL → Cypher: перевод запроса на естественном языке в Cypher по схеме онтологии.
Ключевая фича демо — исследователь без знания графовых БД задаёт вопрос словами.
"""
import re

from knowledge.ontology import ENTITY_TYPES, RELATION_TYPES
from knowledge.services.llm import get_llm
from knowledge.services.retrieval import build_schema_context

# Few-shot примеры соответствуют демо-сценариям кейса.
FEWSHOT = """Пример 1 — обессоливание воды с числовым ограничением и источниками:
Вопрос: "методы обессоливания при сухом остатке <= 1000 мг/дм3, показать источники"
Cypher:
MATCH (p:Process {domain:'water_treatment'})-[:OPERATES_AT_CONDITION]->(c:Condition)
WHERE c.param='dry_residue' AND c.value <= 1000
OPTIONAL MATCH (p)-[:DESCRIBED_IN]->(pub:Publication)-[:HAS_GEO]->(g:GeoContext)
RETURN p.name AS method, c.value AS limit, c.unit AS unit,
       collect(DISTINCT {title: pub.title, year: pub.year, geo: g.scope}) AS sources;

Пример 2 — циркуляция католита, оптимальная скорость (гибкое сопоставление названий):
Вопрос: "технические решения циркуляции католита при электроэкстракции никеля в мировой практике, оптимальная скорость потока"
Cypher:
MATCH (p:Process)
WHERE toLower(p.name) CONTAINS 'электроэкстракц'
OPTIONAL MATCH (p)-[:OPERATES_AT_CONDITION]->(c:Condition)
OPTIONAL MATCH (p)-[:PRODUCES_OUTPUT]->(f:Finding)
OPTIONAL MATCH (p)-[:DESCRIBED_IN]->(pub:Publication)-[:HAS_GEO]->(g:GeoContext {scope:'foreign'})
RETURN p.name AS process,
       collect(DISTINCT {param: c.param, value: c.value, unit: c.unit}) AS conditions,
       collect(DISTINCT f.statement) AS findings,
       collect(DISTINCT {title: pub.title, year: pub.year, geo: g.scope}) AS sources;

Пример 3 — распределение Au/Ag/МПГ между штейном и шлаком за последние 5 лет:
Вопрос: "эксперименты и публикации по распределению Au, Ag и МПГ между медным/никелевым штейном и шлаком за последние 5 лет"
Cypher:
MATCH (p:Process)-[:PRODUCES_OUTPUT|USES_MATERIAL]->(m:Material)
WHERE toLower(m.name) CONTAINS 'штейн' OR toLower(m.name) CONTAINS 'шлак'
   OR toLower(m.name) CONTAINS 'мпг' OR toLower(m.name) CONTAINS 'золото' OR toLower(m.name) CONTAINS 'серебро'
OPTIONAL MATCH (p)-[:PRODUCES_OUTPUT]->(f:Finding)
OPTIONAL MATCH (p)-[:DESCRIBED_IN]->(pub:Publication)-[:HAS_GEO]->(g:GeoContext)
WHERE pub IS NULL OR pub.year >= date().year - 5
RETURN p.name AS process, collect(DISTINCT m.name) AS materials,
       collect(DISTINCT f.statement) AS findings,
       collect(DISTINCT {title: pub.title, year: pub.year, geo: g.scope}) AS sources;

Пример 4 — закачка шахтных вод в глубокие горизонты, РФ и мир, технико-экономические показатели:
Вопрос: "способы закачки шахтных вод в глубокие горизонты в России и за рубежом и их технико-экономические показатели"
Cypher:
MATCH (p:Process)
WHERE toLower(p.name) CONTAINS 'закачк' OR toLower(p.name) CONTAINS 'захорон'
OPTIONAL MATCH (p)-[:OPERATES_AT_CONDITION]->(c:Condition)
OPTIONAL MATCH (p)-[:HAS_ECONOMICS]->(ec:EconomicIndicator)
OPTIONAL MATCH (p)-[:DESCRIBED_IN]->(pub:Publication)-[:HAS_GEO]->(g:GeoContext)
RETURN p.name AS process,
       collect(DISTINCT {param: c.param, value: c.value, unit: c.unit}) AS conditions,
       collect(DISTINCT {indicator: ec.name, value: ec.value, kind: ec.capex_opex}) AS economics,
       collect(DISTINCT {title: pub.title, year: pub.year, geo: g.scope}) AS sources;"""

SYSTEM_PROMPT = f"""Ты переводишь вопросы о горно-металлургическом R&D в запросы Cypher
для Neo4j по фиксированной онтологии.
Метки узлов: {', '.join(ENTITY_TYPES)}.
Типы связей: {', '.join(RELATION_TYPES)}.
Правила:
- используй ТОЛЬКО реально существующие метки, связи и ЗНАЧЕНИЯ свойств из блока «СХЕМА ГРАФА»
  в запросе пользователя. НЕ придумывай значения name/domain/param — бери их из схемы;
- для сопоставления НАЗВАНИЙ применяй ГИБКОЕ сравнение через WHERE, а не точное равенство в
  паттерне: например `WHERE toLower(p.name) CONTAINS 'электроэкстракц'` или
  `toLower(m.name) CONTAINS 'католит'`;
- числовые ограничения выражай через свойства узлов Condition (param, op, value, unit);
- гео: «мировая/зарубежная практика» → GeoContext.scope='foreign', «отечественная/российская»
  → 'domestic'. Если география явно НЕ указана в вопросе — НЕ добавляй фильтр по гео и делай
  связь к Publication/GeoContext через OPTIONAL MATCH;
- возвращай только READ-запрос (MATCH/RETURN), без записи в граф;
- верни ТОЛЬКО текст Cypher, без пояснений.
{FEWSHOT}"""

_WRITE_CLAUSE = re.compile(r'\b(CREATE|MERGE|DELETE|SET|REMOVE|DROP)\b', re.IGNORECASE)


def nl_to_cypher(question: str) -> str:
    ctx = build_schema_context()
    user = (
        f'СХЕМА ГРАФА (реальные значения — используй ТОЛЬКО их):\n{ctx}\n\n'
        f'Вопрос: {question}\nCypher:'
    )
    raw = get_llm().chat(system=SYSTEM_PROMPT, user=user, max_tokens=1024)
    return _strip_fences(raw)


def is_read_only(cypher: str) -> bool:
    """Guardrail: разрешаем исполнять только READ-запросы."""
    return not _WRITE_CLAUSE.search(cypher)


def _strip_fences(s: str) -> str:
    s = s.strip()
    s = re.sub(r'^```(?:cypher)?', '', s, flags=re.IGNORECASE)
    s = re.sub(r'```$', '', s)
    return s.strip()

"""
Заземление NL→Cypher на реальные данные графа и запасной поиск.

- build_schema_context(): собирает реальный словарь графа (метки, связи и ЗНАЧЕНИЯ ключевых
  свойств), чтобы LLM не выдумывал названия процессов/доменов/параметров.
- keyword_fallback(): если сгенерированный Cypher вернул 0 строк — грубый поиск по ключевым
  словам вопроса (с префиксным «стеммингом» для русской морфологии), чтобы ответ не был пустым.
"""
import re

from knowledge.services import graph

# Стоп-слова вопроса, которые не несут смысла для поиска.
_STOP = {
    'какие', 'какая', 'какой', 'каков', 'какое', 'что', 'чем', 'при', 'для', 'над', 'под',
    'технические', 'решения', 'решение', 'описаны', 'описано', 'существуют', 'считается',
    'мировой', 'мировая', 'практике', 'практика', 'зарубежных', 'отечественной', 'показать',
    'покажи', 'найти', 'применяются', 'применялись', 'используются', 'каковы', 'этом',
}


def build_schema_context() -> str:
    """Реальные метки, связи и значения ключевых свойств графа — компактным текстом."""
    lines: list[str] = []
    try:
        labels = graph.run('MATCH (n) UNWIND labels(n) AS l RETURN l, count(*) AS c ORDER BY c DESC')
        if labels:
            lines.append('Метки узлов: ' + ', '.join(f"{r['l']}({r['c']})" for r in labels))
        rels = graph.run('MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c ORDER BY c DESC')
        if rels:
            lines.append('Типы связей: ' + ', '.join(f"{r['t']}" for r in rels))
        procs = graph.run('MATCH (p:Process) RETURN collect(DISTINCT p.name) AS names, collect(DISTINCT p.domain) AS domains')
        if procs and procs[0]['names']:
            lines.append('Process.name (реальные): ' + ', '.join(f'"{n}"' for n in procs[0]['names'] if n))
            lines.append('Process.domain (реальные): ' + ', '.join(f'"{d}"' for d in procs[0]['domains'] if d))
        mats = graph.run('MATCH (m:Material) RETURN collect(DISTINCT m.name) AS names')
        if mats and mats[0]['names']:
            lines.append('Material.name: ' + ', '.join(f'"{n}"' for n in mats[0]['names'] if n))
        conds = graph.run('MATCH (c:Condition) RETURN collect(DISTINCT c.param) AS params')
        if conds and conds[0]['params']:
            lines.append('Condition.param (реальные): ' + ', '.join(f'"{p}"' for p in conds[0]['params'] if p))
        geos = graph.run('MATCH (g:GeoContext) RETURN collect(DISTINCT g.scope) AS scopes')
        if geos and geos[0]['scopes']:
            lines.append('GeoContext.scope: ' + ', '.join(f'"{s}"' for s in geos[0]['scopes'] if s))
    except Exception:  # noqa: BLE001 — контекст необязателен, без него просто меньше подсказок
        return ''
    return '\n'.join(lines)


def _keywords(question: str) -> list[str]:
    """Ключевые слова вопроса, обрезанные до префикса (грубый стемминг под русскую морфологию)."""
    words = re.findall(r'[А-Яа-яЁёA-Za-z]{5,}', question.lower())
    seen: dict[str, None] = {}
    for w in words:
        if w in _STOP:
            continue
        seen.setdefault(w[:6], None)  # префикс: 'электроэкстракции' и '...ция' → 'электр'
    return list(seen.keys())


def keyword_fallback(question: str) -> list[dict]:
    """Запасной поиск процессов по ключевым словам вопроса (когда точный Cypher дал 0 строк)."""
    kws = _keywords(question)
    if not kws:
        return []
    return graph.run(
        'MATCH (p:Process) '
        'OPTIONAL MATCH (p)-[:USES_MATERIAL|APPLIED_FOR]->(m:Material) '
        'OPTIONAL MATCH (p)-[:DESCRIBED_IN]->(pub:Publication)-[:HAS_GEO]->(g:GeoContext) '
        'OPTIONAL MATCH (p)-[:OPERATES_AT_CONDITION]->(c:Condition) '
        'WITH p, collect(DISTINCT toLower(m.name)) AS mats, '
        '     collect(DISTINCT {title: pub.title, year: pub.year, geo: g.scope}) AS sources, '
        '     collect(DISTINCT {param: c.param, value: c.value, unit: c.unit}) AS conditions '
        'WHERE any(kw IN $kws WHERE toLower(p.name) CONTAINS kw) '
        '   OR any(kw IN $kws WHERE any(x IN mats WHERE x CONTAINS kw)) '
        'RETURN p.name AS method, [s IN sources WHERE s.title IS NOT NULL] AS sources, '
        '       [c IN conditions WHERE c.param IS NOT NULL] AS conditions '
        'LIMIT 25',
        {'kws': kws},
    )

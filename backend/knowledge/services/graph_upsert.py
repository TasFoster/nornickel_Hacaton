"""
Идемпотентная загрузка результата извлечения в граф (MERGE + провенанс).

Повторный запуск не создаёт дублей (MERGE по ключу) и наращивает evidence_count —
это даёт «число подтверждающих источников» из модели верификации. Метки узлов и типы
связей валидируются против онтологии перед подстановкой в Cypher (защита от инъекции,
т.к. их нельзя передать параметром).
"""
from knowledge.ontology import ENTITY_TYPES, RELATION_TYPES
from knowledge.services import graph


def _safe_label(t: str | None) -> str:
    return t if t in ENTITY_TYPES else 'Entity'


def _condition_key(c: dict) -> str:
    return f"{c.get('param')}|{c.get('op')}|{c.get('value')}|{c.get('unit')}"


def upsert_entities(entities: list[dict], prov: dict) -> int:
    n = 0
    for e in entities:
        name = (e.get('name') or '').strip()
        if not name:
            continue
        label = _safe_label(e.get('type'))
        graph.run(
            f'MERGE (n:`{label}` {{name:$name}}) '
            'ON CREATE SET n.evidence_count = 1 '
            'ON MATCH SET n.evidence_count = coalesce(n.evidence_count, 0) + 1 '
            'SET n += $props, n.source_ref = $src, n.confidence = $conf, '
            '    n.actualized_at = $ts, n.extraction = $ext',
            {
                'name': name, 'props': e.get('props') or {},
                'src': prov['source_ref'], 'conf': prov['confidence'],
                'ts': prov['actualized_at'], 'ext': prov['extraction'],
            },
        )
        n += 1
    return n


def upsert_conditions(conditions: list[dict], prov: dict, owner: str | None = None) -> int:
    n = 0
    for c in conditions:
        key = _condition_key(c)
        graph.run(
            'MERGE (n:Condition {key:$key}) '
            'SET n.param=$param, n.op=$op, n.value=$value, n.value2=$value2, n.unit=$unit, '
            '    n.source_ref=$src, n.confidence=$conf, n.actualized_at=$ts',
            {
                'key': key, 'param': c.get('param'), 'op': c.get('op'),
                'value': c.get('value'), 'value2': c.get('value2'), 'unit': c.get('unit'),
                'src': prov['source_ref'], 'conf': prov['confidence'], 'ts': prov['actualized_at'],
            },
        )
        if owner:
            graph.run(
                'MATCH (p {name:$owner}), (c:Condition {key:$key}) '
                'MERGE (p)-[:OPERATES_AT_CONDITION]->(c)',
                {'owner': owner, 'key': key},
            )
        n += 1
    return n


def upsert_relations(relations: list[dict], prov: dict) -> int:
    n = 0
    for r in relations:
        rtype = r.get('type')
        if rtype not in RELATION_TYPES:
            continue
        a, b = (r.get('from') or '').strip(), (r.get('to') or '').strip()
        if not a or not b:
            continue
        graph.run(
            'MATCH (a {name:$a}), (b {name:$b}) '
            f'MERGE (a)-[rel:`{rtype}`]->(b) '
            'ON CREATE SET rel.evidence_count = 1 '
            'ON MATCH SET rel.evidence_count = coalesce(rel.evidence_count, 0) + 1 '
            'SET rel.source_ref=$src, rel.confidence=$conf, rel.actualized_at=$ts',
            {
                'a': a, 'b': b, 'src': prov['source_ref'],
                'conf': prov['confidence'], 'ts': prov['actualized_at'],
            },
        )
        n += 1
    return n


def upsert_extraction(result, prov: dict, condition_owner: str | None = None) -> dict:
    """Загрузить весь результат извлечения. Порядок: узлы → условия → связи (нужны оба конца)."""
    return {
        'entities': upsert_entities(result.entities, prov),
        'conditions': upsert_conditions(result.conditions, prov, owner=condition_owner),
        'relations': upsert_relations(result.relations, prov),
    }

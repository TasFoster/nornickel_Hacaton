"""
REST API поверх графа знаний и пайплайнов. Тонкий слой: разбор запроса → сервис → ответ.
Каждый запрос к графу пишется в аудит (QueryLog) — требование кейса по ИБ.
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from knowledge.models import QueryLog
from knowledge.services import graph
from knowledge.services.nl2cypher import nl_to_cypher, is_read_only
from knowledge.services.synthesis import synthesize
from knowledge.services.retrieval import keyword_fallback


def _audit(**kwargs):
    """Запись в журнал аудита best-effort: сбой аудита не должен ломать ответ API."""
    try:
        QueryLog.objects.create(**kwargs)
    except Exception:  # noqa: BLE001
        pass


@api_view(['GET'])
def health(request):
    """Живость API и связь с Neo4j."""
    try:
        graph.verify_connectivity()
        return Response({'status': 'ok', 'neo4j': 'up'})
    except Exception as exc:  # noqa: BLE001 — на health отдаём причину как есть
        return Response(
            {'status': 'degraded', 'neo4j': 'down', 'detail': str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@api_view(['POST'])
def query(request):
    """Запрос на естественном языке: NL → Cypher → граф → (позже) синтез ответа."""
    question = (request.data or {}).get('question')
    if not question:
        return Response({'error': 'Не передан question'}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user if request.user.is_authenticated else None
    cypher = ''
    try:
        cypher = nl_to_cypher(question)
        if not is_read_only(cypher):
            _audit(user=user, question=question, cypher=cypher, error='Отклонён запрос на запись')
            return Response(
                {'error': 'Сгенерирован запрос на запись — отклонён', 'cypher': cypher},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rows = graph.run(cypher)
        used_fallback = False
        if not rows:
            # Точный запрос ничего не нашёл — грубый поиск по ключевым словам вопроса.
            rows = keyword_fallback(question)
            used_fallback = bool(rows)
        answer = synthesize(question, rows)  # структурированный «литобзор» из строк графа
        _audit(user=user, question=question, cypher=cypher, row_count=len(rows))
        return Response({'question': question, 'cypher': cypher, 'rows': rows,
                         'answer': answer, 'fallback': used_fallback})
    except Exception as exc:  # noqa: BLE001
        _audit(user=user, question=question, cypher=cypher, error=str(exc))
        return Response(
            {'error': 'Ошибка выполнения запроса', 'detail': str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
def subgraph(request):
    """Подграф для визуализации цепочек «материал → процесс → оборудование → результат».

    Реализован чистым Cypher (без APOC), поэтому работает и в локальном Neo4j Community,
    и в Aura. Собирает узлы в радиусе 2 от центра и связи между ними, возвращая примитивы
    (id/labels/props, type/start/end) — удобно для визуализации на фронте.
    """
    center = request.query_params.get('center', '')
    if not center:
        return Response({'error': 'Не передан center'}, status=status.HTTP_400_BAD_REQUEST)
    rows = graph.run(
        'MATCH (c {name:$center}) '
        'OPTIONAL MATCH (c)-[*1..2]-(m) '
        'WITH c, collect(DISTINCT m) AS others '
        'WITH [c] + [x IN others WHERE x IS NOT NULL] AS ns '
        'UNWIND ns AS n '
        'OPTIONAL MATCH (n)-[r]-(n2) WHERE n2 IN ns '
        'WITH ns, collect(DISTINCT r) AS rels '
        'RETURN [n IN ns | {id: elementId(n), labels: labels(n), name: n.name, props: properties(n)}] AS nodes, '
        '       [r IN rels WHERE r IS NOT NULL | {type: type(r), start: elementId(startNode(r)), end: elementId(endNode(r))}] AS relationships',
        {'center': center},
    )
    return Response(rows[0] if rows else {'nodes': [], 'relationships': []})

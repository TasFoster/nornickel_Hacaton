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
from knowledge.services.synthesis import synthesize, conclusion_from_answer
from knowledge.services.retrieval import (
    hydrate_processes, process_names_from_rows, recommend, detect_gaps,
    search_findings, findings_from_rows, intent_conclusion,
)


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
    """Запрос на естественном языке: NL → Cypher → граф → синтез ответа.

    Точность прежде всего: выборка данных идёт ТОЛЬКО из сгенерированного LLM Cypher —
    приблизительного поиска по ключевым словам нет (он подмешивал слабо связанные данные
    и повышал погрешность выборки). Если LLM недоступен или его Cypher ничего не нашёл —
    возвращаем честный пустой ответ, а не домыслы. 503 отдаём только если недоступен граф.
    """
    question = (request.data or {}).get('question')
    if not question:
        return Response({'error': 'Не передан question'}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user if request.user.is_authenticated else None
    cypher = ''
    llm_ok = True

    # 1. NL → Cypher. При недоступности LLM — не 500, но и данных без Cypher не выдумываем.
    try:
        cypher = nl_to_cypher(question)
    except Exception as exc:  # noqa: BLE001 — LLM недоступен: продолжаем, ответ будет пустым
        llm_ok = False
        _audit(user=user, question=question, cypher='', error=f'LLM недоступен: {exc}')

    # Guardrail: сгенерированный запрос на запись отклоняем.
    if cypher and not is_read_only(cypher):
        _audit(user=user, question=question, cypher=cypher, error='Отклонён запрос на запись')
        return Response(
            {'error': 'Сгенерирован запрос на запись — отклонён', 'cypher': cypher},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 2. Исполняем Cypher. Ошибка исполнения: если граф жив — это плохой Cypher (пустой ответ),
    #    если граф недоступен — честный 503. Приблизительного поиска по словам больше нет.
    rows = []
    if cypher:
        try:
            rows = graph.run(cypher)
        except Exception as exc:  # noqa: BLE001
            _audit(user=user, question=question, cypher=cypher, error=f'Cypher не выполнен: {exc}')
            try:
                graph.verify_connectivity()
            except Exception as gexc:  # noqa: BLE001 — недоступен сам граф
                _audit(user=user, question=question, cypher=cypher, error=f'Граф недоступен: {gexc}')
                return Response(
                    {'error': 'Граф недоступен', 'detail': str(gexc)},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            rows = []  # граф жив, но Cypher не подошёл — пустой ответ без домыслов

    # 3. Гидратация: LLM нашёл нужные процессы, но его RETURN часто неполон (забывает источники/
    #    условия). Поэтому по найденным процессам детерминированно подтягиваем полный контекст —
    #    ответ выходит богатым (условия, выводы, источники) независимо от качества Cypher.
    names = process_names_from_rows(rows)
    if names:
        try:
            hydrated = hydrate_processes(names)
            if hydrated:
                rows = hydrated
        except Exception as exc:  # noqa: BLE001 — гидратация необязательна, не роняем ответ
            _audit(user=user, question=question, cypher=cypher, error=f'Гидратация не удалась: {exc}')

    # 4. Синтез ответа строго из точных строк (детерминированный синтез исключений не бросает).
    answer = synthesize(question, rows)

    # 5. Обогащаем ответ: прямые выводы по вопросу (часто ответ — в тексте Finding, а не в имени
    #    процесса), пробелы в знаниях и рекомендации (эксперты, лаборатории, похожие кейсы).
    try:
        recs = recommend(names)
        # Вывод гарантируем для любого непустого ответа: 1) релевантный по словам Finding →
        # 2) выводы найденных процессов → 3) синтез вывода из лучшего метода.
        found = search_findings(question) or findings_from_rows(rows)
        if not found:
            c = conclusion_from_answer(answer)
            found = [c] if c else []
        # Вывод под НАМЕРЕНИЕ вопроса (оборудование/материал/эксперт/лаборатория) — в начало,
        # чтобы ответ отвечал именно на заданный вопрос, а не просто на тему.
        ic = intent_conclusion(question, rows, recs, answer)
        if ic:
            found = [ic] + [f for f in found if f.get('statement') != ic.get('statement')]
        answer['findings'] = found[:5]
        answer['gaps'] = detect_gaps(answer, names)
        answer['recommendations'] = recs
    except Exception:  # noqa: BLE001 — дополнительная аналитика необязательна
        answer.setdefault('findings', [])
        answer.setdefault('gaps', [])
        answer.setdefault('recommendations', {'experts': [], 'facilities': [], 'similar': []})

    _audit(user=user, question=question, cypher=cypher, row_count=len(rows))
    return Response({'question': question, 'cypher': cypher, 'rows': rows,
                     'answer': answer, 'fallback': False, 'llm': llm_ok})


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


# Загрузка одного документа за запрос ограничена по объёму, чтобы синхронный ответ был быстрым.
_INGEST_MAX_BYTES = 25 * 1024 * 1024   # 25 МБ на файл
_INGEST_MAX_CHUNKS = 12                 # обрабатываем первые N чанков (баланс полноты/времени)


@api_view(['POST'])
def ingest(request):
    """Загрузка документа в граф: PDF/DOCX/XLSX/CSV/TXT/MD → извлечение знаний → нормализация
    терминов и единиц → идемпотентный upsert (MERGE) с провенансом.

    Реализует требование «Импорт и нормализация данных / поддержка загрузки». Файл передаётся
    multipart-полем `file`. Ошибки импорта обрабатываются (400 с причиной), а не роняют сервер.
    """
    import os
    import tempfile
    from pathlib import Path as _Path

    from django.utils import timezone
    from knowledge.services.documents import read_document, chunk_text, SUPPORTED
    from knowledge.services.extractor import LlmExtractor
    from knowledge.services.normalize import canonicalize_term, normalize_unit
    from knowledge.services.graph_upsert import upsert_extraction

    upload = request.FILES.get('file')
    if upload is None:
        return Response({'error': 'Не передан файл (ожидается multipart-поле "file")'},
                        status=status.HTTP_400_BAD_REQUEST)
    ext = _Path(upload.name).suffix.lower()
    if ext not in SUPPORTED:
        return Response({'error': f'Формат {ext or "?"} не поддерживается',
                         'supported': list(SUPPORTED)}, status=status.HTTP_400_BAD_REQUEST)
    if upload.size and upload.size > _INGEST_MAX_BYTES:
        return Response({'error': f'Файл больше {_INGEST_MAX_BYTES // (1024 * 1024)} МБ'},
                        status=status.HTTP_400_BAD_REQUEST)

    # Сохраняем во временный файл, читаем текст, гарантированно удаляем.
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            for part in upload.chunks():
                tmp.write(part)
            tmp_path = _Path(tmp.name)
        text = read_document(tmp_path)
    except Exception as exc:  # noqa: BLE001 — битый/нечитаемый файл: 400, а не 500
        return Response({'error': f'Не удалось прочитать файл: {exc}'},
                        status=status.HTTP_400_BAD_REQUEST)
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    if not (text or '').strip():
        return Response({'error': 'Из файла не извлечён текст'}, status=status.HTTP_400_BAD_REQUEST)

    chunks = chunk_text(text)
    truncated = len(chunks) > _INGEST_MAX_CHUNKS
    chunks = chunks[:_INGEST_MAX_CHUNKS]
    extractor = LlmExtractor()
    totals = {'entities': 0, 'conditions': 0, 'relations': 0}
    llm_errors = 0
    for ch in chunks:
        try:
            result = extractor.extract(ch, source_ref=upload.name, lang='ru')
        except Exception:  # noqa: BLE001 — LLM недоступен на этом чанке: пропускаем
            llm_errors += 1
            continue
        for e in result.entities:  # нормализация терминов (синонимы → канон)
            e['name'] = canonicalize_term(e.get('name', ''))
        for c in result.conditions:  # нормализация единиц (мг/дм3 → мг/л и т.п.)
            try:
                c['value'], c['unit'] = normalize_unit(float(c.get('value', 0)), c.get('unit', ''))
            except (TypeError, ValueError):
                pass
        prov = {'source_ref': upload.name, 'confidence': 'medium',
                'actualized_at': timezone.now().isoformat(), 'extraction': 'llm'}
        try:
            counts = upsert_extraction(result, prov)
            for k in totals:
                totals[k] += counts[k]
        except Exception:  # noqa: BLE001 — сбой upsert одного чанка не валит всю загрузку
            continue

    _audit(user=request.user if request.user.is_authenticated else None,
           question=f'ingest: {upload.name}', cypher='',
           row_count=totals['entities'])
    return Response({'file': upload.name, 'format': ext,
                     'chunks_processed': len(chunks), 'truncated': truncated,
                     'llm_errors': llm_errors, **totals})


@api_view(['POST'])
def fact(request):
    """Ручная корректировка графа экспертом: добавить вывод (Finding) к процессу с провенансом
    'manual' и высокой достоверностью. Закрывает требование «ручная корректировка графа
    экспертами». Пример тела: {"process": "флотация шлака", "finding": "...", "geo": "domestic"}.
    """
    from django.utils import timezone

    data = request.data or {}
    proc = (data.get('process') or '').strip()
    stmt = (data.get('finding') or '').strip()
    if not proc or not stmt:
        return Response({'error': 'Нужны поля process и finding'}, status=status.HTTP_400_BAD_REQUEST)
    geo = (data.get('geo') or '').strip().lower()
    geo = geo if geo in ('domestic', 'foreign') else ''
    ts = timezone.now().isoformat()
    try:
        graph.run(
            'MERGE (p:Process {name:$proc}) '
            'ON CREATE SET p.extraction="manual", p.actualized_at=$ts '
            'MERGE (f:Finding {statement:$stmt}) '
            'SET f.extraction="manual", f.confidence="high", f.curated=true, f.actualized_at=$ts '
            'MERGE (p)-[r:PRODUCES_OUTPUT]->(f) SET r.confidence="high", r.actualized_at=$ts',
            {'proc': proc, 'stmt': stmt, 'ts': ts},
        )
        if geo:
            graph.run(
                'MATCH (f:Finding {statement:$stmt}) '
                'MERGE (g:GeoContext {scope:$geo}) MERGE (f)-[:HAS_GEO]->(g)',
                {'stmt': stmt, 'geo': geo},
            )
    except Exception as exc:  # noqa: BLE001
        return Response({'error': f'Не удалось записать факт: {exc}'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    _audit(user=request.user if request.user.is_authenticated else None,
           question=f'manual fact: {proc}', cypher='', row_count=1)
    return Response({'ok': True, 'process': proc, 'finding': stmt, 'geo': geo or None})

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


def build_schema_context(question: str = '') -> str:
    """Реальный словарь графа для заземления NL→Cypher, СФОКУСИРОВАННЫЙ на вопросе.

    Граф после обогащения большой (сотни процессов/материалов). Вываливать весь словарь
    в промпт бессмысленно: LLM тонет в нём и промахивается. Поэтому отдаём метки/связи (скелет)
    + только те имена процессов/материалов, что релевантны ключевым словам вопроса (CONTAINS),
    с жёстким лимитом на количество. Без вопроса — ограниченная выборка (обратная совместимость).
    """
    lines: list[str] = []
    kws = _keywords(question) if question else []
    try:
        labels = graph.run('MATCH (n) UNWIND labels(n) AS l RETURN l, count(*) AS c ORDER BY c DESC')
        if labels:
            lines.append('Метки узлов: ' + ', '.join(f"{r['l']}({r['c']})" for r in labels))
        rels = graph.run('MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c ORDER BY c DESC')
        if rels:
            lines.append('Типы связей: ' + ', '.join(f"{r['t']}" for r in rels))

        # Процессы и материалы, релевантные вопросу (или ограниченная выборка без вопроса).
        if kws:
            procs = graph.run(
                'MATCH (p:Process) WHERE any(k IN $kws WHERE toLower(p.name) CONTAINS k) '
                'RETURN collect(DISTINCT p.name)[0..40] AS names', {'kws': kws})
            mats = graph.run(
                'MATCH (m:Material) WHERE any(k IN $kws WHERE toLower(m.name) CONTAINS k) '
                'RETURN collect(DISTINCT m.name)[0..40] AS names', {'kws': kws})
        else:
            procs = graph.run('MATCH (p:Process) RETURN collect(DISTINCT p.name)[0..40] AS names')
            mats = graph.run('MATCH (m:Material) RETURN collect(DISTINCT m.name)[0..40] AS names')
        pnames = (procs[0]['names'] if procs else []) or []
        if pnames:
            lines.append('Process.name, релевантные вопросу (используй ТОЧНО эти имена для CONTAINS): '
                         + ', '.join(f'"{n}"' for n in pnames if n))
        mnames = (mats[0]['names'] if mats else []) or []
        if mnames:
            lines.append('Material.name, релевантные вопросу: ' + ', '.join(f'"{n}"' for n in mnames if n))

        doms = graph.run('MATCH (p:Process) WHERE p.domain IS NOT NULL RETURN collect(DISTINCT p.domain) AS d')
        dl = (doms[0]['d'] if doms else []) or []
        if dl:
            lines.append('Process.domain: ' + ', '.join(f'"{d}"' for d in dl[:20]))
        conds = graph.run('MATCH (c:Condition) WHERE c.param IS NOT NULL RETURN collect(DISTINCT c.param) AS p')
        cp = (conds[0]['p'] if conds else []) or []
        if cp:
            lines.append('Condition.param (реальные): ' + ', '.join(f'"{p}"' for p in cp[:40]))
        geos = graph.run('MATCH (g:GeoContext) WHERE g.scope IS NOT NULL RETURN collect(DISTINCT g.scope) AS s')
        gs = (geos[0]['s'] if geos else []) or []
        if gs:
            lines.append('GeoContext.scope: ' + ', '.join(f'"{s}"' for s in gs[:10]))
    except Exception:  # noqa: BLE001 — контекст необязателен, без него просто меньше подсказок
        return ''
    return '\n'.join(lines)


def hydrate_processes(names: list[str], limit: int = 12) -> list[dict]:
    """По именам процессов детерминированно подтянуть их условия, выводы, материалы и источники.

    Сгенерированный LLM Cypher часто неполон в RETURN (забывает источники/условия) — поэтому,
    как только процессы найдены по именам, полный контекст берём фиксированным корректным
    запросом. Гарантирует, что ответ так же богат, как демо, независимо от качества NL→Cypher.
    """
    names = [n for n in {(n or '').strip() for n in names} if n][:limit]
    if not names:
        return []
    return graph.run(
        'MATCH (p:Process) WHERE p.name IN $names '
        'OPTIONAL MATCH (p)-[:OPERATES_AT_CONDITION]->(c:Condition) '
        'OPTIONAL MATCH (p)-[:PRODUCES_OUTPUT]->(f:Finding) '
        'OPTIONAL MATCH (p)-[:USES_MATERIAL]->(m:Material) '
        'OPTIONAL MATCH (p)-[:USES_EQUIPMENT]->(eq:Equipment) '
        'OPTIONAL MATCH (p)-[:DESCRIBED_IN]->(pub:Publication) '
        'OPTIONAL MATCH (pub)-[:HAS_GEO]->(g:GeoContext) '
        'RETURN p.name AS method, p.domain AS domain, '
        '  collect(DISTINCT {param: c.param, op: c.op, value: c.value, unit: c.unit}) AS conditions, '
        '  collect(DISTINCT f.statement) AS findings, '
        '  collect(DISTINCT m.name) AS materials, '
        '  collect(DISTINCT eq.name) AS equipment, '
        '  collect(DISTINCT {title: pub.title, year: pub.year, geo: g.scope}) AS sources',
        {'names': names},
    )


def recommend(names: list[str], limit: int = 6) -> dict:
    """Рекомендации по найденным процессам: связанные эксперты, лаборатории/предприятия и
    похожие кейсы (процессы с общими материалами). Закрывает требования «связанные эксперты
    и лаборатории» и «рекомендации по похожим кейсам и экспертам»."""
    names = [n for n in {(n or '').strip() for n in names} if n][:limit]
    if not names:
        return {'experts': [], 'facilities': [], 'similar': []}
    fetch = limit * 5  # берём с запасом, схлопываем дубли (пробелы/регистр) и режем до limit
    experts = graph.run(
        'MATCH (p:Process) WHERE p.name IN $names MATCH (p)-[*1..2]-(e:Expert) '
        'RETURN DISTINCT e.name AS name LIMIT $fetch', {'names': names, 'fetch': fetch})
    facilities = graph.run(
        'MATCH (p:Process) WHERE p.name IN $names MATCH (p)-[*1..2]-(f:Facility) '
        'RETURN DISTINCT f.name AS name LIMIT $fetch', {'names': names, 'fetch': fetch})
    similar = graph.run(
        'MATCH (p:Process) WHERE p.name IN $names '
        'MATCH (p)-[:USES_MATERIAL]->(m:Material)<-[:USES_MATERIAL]-(s:Process) '
        'WHERE NOT s.name IN $names '
        'RETURN DISTINCT s.name AS name, count(DISTINCT m) AS shared '
        'ORDER BY shared DESC LIMIT $fetch', {'names': names, 'fetch': fetch})

    def clean(rows: list[dict]) -> list[str]:
        seen, out = set(), []
        for r in rows:
            name = (r.get('name') or '').strip()
            key = name.lower()
            if name and key not in seen:
                seen.add(key)
                out.append(name)
        return out[:limit]
    return {'experts': clean(experts), 'facilities': clean(facilities), 'similar': clean(similar)}


def detect_gaps(answer: dict, names: list[str]) -> list[str]:
    """Выявление пробелов в знаниях по текущему запросу: методы без подтверждающих источников,
    слабое покрытие, противоречия. Закрывает требование «выявление пробелов в знаниях»."""
    gaps: list[str] = []
    for m in answer.get('consensus', []):
        if not m.get('sources'):
            gaps.append(f'Метод «{m.get("name")}» найден в графе, но без подтверждающих источников — пробел в данных')
    total_src = len(answer.get('sources', []))
    if answer.get('consensus') and total_src < 2:
        gaps.append('Слабое покрытие источниками (менее 2) — рекомендуется дозагрузить публикации по теме')
    if names:
        try:
            c = graph.run('MATCH (p:Process) WHERE p.name IN $names MATCH (p)-[:CONTRADICTS]-() '
                          'RETURN count(*) AS c', {'names': names})
            if c and c[0]['c']:
                gaps.append('Обнаружены противоречивые данные (CONTRADICTS) — требуется экспертная верификация')
        except Exception:  # noqa: BLE001
            pass
    return gaps[:6]


def search_findings(question: str, limit: int = 5) -> list[dict]:
    """Прямой поиск ВЫВОДОВ (Finding), отвечающих на вопрос: часто ответ («0.1–0.3 м/с,
    улучшает качество катодного осадка») лежит в тексте вывода, а не в имени процесса.
    Ранжируем по числу совпавших ключевых слов вопроса. Возвращает вывод + процесс + источники.
    """
    kws = _keywords(question)
    if not kws:
        return []
    # для содержательных вопросов требуем ≥2 совпавших слов (отсекаем случайные совпадения
    # по одному общему слову вроде «обеспечивает»); для коротких — достаточно одного.
    min_score = 2 if len(kws) >= 3 else 1
    rows = graph.run(
        'MATCH (f:Finding) WHERE f.statement IS NOT NULL '
        'WITH f, size([k IN $kws WHERE toLower(f.statement) CONTAINS k]) AS score '
        'WHERE score >= $min_score '
        'OPTIONAL MATCH (p:Process)-[:PRODUCES_OUTPUT]->(f) '
        'OPTIONAL MATCH (p)-[:DESCRIBED_IN]->(pub:Publication) '
        'OPTIONAL MATCH (pub)-[:HAS_GEO]->(g:GeoContext) '
        'WITH f, score, collect(DISTINCT p.name) AS procs, '
        '     collect(DISTINCT {title: pub.title, year: pub.year, geo: g.scope}) AS sources '
        'RETURN f.statement AS statement, score, procs, sources '
        'ORDER BY score DESC LIMIT $lim', {'kws': kws, 'lim': limit, 'min_score': min_score})
    if not rows:
        return []
    top = rows[0].get('score') or 0
    out, seen = [], set()
    for r in rows:
        stmt = (r.get('statement') or '').strip()
        # оставляем только сильнейший тир: score не ниже (макс − 1) — иначе в выводы попадает
        # случайный вывод, совпавший лишь по паре общих слов.
        if not stmt or stmt.lower() in seen or (r.get('score') or 0) < top - 1:
            continue
        seen.add(stmt.lower())
        procs = [p for p in (r.get('procs') or []) if p]
        srcs = [s for s in (r.get('sources') or []) if s and s.get('title')]
        out.append({'statement': stmt, 'process': procs[0] if procs else '', 'sources': len(srcs)})
    return out


def intent_conclusion(question: str, rows: list[dict], recs: dict | None = None,
                      answer: dict | None = None) -> dict | None:
    """Вывод под НАМЕРЕНИЕ вопроса: «какие методы» → перечислить методы, «какое оборудование» →
    оборудование, «кто/эксперт» → экспертов, «где/лаборатория» → предприятия, «какой материал»
    → материалы. Иначе ответ топикально верный, но не отвечает на конкретный вопрос (напр. вывод
    про сухой остаток на вопрос «какие методы подходят»)."""
    q = (question or '').lower()
    proc = ''
    for r in rows:
        proc = r.get('method') or r.get('process') or ''
        if proc:
            break
    proc = proc or 'процесс'

    def collect(key: str) -> list[str]:
        out: list[str] = []
        for r in rows:
            for v in (r.get(key) or []):
                v = (v or '').strip() if isinstance(v, str) else v
                if v and v not in out:
                    out.append(v)
        return out

    if any(k in q for k in ('оборудован', 'установк', 'аппарат', 'агрегат', ' печь', ' ванна', 'насос')):
        eq = collect('equipment')
        if eq:
            return {'statement': f'Для «{proc}» используют оборудование: ' + ', '.join(eq[:6]) + '.',
                    'process': proc, 'sources': 0}
    if any(k in q for k in ('реагент', 'материал', 'сырьё', 'сырье', 'из чего')):
        mat = collect('materials')
        if mat:
            return {'statement': f'В процессе «{proc}» используются материалы/реагенты: '
                                 + ', '.join(mat[:8]) + '.', 'process': proc, 'sources': 0}
    if any(k in q for k in ('эксперт', 'автор', 'специалист', 'кто ')):
        ex = (recs or {}).get('experts') or []
        if ex:
            return {'statement': 'Профильные эксперты по теме: ' + ', '.join(ex[:6]) + '.',
                    'process': proc, 'sources': 0}
    if any(k in q for k in ('лаборатор', 'предприят', 'завод', 'фабрик', 'где ')):
        fac = (recs or {}).get('facilities') or []
        if fac:
            return {'statement': 'Связанные лаборатории и предприятия: ' + ', '.join(fac[:6]) + '.',
                    'process': proc, 'sources': 0}
    # «какие методы/способы/технологии подходят» → прямой список применимых методов из ответа.
    if any(k in q for k in ('метод', 'способ', 'технолог', 'вариант', 'решени', 'подход', 'какие')):
        methods = [m.get('name') for m in ((answer or {}).get('consensus') or []) if m.get('name')]
        if not methods:
            methods = list(dict.fromkeys(process_names_from_rows(rows)))
        methods = [m for m in methods if m][:6]
        if methods:
            return {'statement': 'По запросу подходят методы/решения: ' + ', '.join(methods) + '.',
                    'process': methods[0], 'sources': 0}
    return None


def findings_from_rows(rows: list[dict], limit: int = 4) -> list[dict]:
    """Выводы найденных процессов из гидратированных строк (у каждого процесса свои Finding).
    Запасной источник вывода, когда прямой поиск по словам ничего не дал."""
    out, seen = [], set()
    for r in rows:
        proc = r.get('method') or r.get('process') or ''
        srcs = [s for s in (r.get('sources') or []) if s and s.get('title')]
        for st in (r.get('findings') or []):
            st = (st or '').strip()
            if st and st.lower() not in seen:
                seen.add(st.lower())
                out.append({'statement': st, 'process': proc, 'sources': len(srcs)})
    return out[:limit]


def process_names_from_rows(rows: list[dict]) -> list[str]:
    """Достать имена процессов из строк произвольного результата (метод/процесс/имя)."""
    out: list[str] = []
    for r in rows:
        v = r.get('method') or r.get('process') or r.get('name') or r.get('p.name')
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
    return out


def _keywords(question: str) -> list[str]:
    """Ключевые слова вопроса, обрезанные до префикса (грубый стемминг под русскую морфологию)."""
    words = re.findall(r'[А-Яа-яЁёA-Za-z]{4,}', question.lower())
    seen: dict[str, None] = {}
    for w in words:
        if w in _STOP:
            continue
        seen.setdefault(w[:6], None)  # префикс: 'электроэкстракции' и '...ция' → 'электр'
    return list(seen.keys())


def keyword_fallback(question: str) -> list[dict]:
    """Детерминированный поиск по графу без LLM (когда точный Cypher пуст или LLM недоступен).

    Идея: находим любые узлы, чьё имя/синонимы/параметр/заголовок/вывод совпали с ключевыми
    словами вопроса, затем собираем связанные с ними процессы (в радиусе 2) и их контекст —
    материалы, выводы, источники (с гео РФ/мир), числовые условия. Работает на seed-графе
    по всем четырём сценариям кейса и полностью офлайн.
    """
    kws = _keywords(question)
    if not kws:
        return []
    return graph.run(
        # 1) seed-узлы: совпадение ключевого слова по name / aliases / param / title / statement
        'MATCH (n) '
        'WHERE any(kw IN $kws WHERE toLower(coalesce(n.name, "")) CONTAINS kw) '
        '   OR any(kw IN $kws WHERE toLower(coalesce(n.param, "")) CONTAINS kw) '
        '   OR any(kw IN $kws WHERE toLower(coalesce(n.title, "")) CONTAINS kw) '
        '   OR any(kw IN $kws WHERE toLower(coalesce(n.statement, "")) CONTAINS kw) '
        '   OR any(kw IN $kws WHERE any(a IN coalesce(n.aliases, []) WHERE toLower(a) CONTAINS kw)) '
        'WITH collect(DISTINCT n) AS seeds '
        # 2) процессы: сам seed — процесс, либо процесс в радиусе 2 связей от seed
        'UNWIND seeds AS s '
        'MATCH (p:Process) WHERE p IN seeds OR (p)-[*1..2]-(s) '
        'WITH DISTINCT p '
        'OPTIONAL MATCH (p)-[:USES_MATERIAL|APPLIED_FOR|PRODUCES_OUTPUT]->(m:Material) '
        'OPTIONAL MATCH (p)-[:PRODUCES_OUTPUT]->(f:Finding) '
        'OPTIONAL MATCH (p)-[:DESCRIBED_IN]->(pub:Publication)-[:HAS_GEO]->(g:GeoContext) '
        'OPTIONAL MATCH (p)-[:OPERATES_AT_CONDITION]->(c:Condition) '
        'RETURN p.name AS method, '
        '       [x IN collect(DISTINCT m.name) WHERE x IS NOT NULL] AS materials, '
        '       [x IN collect(DISTINCT f.statement) WHERE x IS NOT NULL] AS findings, '
        '       [x IN collect(DISTINCT {title: pub.title, year: pub.year, geo: g.scope}) WHERE x.title IS NOT NULL] AS sources, '
        '       [x IN collect(DISTINCT {param: c.param, op: c.op, value: c.value, value2: c.value2, unit: c.unit}) WHERE x.param IS NOT NULL] AS conditions '
        'LIMIT 25',
        {'kws': kws},
    )

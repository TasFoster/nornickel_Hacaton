"""
Синтез структурированного ответа-«литобзора» из строк результата Cypher.

Берёт вопрос + данные из графа (JSON строк) и через LLM собирает ответ по фиксированной
схеме: метрики, консенсус, зоны разногласий, источники (с гео РФ/Мир и достоверностью).
Строгая валидация pydantic + детерминированный fallback, чтобы UI всегда получал корректную
структуру, даже если модель недоступна или вернула мусор.
"""
import json

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from knowledge.services.jsonutil import extract_json
from knowledge.services.llm import get_llm


class _Num(BaseModel):
    model_config = ConfigDict(extra='ignore')
    label: str
    value: str


class _Method(BaseModel):
    model_config = ConfigDict(extra='ignore')
    name: str
    note: str = ''
    desc: str = ''
    nums: list[_Num] = Field(default_factory=list)
    confidence: str = 'medium'
    sources: int = 0


class _Dispute(BaseModel):
    model_config = ConfigDict(extra='ignore')
    name: str
    note: str = ''
    desc: str = ''
    tag: str = ''


class _Source(BaseModel):
    model_config = ConfigDict(extra='ignore')
    kind: str = 'Источник'
    title: str
    year: int | None = None
    geo: str = ''
    confidence: str = 'medium'


class _Metrics(BaseModel):
    model_config = ConfigDict(extra='ignore')
    sources: int = 0
    confidence: str = '—'
    consensus: int = 0
    disputes: int = 0


class _Answer(BaseModel):
    model_config = ConfigDict(extra='ignore')
    metrics: _Metrics = Field(default_factory=_Metrics)
    consensus: list[_Method] = Field(default_factory=list)
    disputes: list[_Dispute] = Field(default_factory=list)
    sources: list[_Source] = Field(default_factory=list)


SYNTH_SYSTEM = """Ты — аналитик R&D в горно-металлургии. По вопросу пользователя и данным,
извлечённым из графа знаний (JSON строк результата запроса), собери структурированный
ответ-«литобзор». Верни СТРОГО JSON по схеме:
{
 "metrics": {"sources": <int>, "confidence": "Высокий|Средний|Низкий", "consensus": <int>, "disputes": <int>},
 "consensus": [{"name":"<метод/решение>","note":"<кратко>","desc":"<вывод по данным>",
               "nums":[{"label":"<параметр>","value":"<значение с единицей>"}],
               "confidence":"high|medium|low","sources":<int>}],
 "disputes": [{"name":"<предмет спора>","note":"<условие>","desc":"<в чём расхождение>","tag":"<напр. РФ ↔ Мир>"}],
 "sources": [{"kind":"<Статья|Отчёт|Патент|Диссертация>","title":"<название>","year":<int>,"geo":"РФ|Мир","confidence":"high|medium|low"}]
}
Правила: используй ТОЛЬКО данные из JSON, не выдумывай факты. Маппинг гео: 'domestic'→'РФ',
'foreign'→'Мир'. Если данных для раздела нет — пустой массив. Верни ТОЛЬКО JSON."""


# Значения-«пустышки», которые не должны попадать в UI как источник/метод.
_JUNK = {'', 'null', 'none', 'nan', 'n/a', '—', '-', 'нет', 'нет данных', 'unknown', 'undefined'}


def _is_junk(v) -> bool:
    return v is None or str(v).strip().lower() in _JUNK


# Пределы вывода — чтобы по широким темам не сыпать десятками карточек (демо-опрятность).
_MAX_METHODS = 8
_MAX_SOURCES = 12


def _clean(ans: dict) -> dict:
    """Убрать пустышки (методы без имени, источники без названия — напр. пустой OPTIONAL MATCH
    дал {title:null}), ограничить вывод топом и пересчитать метрики. Иначе в UI протекают
    карточки «NULL» и по широким запросам — десятки однотипных карточек."""
    srcs = [s for s in (ans.get('sources') or []) if not _is_junk(s.get('title'))]
    for s in srcs:  # год-пустышку не показываем
        if _is_junk(s.get('year')):
            s['year'] = None
    # свежее — выше; затем ограничиваем число источников
    srcs.sort(key=lambda s: (s.get('year') or 0), reverse=True)
    srcs = srcs[:_MAX_SOURCES]
    cons = [m for m in (ans.get('consensus') or []) if not _is_junk(m.get('name'))]
    # методы с бОльшим числом подтверждающих источников — выше; ограничиваем число методов
    cons.sort(key=lambda m: m.get('sources') or 0, reverse=True)
    cons = cons[:_MAX_METHODS]
    disp = [d for d in (ans.get('disputes') or []) if not _is_junk(d.get('name'))]
    met = dict(ans.get('metrics') or {})
    met['sources'], met['consensus'], met['disputes'] = len(srcs), len(cons), len(disp)
    ans.update({'sources': srcs, 'consensus': cons, 'disputes': disp, 'metrics': met})
    return ans


def synthesize(question: str, rows: list[dict]) -> dict:
    """Собрать структурированный ответ из строк графа. Никогда не бросает исключение."""
    if not rows:
        return _empty(question)
    payload = json.dumps(rows, ensure_ascii=False)[:6000]
    try:
        raw = get_llm().chat(
            system=SYNTH_SYSTEM,
            user=f'Вопрос: {question}\nДанные из графа (JSON):\n{payload}',
            max_tokens=2048,
        )
        data = extract_json(raw)
        if data:
            model = _Answer(**data)
            return _clean({'question': question, **model.model_dump()})
    except (ValidationError, Exception):  # noqa: BLE001 — синтез не должен ронять ответ
        pass
    return _clean(_fallback(question, rows))


def conclusion_from_answer(answer: dict) -> dict | None:
    """Синтез вывода, когда прямых Finding нет: чтобы у ЛЮБОГО непустого ответа был осмысленный
    вывод. Берём метод С СОДЕРЖАНИЕМ (описание/числа); если методов нет — вывод по источникам."""
    cons = answer.get('consensus') or []
    if cons:
        # предпочитаем метод, у которого есть описание или числа, иначе самый подтверждённый
        m = next((x for x in cons if x.get('desc') or x.get('nums')), cons[0])
        parts = []
        if m.get('desc'):
            parts.append(str(m['desc']).strip())
        nums = m.get('nums') or []
        if nums:
            parts.append('; '.join(f"{n.get('label')}: {n.get('value')}" for n in nums if n.get('value')))
        body = ' '.join(p for p in parts if p)
        stmt = (f'По запросу применим метод «{m.get("name")}»: {body}' if body
                else f'По данным графа, по запросу применим метод «{m.get("name")}» '
                     f'(подтверждён источниками: {m.get("sources", 0)}).')
        return {'statement': stmt, 'process': m.get('name', ''), 'sources': m.get('sources', 0)}
    srcs = answer.get('sources') or []
    if srcs:
        return {'statement': f'По запросу найдено {len(srcs)} источник(ов) по теме; '
                             f'отдельный метод в консенсусе не выделен — см. источники ниже.',
                'process': '', 'sources': len(srcs)}
    return None


def _empty(question: str) -> dict:
    return {
        'question': question,
        'metrics': {'sources': 0, 'confidence': '—', 'consensus': 0, 'disputes': 0},
        'consensus': [], 'disputes': [], 'sources': [],
    }


def _fallback(question: str, rows: list[dict]) -> dict:
    """Детерминированная сборка без LLM: методы и источники из типичных ключей.

    Дедуплицирует методы (по названию) и источники (по названию+году) — один и тот же
    процесс/публикация может встретиться в нескольких строках результата графа.
    """
    methods, sources = [], []
    seen_methods, seen_sources = set(), set()
    for r in rows:
        name = (r.get('method') or r.get('name') or r.get('process')
                or r.get('p.name') or r.get('process_name'))
        # источники этой строки (процесса)
        row_sources = []
        for key, val in r.items():
            if 'source' in key.lower() and isinstance(val, list):
                row_sources = [s for s in val if isinstance(s, dict) and s.get('title')]
        if name and str(name) not in seen_methods:
            seen_methods.add(str(name))
            methods.append({'name': str(name), 'note': '', 'desc': '', 'nums': [],
                            'confidence': 'medium', 'sources': len(row_sources)})
        for s in row_sources:
            skey = (s['title'], s.get('year'))
            if skey in seen_sources:
                continue
            seen_sources.add(skey)
            raw_geo = s.get('geo') or s.get('country') or ''
            geo = {'domestic': 'РФ', 'foreign': 'Мир'}.get(raw_geo, raw_geo)
            sources.append({'kind': 'Источник', 'title': s['title'],
                            'year': s.get('year'), 'geo': geo, 'confidence': 'medium'})
    return {
        'question': question,
        'metrics': {'sources': len(sources), 'confidence': 'Средний',
                    'consensus': len(methods), 'disputes': 0},
        'consensus': methods, 'disputes': [], 'sources': sources,
    }

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
            return {'question': question, **model.model_dump()}
    except (ValidationError, Exception):  # noqa: BLE001 — синтез не должен ронять ответ
        pass
    return _fallback(question, rows)


def _empty(question: str) -> dict:
    return {
        'question': question,
        'metrics': {'sources': 0, 'confidence': '—', 'consensus': 0, 'disputes': 0},
        'consensus': [], 'disputes': [], 'sources': [],
    }


def _fallback(question: str, rows: list[dict]) -> dict:
    """Детерминированная сборка без LLM: методы и источники из типичных ключей."""
    methods, sources = [], []
    for r in rows:
        name = r.get('method') or r.get('name') or r.get('p.name')
        if name:
            methods.append({'name': str(name), 'note': '', 'desc': '', 'nums': [],
                            'confidence': 'medium', 'sources': 0})
        for key, val in r.items():
            if 'source' in key.lower() and isinstance(val, list):
                for s in val:
                    if isinstance(s, dict) and s.get('title'):
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

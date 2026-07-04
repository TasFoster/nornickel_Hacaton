import type { AnswerData, Confidence } from '../types';
import { answerToMarkdown, answerToJsonLd, download } from '../lib/export';

function confPill(c: Confidence): { cls: string; label: string } {
  if (c === 'high') return { cls: 'pill hi dot', label: 'Высокая' };
  if (c === 'medium') return { cls: 'pill mid dot', label: 'Средняя' };
  return { cls: 'pill mid dot', label: 'Низкая' };
}

interface Props {
  answer: AnswerData;
  cypher?: string;
  onShowGraph: () => void;
}

export default function SearchAnswer({ answer, cypher, onShowGraph }: Props) {
  const ru = answer.sources.filter((s) => s.geo === 'РФ').length;
  const world = answer.sources.length - ru;
  const empty = answer.consensus.length === 0 && answer.disputes.length === 0 && answer.sources.length === 0;

  return (
    <section className="panel on">
      <div className="filters">
        <span className="flabel">Фильтры</span>
        <button className="chip on">Материал: вода <span className="x">×</span></button>
        <button className="chip on">Процесс: обессоливание <span className="x">×</span></button>
        <button className="chip geo-ru on">География: Россия <span className="x">×</span></button>
        <button className="chip">+ Мировая практика</button>
        <button className="chip on">Годы: 2019–2024 <span className="x">×</span></button>
        <button className="chip on">Достоверность: высокая+ <span className="x">×</span></button>
      </div>

      {cypher && (
        <div className="qcard" style={{ marginBottom: 14 }}>
          <div className="eyebrow">Сгенерированный запрос (NL → Cypher)</div>
          <pre style={{ fontFamily: 'var(--data)', fontSize: 12.5, color: 'var(--text)', whiteSpace: 'pre-wrap', margin: 0, overflowX: 'auto' }}>{cypher}</pre>
        </div>
      )}

      <div className="qcard">
        <div className="eyebrow">Запрос → синтез ответа</div>
        <div className="question">{answer.question}</div>
        <div className="summary">
          <div className="metric"><div className="mv">{answer.metrics.sources}</div><div className="ml">источников</div></div>
          <div className="metric"><div className="mv ok">{answer.metrics.confidence}</div><div className="ml">уровень достоверности</div></div>
          <div className="metric"><div className="mv">{answer.metrics.consensus}</div><div className="ml">метода в консенсусе</div></div>
          <div className="metric"><div className="mv warn">{answer.metrics.disputes}</div><div className="ml">зона разногласий</div></div>
        </div>
      </div>

      {empty && (
        <div className="qcard" style={{ borderLeft: '4px solid var(--warn)' }}>
          <div className="eyebrow" style={{ color: 'var(--warn)' }}>Ничего не найдено</div>
          <div style={{ fontSize: 14, color: 'var(--slate)' }}>
            По запросу в графе знаний не нашлось данных. Попробуйте переформулировать: назвать
            материал или процесс (напр. «электроэкстракция никеля», «обессоливание воды»),
            снять слишком узкие условия или убрать ограничение по географии.
            Сгенерированный Cypher показан выше — по нему видно, что именно искалось.
          </div>
        </div>
      )}
      {!empty && (<>
      <div className="block ok">
        <div className="head"><span className="sev" /><h3>Консенсус — применимые методы</h3><span className="count">{answer.consensus.length} метода</span></div>
        <div className="body"><div className="rows">
          {answer.consensus.map((m) => {
            const p = confPill(m.confidence);
            return (
              <div className="mrow" key={m.name}>
                <div className="name">{m.name}<small>{m.note}</small></div>
                <div className="desc">{m.desc}
                  <div className="nums">
                    {m.nums.map((n) => <span className="num" key={n.label}>{n.label}: <b>{n.value}</b></span>)}
                  </div>
                </div>
                <div className="badges"><span className={p.cls}>{p.label}</span><span className="geo">{m.sources} ист.</span></div>
              </div>
            );
          })}
        </div></div>
      </div>

      <div className="block warn">
        <div className="head"><span className="sev" /><h3>Зона разногласий</h3><span className="count">{answer.disputes.length} расхождение</span></div>
        <div className="body"><div className="rows">
          {answer.disputes.map((d) => (
            <div className="mrow" key={d.name}>
              <div className="name">{d.name}<small>{d.note}</small></div>
              <div className="desc">{d.desc}</div>
              <div className="badges"><span className="pill mid dot">Спорно</span><span className="geo">{d.tag}</span></div>
            </div>
          ))}
        </div></div>
      </div>

      <div className="sectlabel">Источники — {answer.sources.length} (Россия: {ru} · Мировая практика: {world})</div>
      <div className="srcgrid">
        {answer.sources.map((s) => {
          const p = confPill(s.confidence);
          return (
            <div className="src" key={s.title}>
              <span className="kind">{s.kind}</span>
              <span className="ttl">{s.title}</span>
              <div className="meta"><span className="yr">{s.year}</span><span className="geo">{s.geo}</span><span className={p.cls}>{p.label}</span></div>
            </div>
          );
        })}
      </div>

      <div className="actions">
        <button className="btn btn-primary" onClick={onShowGraph}>Показать в графе</button>
        <button className="btn btn-ghost" onClick={() => window.print()}>Экспорт PDF</button>
        <button className="btn btn-ghost" onClick={() => download('nornicel-otvet.md', answerToMarkdown(answer), 'text/markdown')}>Экспорт Markdown</button>
        <button className="btn btn-ghost" onClick={() => download('nornicel-otvet.jsonld', JSON.stringify(answerToJsonLd(answer), null, 2), 'application/ld+json')}>Экспорт JSON-LD</button>
      </div>
      </>)}
    </section>
  );
}

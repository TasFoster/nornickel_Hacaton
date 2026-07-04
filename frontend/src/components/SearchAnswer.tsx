import type { AnswerData, Confidence } from '../types';
import { answerToMarkdown, answerToJsonLd, download } from '../lib/export';

function confPill(c: Confidence): { cls: string; label: string } {
  if (c === 'high') return { cls: 'pill hi dot', label: 'Высокая' };
  if (c === 'medium') return { cls: 'pill mid dot', label: 'Средняя' };
  return { cls: 'pill mid dot', label: 'Низкая' };
}

interface Props {
  answer: AnswerData;
  onShowGraph: () => void;
}

export default function SearchAnswer({ answer, onShowGraph }: Props) {
  const ru = answer.sources.filter((s) => s.geo === 'РФ').length;
  const world = answer.sources.length - ru;
  const findings = answer.findings ?? [];
  const empty = answer.consensus.length === 0 && answer.disputes.length === 0
    && answer.sources.length === 0 && findings.length === 0;

  return (
    <section className="panel on">
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

      {!!findings.length && (
        <div className="block ok" style={{ marginBottom: 14 }}>
          <div className="head"><span className="sev" /><h3>Ключевые выводы по запросу</h3><span className="count">{findings.length}</span></div>
          <div className="body"><div className="rows">
            {findings.map((f, fi) => (
              <div className="mrow" key={fi}>
                <div className="name" style={{ minWidth: 0 }}>{f.process || 'вывод'}</div>
                <div className="desc">{f.statement}</div>
                <div className="badges"><span className="geo">{f.sources} ист.</span></div>
              </div>
            ))}
          </div></div>
        </div>
      )}

      {empty && (
        <div className="qcard" style={{ borderLeft: '4px solid var(--warn)' }}>
          <div className="eyebrow" style={{ color: 'var(--warn)' }}>Ничего не найдено</div>
          <div style={{ fontSize: 14, color: 'var(--slate)' }}>
            По запросу в графе знаний не нашлось данных. Попробуйте переформулировать: назвать
            материал или процесс (напр. «электроэкстракция никеля», «обессоливание воды»),
            снять слишком узкие условия или убрать ограничение по географии.
          </div>
        </div>
      )}
      {!empty && (<>
      <div className="block ok">
        <div className="head"><span className="sev" /><h3>Консенсус — применимые методы</h3><span className="count">{answer.consensus.length} метода</span></div>
        <div className="body"><div className="rows">
          {answer.consensus.map((m, mi) => {
            const p = confPill(m.confidence);
            return (
              <div className="mrow" key={mi}>
                <div className="name">{m.name}<small>{m.note}</small></div>
                <div className="desc">{m.desc}
                  <div className="nums">
                    {m.nums.map((n, ni) => <span className="num" key={ni}>{n.label}: <b>{n.value}</b></span>)}
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
          {answer.disputes.map((d, di) => (
            <div className="mrow" key={di}>
              <div className="name">{d.name}<small>{d.note}</small></div>
              <div className="desc">{d.desc}</div>
              <div className="badges"><span className="pill mid dot">Спорно</span><span className="geo">{d.tag}</span></div>
            </div>
          ))}
        </div></div>
      </div>

      {!!answer.gaps?.length && (
        <div className="qcard" style={{ borderLeft: '4px solid var(--warn)', marginBottom: 14 }}>
          <div className="eyebrow" style={{ color: 'var(--warn)' }}>Пробелы в знаниях</div>
          <ul style={{ margin: '6px 0 0', paddingLeft: 18, fontSize: 13.5, color: 'var(--slate)', lineHeight: 1.5 }}>
            {answer.gaps.map((g, gi) => <li key={gi}>{g}</li>)}
          </ul>
        </div>
      )}

      <div className="sectlabel">Источники — {answer.sources.length} (Россия: {ru} · Мировая практика: {world})</div>
      <div className="srcgrid">
        {answer.sources.map((s, si) => {
          const p = confPill(s.confidence);
          return (
            <div className="src" key={si}>
              <span className="kind">{s.kind}</span>
              <span className="ttl">{s.title}</span>
              <div className="meta"><span className="yr">{s.year}</span><span className="geo">{s.geo}</span><span className={p.cls}>{p.label}</span></div>
            </div>
          );
        })}
      </div>

      {(() => {
        const r = answer.recommendations;
        if (!r || (!r.experts.length && !r.facilities.length && !r.similar.length)) return null;
        const Row = ({ label, items }: { label: string; items: string[] }) =>
          items.length ? (
            <div style={{ marginTop: 8 }}>
              <span style={{ fontSize: 12, color: 'var(--slate)', marginRight: 8 }}>{label}:</span>
              {items.map((x, i) => (
                <span key={i} className="pill mid" style={{ marginRight: 6, marginBottom: 4, display: 'inline-block' }}>{x}</span>
              ))}
            </div>
          ) : null;
        return (
          <>
            <div className="sectlabel">Рекомендации</div>
            <div className="qcard">
              <Row label="Похожие кейсы" items={r.similar} />
              <Row label="Связанные лаборатории и предприятия" items={r.facilities} />
              <Row label="Эксперты" items={r.experts} />
            </div>
          </>
        );
      })()}

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

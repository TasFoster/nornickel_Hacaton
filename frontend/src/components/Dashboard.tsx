// Дашборд по ТЕКУЩЕМУ запросу: показатели выводятся из ответа синтеза и меняются под каждый
// вопрос (источники, методы, достоверность, РФ/мир, распределение по годам).
import type { CSSProperties } from 'react';
import type { AnswerData } from '../types';

const lead: CSSProperties = { margin: '0 0 16px', fontSize: 13.5, lineHeight: 1.5, color: 'var(--slate)' };
const hint: CSSProperties = { margin: '-2px 0 14px', fontSize: 12.5, lineHeight: 1.5, color: 'var(--slate)' };

function Bar({ label, val, pct, tone }: { label: string; val: string; pct: number; tone?: 'ru' | 'world' | 'low' }) {
  return (
    <div className="cov">
      <div className="top"><span className="dom">{label}</span><span className="val">{val}</span></div>
      <div className={tone === 'low' ? 'bar low' : 'bar'}>
        <span style={{ width: `${Math.max(3, Math.min(100, pct))}%`, background: tone === 'world' ? 'var(--slate)' : undefined }} />
      </div>
    </div>
  );
}

export default function Dashboard({ answer }: { answer: AnswerData }) {
  const src = answer.sources;
  const empty = answer.consensus.length === 0 && src.length === 0;
  const ru = src.filter((s) => s.geo === 'РФ').length;
  const world = src.length - ru;
  const total = src.length || 1;

  const byYear: Record<number, number> = {};
  src.forEach((s) => { if (s.year) byYear[s.year] = (byYear[s.year] || 0) + 1; });
  const years = Object.entries(byYear).map(([y, c]) => [Number(y), c] as [number, number]).sort((a, b) => a[0] - b[0]);
  const maxYear = Math.max(1, ...years.map(([, c]) => c));

  const methods = [...answer.consensus].sort((a, b) => (b.sources || 0) - (a.sources || 0));
  const maxM = Math.max(1, ...methods.map((m) => m.sources || 0));

  return (
    <section className="panel on">
      <p style={lead}>
        Аналитика по <b>текущему запросу</b> — панель пересчитывается под каждый вопрос из строки поиска.
      </p>

      {empty ? (
        <div className="card">
          <h3>Нет данных по запросу</h3>
          <p style={hint}>
            По текущему запросу в графе знаний ничего не нашлось — показывать нечего.
            Задайте вопрос в строке поиска (напр. «обессоливание воды», «электроэкстракция никеля»).
          </p>
        </div>
      ) : (
        <div className="dgrid">
          <div className="card">
            <h3>Ключевые показатели ответа</h3>
            <p style={hint}>Сводка по найденному: сколько источников, методов, общий уровень достоверности и есть ли разногласия.</p>
            <div className="summary" style={{ marginTop: 4 }}>
              <div className="metric"><div className="mv">{answer.metrics.sources}</div><div className="ml">источников</div></div>
              <div className="metric"><div className="mv ok">{answer.metrics.confidence}</div><div className="ml">достоверность</div></div>
              <div className="metric"><div className="mv">{answer.consensus.length}</div><div className="ml">методов</div></div>
              <div className="metric"><div className="mv warn">{answer.disputes.length}</div><div className="ml">разногласий</div></div>
            </div>
          </div>

          <div className="card">
            <h3>Отечественная vs мировая практика</h3>
            <p style={hint}>Как источники по этому запросу делятся на российские (РФ) и зарубежные.</p>
            <Bar label="Отечественная (РФ)" val={String(ru)} pct={(ru / total) * 100} tone="ru" />
            <Bar label="Мировая практика" val={String(world)} pct={(world / total) * 100} tone="world" />
          </div>

          <div className="card">
            <h3>Найденные методы</h3>
            <p style={hint}>Методы/решения из ответа и число подтверждающих источников у каждого.</p>
            {methods.length ? methods.map((m, i) => (
              <Bar key={i} label={m.name} val={`${m.sources} ист.`} pct={((m.sources || 0) / maxM) * 100} tone={(m.sources || 0) === 0 ? 'low' : undefined} />
            )) : <p style={hint}>Методы не выделены.</p>}
          </div>

          <div className="card">
            <h3>Источники по годам</h3>
            <p style={hint}>Распределение найденных источников по годам публикации — видно, насколько свежие данные.</p>
            {years.length ? years.map(([y, c]) => (
              <Bar key={y} label={String(y)} val={`${c}`} pct={(c / maxYear) * 100} />
            )) : <p style={hint}>Годы у источников не указаны.</p>}
          </div>
        </div>
      )}
    </section>
  );
}

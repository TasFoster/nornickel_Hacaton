import type { Tab } from '../App';

export default function NavRail({ tab, onTab }: { tab: Tab; onTab: (t: Tab) => void }) {
  return (
    <aside className="rail">
      <div className="brand">N</div>
      <button className={tab === 'search' ? 'on' : ''} title="Поиск" aria-label="Поиск" onClick={() => onTab('search')}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
      </button>
      <button className={tab === 'graph' ? 'on' : ''} title="Граф знаний" aria-label="Граф знаний" onClick={() => onTab('graph')}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="5" cy="6" r="2.4" /><circle cx="19" cy="6" r="2.4" /><circle cx="12" cy="18" r="2.4" /><path d="M7 7 10.5 16M17 7 13.5 16M7 6h10" /></svg>
      </button>
      <button className={tab === 'dash' ? 'on' : ''} title="Дашборд" aria-label="Дашборд" onClick={() => onTab('dash')}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M4 20V10M9 20V4M14 20v-7M19 20V8" /></svg>
      </button>
      <button title="Источники" aria-label="Источники">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M4 5.5A2 2 0 0 1 6 4h6l2 2h4a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z" /></svg>
      </button>
      <div className="sp" />
      <button title="Аудит и доступ" aria-label="Аудит и доступ">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 3 5 6v5c0 4.5 3 8 7 10 4-2 7-5.5 7-10V6z" /></svg>
      </button>
    </aside>
  );
}

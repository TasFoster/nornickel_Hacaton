interface Props {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  loading: boolean;
  live: boolean;
}

export default function TopBar({ value, onChange, onSubmit, loading, live }: Props) {
  return (
    <header className="topbar">
      <div className="wordmark">
        <b>Nornicel&nbsp;KG</b>
        <span>Карта знаний R&amp;D</span>
      </div>
      <label className="search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') onSubmit(); }}
          aria-label="Запрос на естественном языке"
          placeholder="Спросите на естественном языке…"
        />
        <kbd>Enter</kbd>
      </label>
      <span
        className={live ? 'pill hi dot' : 'pill mid dot'}
        title={live ? 'Запрос дошёл до backend' : 'Демо-данные (backend не отвечает или синтез не готов)'}
      >
        {live ? 'live' : 'демо'}
      </span>
      <button className="btn btn-primary" onClick={onSubmit} disabled={loading}>
        {loading ? 'Идёт…' : 'Найти'}
      </button>
    </header>
  );
}

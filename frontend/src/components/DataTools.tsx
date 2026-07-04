// Панель «Данные»: импорт документа (PDF/DOCX/XLSX/CSV/TXT/MD) и ручная корректировка графа
// экспертом. Закрывает требования «поддержка загрузки» и «ручная корректировка графа».
import { useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import { ingestDocument, addFact, type IngestResult } from '../api/client';

const hint: CSSProperties = { margin: '-2px 0 14px', fontSize: 12.5, lineHeight: 1.5, color: 'var(--slate)' };
const inp: CSSProperties = { width: '100%', padding: '9px 11px', fontSize: 13.5, border: '1px solid var(--line)', borderRadius: 8, marginBottom: 8, boxSizing: 'border-box' };

export default function DataTools() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [ingRes, setIngRes] = useState<IngestResult | null>(null);
  const [ingErr, setIngErr] = useState('');

  const [proc, setProc] = useState('');
  const [find, setFind] = useState('');
  const [geo, setGeo] = useState('');
  const [factMsg, setFactMsg] = useState('');
  const [factErr, setFactErr] = useState('');

  async function onUpload(file: File) {
    setBusy(true); setIngErr(''); setIngRes(null);
    try {
      setIngRes(await ingestDocument(file));
    } catch (e) {
      setIngErr(e instanceof Error ? e.message : 'Ошибка загрузки');
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  async function onAddFact() {
    setFactMsg(''); setFactErr('');
    if (!proc.trim() || !find.trim()) { setFactErr('Заполните процесс и вывод'); return; }
    setBusy(true);
    try {
      await addFact(proc.trim(), find.trim(), geo || undefined);
      setFactMsg('Факт добавлен в граф (провенанс: ручная правка эксперта).');
      setProc(''); setFind(''); setGeo('');
    } catch (e) {
      setFactErr(e instanceof Error ? e.message : 'Ошибка записи');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel on">
      <p style={{ margin: '0 0 16px', fontSize: 13.5, lineHeight: 1.5, color: 'var(--slate)' }}>
        Импорт источников в граф знаний и ручная корректировка данных экспертом.
      </p>
      <div className="dgrid">
        <div className="card">
          <h3>Загрузка документа</h3>
          <p style={hint}>
            Статьи, обзоры, отчёты, патенты, справочники. Форматы: <b>PDF, DOCX, XLSX, CSV, TXT, MD</b>.
            Документ проходит извлечение сущностей/связей/условий, нормализацию терминов и единиц,
            и добавляется в граф.
          </p>
          <input
            ref={fileRef} type="file" accept=".pdf,.docx,.xlsx,.csv,.txt,.md"
            disabled={busy}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) onUpload(f); }}
          />
          {busy && <p style={hint}>Обработка… (извлечение через LLM может занять несколько секунд)</p>}
          {ingErr && <p style={{ ...hint, color: 'var(--warn)' }}>Ошибка: {ingErr}</p>}
          {ingRes && (
            <div className="summary" style={{ marginTop: 12 }}>
              <div className="metric"><div className="mv">{ingRes.entities}</div><div className="ml">узлов</div></div>
              <div className="metric"><div className="mv">{ingRes.conditions}</div><div className="ml">условий</div></div>
              <div className="metric"><div className="mv">{ingRes.relations}</div><div className="ml">связей</div></div>
              <div className="metric"><div className="mv">{ingRes.chunks_processed}</div><div className="ml">фрагментов</div></div>
            </div>
          )}
          {ingRes && <p style={{ ...hint, marginTop: 8 }}>Загружен «{ingRes.file}» ({ingRes.format}).{ingRes.truncated ? ' Обработана первая часть (большой файл).' : ''}</p>}
        </div>

        <div className="card">
          <h3>Ручная корректировка экспертом</h3>
          <p style={hint}>Добавить проверенный вывод к процессу. Факт помечается провенансом «ручная правка» и высокой достоверностью.</p>
          <input style={inp} placeholder="Процесс (напр. флотация шлака)" value={proc} onChange={(e) => setProc(e.target.value)} disabled={busy} />
          <textarea style={{ ...inp, minHeight: 70, resize: 'vertical' }} placeholder="Вывод / рекомендация" value={find} onChange={(e) => setFind(e.target.value)} disabled={busy} />
          <select style={inp} value={geo} onChange={(e) => setGeo(e.target.value)} disabled={busy}>
            <option value="">География: не указана</option>
            <option value="domestic">Отечественная (РФ)</option>
            <option value="foreign">Мировая практика</option>
          </select>
          <button className="btn btn-primary" onClick={onAddFact} disabled={busy}>Добавить факт</button>
          {factMsg && <p style={{ ...hint, marginTop: 8, color: 'var(--ok, #1a7f4b)' }}>{factMsg}</p>}
          {factErr && <p style={{ ...hint, marginTop: 8, color: 'var(--warn)' }}>{factErr}</p>}
        </div>
      </div>
    </section>
  );
}

// Клиент backend-API. Запрос уходит на сервер (/api/query, /api/graph); при недоступности
// backend компоненты получают демо-структуру (MOCK_*), чтобы интерфейс не ломался.
import type { AnswerData, GraphData, GNode, GEdge, NodeType } from '../types';
import { MOCK_ANSWER, MOCK_GRAPH } from '../data/mock';

// В деве — относительный /api через прокси Vite; в проде задаётся VITE_API_BASE (URL бэкенда).
const BASE = (import.meta.env as unknown as Record<string, string | undefined>).VITE_API_BASE ?? '/api';

interface RawQueryResponse {
  question: string;
  cypher: string;
  rows: unknown[];
  answer?: AnswerData;
}

export interface QueryResult {
  answer: AnswerData;
  live: boolean;       // дошёл ли запрос до backend
  cypher?: string;     // сгенерированный NL→Cypher (если backend ответил)
}

export async function queryKnowledge(question: string): Promise<QueryResult> {
  try {
    const r = await fetch(`${BASE}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    if (!r.ok) throw new Error(`status ${r.status}`);
    const data = (await r.json()) as RawQueryResponse;
    // Если backend вернул синтезированный ответ — показываем его; иначе демо-структуру.
    const answer = data.answer && data.answer.metrics
      ? { ...data.answer, question }
      : { ...MOCK_ANSWER, question };
    return { answer, live: true, cypher: data.cypher };
  } catch {
    return { answer: { ...MOCK_ANSWER, question }, live: false };
  }
}

// --- Подграф вокруг узла: реальные данные из Neo4j (/api/graph?center=…) ---
const LABEL2TYPE: Record<string, NodeType> = {
  Material: 'material', Process: 'process', Equipment: 'equipment', Condition: 'condition',
  Finding: 'finding', Publication: 'publication', Expert: 'expert', Facility: 'equipment',
  Property: 'condition', GeoContext: 'condition', EconomicIndicator: 'finding',
};

interface RawNode { id: string; labels: string[]; name?: string; props?: Record<string, unknown> }
interface RawRel { type: string; start: string; end: string }

// Число строк подписи (тот же перенос, что в GraphView) и высота блока — для учёта размеров.
function lineCount(text: string, max = 15): number {
  const words = String(text).split(/\s+/).filter(Boolean);
  let lines = 0, cur = '';
  for (const w of words) {
    if (w.length > max) { if (cur) { lines++; cur = ''; } lines += Math.ceil(w.length / max); continue; }
    if (!cur) cur = w;
    else if ((cur + ' ' + w).length <= max) cur += ' ' + w;
    else { lines++; cur = w; }
  }
  if (cur) lines++;
  return Math.max(1, lines);
}
const boxH = (label: string, hasSub: boolean) => 12 + lineCount(label) * 14 + (hasSub ? 16 : 0);

// Силовая раскладка (Fruchterman–Reingold) + разведение прямоугольников блоков: связанные узлы
// притягиваются, все отталкиваются, затем накладывающиеся блоки раздвигаются — без перекрытий.
// Раскладка на большом «холсте»; масштаб под окно подбирается отдельно (fitView в GraphView).
function forceLayout(sizes: { w: number; h: number }[], edgeIdx: [number, number][]): { x: number; y: number }[] {
  const n = sizes.length;
  const CW = 1040, CH = 680;
  const pos = Array.from({ length: n }, (_, i) => {
    if (i === 0) return { x: CW / 2, y: CH / 2 };
    const a = (2 * Math.PI * (i - 1)) / Math.max(1, n - 1);
    return { x: CW / 2 + 240 * Math.cos(a), y: CH / 2 + 175 * Math.sin(a) };
  });
  if (n <= 1) return pos;
  const k = Math.sqrt((CW * CH) / n) * 0.7; // идеальная длина связи
  let temp = CW / 6;
  for (let it = 0; it < 300; it++) {
    const disp = pos.map(() => ({ x: 0, y: 0 }));
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
      const dx = pos[i].x - pos[j].x, dy = pos[i].y - pos[j].y, dd = Math.hypot(dx, dy) || 0.01;
      const f = (k * k) / dd, ux = dx / dd, uy = dy / dd; // отталкивание
      disp[i].x += ux * f; disp[i].y += uy * f; disp[j].x -= ux * f; disp[j].y -= uy * f;
    }
    for (const [a, b] of edgeIdx) {
      const dx = pos[a].x - pos[b].x, dy = pos[a].y - pos[b].y, dd = Math.hypot(dx, dy) || 0.01;
      const f = (dd * dd) / k, ux = dx / dd, uy = dy / dd; // притяжение вдоль связи
      disp[a].x -= ux * f; disp[a].y -= uy * f; disp[b].x += ux * f; disp[b].y += uy * f;
    }
    for (let i = 0; i < n; i++) { disp[i].x += (CW / 2 - pos[i].x) * 0.005; disp[i].y += (CH / 2 - pos[i].y) * 0.005; }
    for (let i = 0; i < n; i++) {
      const dl = Math.hypot(disp[i].x, disp[i].y) || 0.01;
      pos[i].x += (disp[i].x / dl) * Math.min(dl, temp);
      pos[i].y += (disp[i].y / dl) * Math.min(dl, temp);
    }
    temp *= 0.965; // охлаждение
  }
  // Разведение наложений блоков по их прямоугольникам — гарантия отсутствия перекрытий.
  const MG = 18;
  for (let it = 0; it < 80; it++) {
    let moved = false;
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
      const dx = pos[j].x - pos[i].x, dy = pos[j].y - pos[i].y;
      const ox = (sizes[i].w + sizes[j].w) / 2 + MG - Math.abs(dx);
      const oy = (sizes[i].h + sizes[j].h) / 2 + MG - Math.abs(dy);
      if (ox > 0 && oy > 0) {
        if (ox < oy) { const p = (ox / 2) * (dx < 0 ? -1 : 1); pos[i].x -= p; pos[j].x += p; }
        else { const p = (oy / 2) * (dy < 0 ? -1 : 1); pos[i].y -= p; pos[j].y += p; }
        moved = true;
      }
    }
    if (!moved) break;
  }
  return pos;
}

function mapSubgraph(d: { nodes?: RawNode[]; relationships?: RawRel[] }): GraphData {
  const VW = 640, VH = 400, W = 120;
  const raw = (d.nodes ?? []).slice(0, 16);
  // 1) метаданные узлов (подпись/тип/свойства) — без координат
  const metas = raw.map((n) => {
    const label0 = (n.labels ?? [])[0] ?? '';
    const type = LABEL2TYPE[label0] ?? 'process';
    const p = n.props ?? {};
    let label = String(n.name ?? p.title ?? p.name ?? p.param ?? p.key ?? n.id);
    let sub: string | undefined;
    if (label0 === 'Condition') {
      label = String(p.param ?? label);
      sub = (p.op === 'range' && p.value2 != null
        ? `${p.value}–${p.value2} ${p.unit ?? ''}`
        : `${p.op ?? ''}${p.value ?? ''} ${p.unit ?? ''}`).trim() || undefined;
    }
    else if (label0 === 'Publication') { label = String(p.title ?? label); sub = p.year ? String(p.year) : undefined; }
    else if (label0 === 'Finding') { label = 'Вывод'; sub = undefined; }  // полный текст вывода — в панели деталей
    else if (label0 === 'GeoContext') { label = String(p.country ?? ({ domestic: 'Россия', foreign: 'Мир' } as Record<string, string>)[String(p.scope)] ?? p.scope ?? label); }
    else if (label0 === 'EconomicIndicator') { sub = p.capex_opex ? String(p.capex_opex) : undefined; }
    // Полные значения свойств — панель деталей их переносит по словам.
    const props: [string, string][] = Object.entries(p).slice(0, 6).map(([k, v]) => [k, String(v ?? '')]);
    return { id: String(n.id), label, sub, type, props };
  });
  // 2) связи по индексам узлов — для раскладки и рендера
  const idx = new Map(metas.map((m, i) => [m.id, i]));
  const rels = (d.relationships ?? []).filter((r) => idx.has(String(r.start)) && idx.has(String(r.end)));
  const edgeIdx: [number, number][] = rels.map((r) => [idx.get(String(r.start))!, idx.get(String(r.end))!]);
  // 3) силовая раскладка с учётом размеров блоков → координаты левого-верхнего угла
  const sizes = metas.map((m) => ({ w: W, h: boxH(m.label, !!m.sub) }));
  const pos = forceLayout(sizes, edgeIdx);
  const nodes: GNode[] = metas.map((m, i) => ({
    ...m,
    x: Math.round(pos[i].x - sizes[i].w / 2),
    y: Math.round(pos[i].y - sizes[i].h / 2),
  }));
  const edges: GEdge[] = rels.map((r) => ({
    from: String(r.start), to: String(r.end),
    label: String(r.type ?? '').toLowerCase(),
    kind: r.type === 'CONTRADICTS' ? 'contra' as const : undefined,
  }));
  return { nodes, edges };
}

export async function fetchGraph(center: string): Promise<GraphData> {
  try {
    const r = await fetch(`${BASE}/graph?center=${encodeURIComponent(center)}`);
    if (!r.ok) throw new Error(`status ${r.status}`);
    const g = mapSubgraph(await r.json());
    return g.nodes.length ? g : MOCK_GRAPH;
  } catch {
    return MOCK_GRAPH;
  }
}

export async function checkHealth(): Promise<boolean> {
  try {
    const r = await fetch(`${BASE}/health`);
    return r.ok;
  } catch {
    return false;
  }
}

// --- Импорт документа: PDF/DOCX/XLSX/CSV/TXT/MD → пайплайн извлечения (POST /api/ingest) ---
export interface IngestResult {
  file: string; format: string; chunks_processed: number;
  entities: number; conditions: number; relations: number; truncated?: boolean;
}
export async function ingestDocument(file: File): Promise<IngestResult> {
  const fd = new FormData();
  fd.append('file', file);
  const r = await fetch(`${BASE}/ingest`, { method: 'POST', body: fd });
  const data = await r.json();
  if (!r.ok) throw new Error((data && data.error) || `Ошибка загрузки (${r.status})`);
  return data as IngestResult;
}

// --- Ручная корректировка графа экспертом (POST /api/fact) ---
export async function addFact(process: string, finding: string, geo?: string): Promise<void> {
  const r = await fetch(`${BASE}/fact`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ process, finding, geo }),
  });
  const data = await r.json();
  if (!r.ok) throw new Error((data && data.error) || `Ошибка записи (${r.status})`);
}

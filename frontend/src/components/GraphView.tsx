import { useEffect, useRef, useState } from 'react';
import type { PointerEvent as RPointerEvent } from 'react';
import { MOCK_GRAPH } from '../data/mock';
import type { GNode, NodeType, GraphData } from '../types';

const VW = 640, VH = 400, W = 120;
const PAD = 900; // запас «холста» вокруг базового окна — узлы можно таскать далеко
const ZMIN = 0.4, ZMAX = 3;

const TYPE: Record<NodeType, { fill: string; stroke: string; tx: string }> = {
  material: { fill: '#EAF1F8', stroke: '#1F5C8B', tx: '#1B2530' },
  process: { fill: '#FFFFFF', stroke: '#A96A38', tx: '#1B2530' },
  equipment: { fill: '#EEF2F7', stroke: '#54657A', tx: '#1B2530' },
  condition: { fill: '#F7EEDD', stroke: '#B0770C', tx: '#1B2530' },
  finding: { fill: '#E7F2EC', stroke: '#2E7D53', tx: '#2E7D53' },
  publication: { fill: '#EEF2F7', stroke: '#141E28', tx: '#1B2530' },
  expert: { fill: '#EEF2F7', stroke: '#141E28', tx: '#1B2530' },
};

const LINE_H = 14;
// Перенос подписи узла по словам (SVG-текст сам не переносится) — показываем текст целиком.
function wrapText(text: string, max = 15): string[] {
  const words = String(text).split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let cur = '';
  for (const w of words) {
    if (w.length > max) {
      if (cur) { lines.push(cur); cur = ''; }
      for (let i = 0; i < w.length; i += max) lines.push(w.slice(i, i + max));
      continue;
    }
    if (!cur) cur = w;
    else if ((cur + ' ' + w).length <= max) cur += ' ' + w;
    else { lines.push(cur); cur = w; }
  }
  if (cur) lines.push(cur);
  return lines.length ? lines : [''];
}
const labelLines = (n: GNode) => wrapText(n.label, 15);
const nodeH = (n: GNode) => 12 + labelLines(n).length * LINE_H + (n.sub ? LINE_H + 2 : 0);
const cx = (n: GNode) => n.x + W / 2;
const cy = (n: GNode) => n.y + nodeH(n) / 2;
const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

// Подобрать окно просмотра так, чтобы весь граф поместился в область с полями.
function fitView(ns: GNode[]) {
  if (!ns.length) return { x: 0, y: 0, k: 1 };
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const n of ns) {
    minX = Math.min(minX, n.x); minY = Math.min(minY, n.y);
    maxX = Math.max(maxX, n.x + W); maxY = Math.max(maxY, n.y + nodeH(n));
  }
  const pad = 48, w = maxX - minX + pad * 2, h = maxY - minY + pad * 2;
  const k = clamp(Math.min(VW / w, VH / h, 1.2), ZMIN, ZMAX);
  const ccx = (minX + maxX) / 2, ccy = (minY + maxY) / 2;
  return { x: ccx - (VW / k) / 2, y: ccy - (VH / k) / 2, k };
}

export default function GraphView({ data = MOCK_GRAPH }: { data?: GraphData }) {
  const fresh = () => data.nodes.map((n) => ({ ...n }));
  const [nodes, setNodes] = useState<GNode[]>(fresh);
  const [selected, setSelected] = useState<string>(data.nodes[0]?.id ?? '');
  const [hover, setHover] = useState<string | null>(null);
  const [view, setView] = useState(() => fitView(data.nodes)); // окно просмотра (пан + зум), под содержимое
  const svgRef = useRef<SVGSVGElement>(null);
  const drag = useRef<{ id: string; dx: number; dy: number; moved: boolean } | null>(null);
  const pan = useRef<{ sx: number; sy: number; vx: number; vy: number } | null>(null);

  const byId = (id: string) => nodes.find((n) => n.id === id);
  const active = hover ?? selected;
  const sel = byId(selected) ?? nodes[0];
  const edges = data.edges.filter((e) => byId(e.from) && byId(e.to));

  // Зум колесом мыши к позиции курсора (нативный слушатель — чтобы гасить прокрутку страницы).
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const p = svg.createSVGPoint(); p.x = e.clientX; p.y = e.clientY;
      const m = svg.getScreenCTM(); if (!m) return;
      const pt = p.matrixTransform(m.inverse());
      setView((v) => {
        const k = clamp(v.k * (e.deltaY < 0 ? 1.12 : 1 / 1.12), ZMIN, ZMAX);
        const rf = k / v.k;
        return { x: pt.x - (pt.x - v.x) / rf, y: pt.y - (pt.y - v.y) / rf, k };
      });
    };
    svg.addEventListener('wheel', onWheel, { passive: false });
    return () => svg.removeEventListener('wheel', onWheel);
  }, []);

  const zoomBy = (f: number) => setView((v) => {
    const k = clamp(v.k * f, ZMIN, ZMAX);
    const w = VW / v.k, h = VH / v.k, ccx = v.x + w / 2, ccy = v.y + h / 2;
    return { x: ccx - VW / k / 2, y: ccy - VH / k / 2, k };
  });
  const resetView = () => setView(fitView(nodes));

  function toSvg(e: RPointerEvent) {
    const svg = svgRef.current!;
    const p = svg.createSVGPoint();
    p.x = e.clientX; p.y = e.clientY;
    const m = svg.getScreenCTM();
    return m ? p.matrixTransform(m.inverse()) : ({ x: 0, y: 0 } as DOMPoint);
  }

  function onDown(e: RPointerEvent<SVGGElement>, n: GNode) {
    e.preventDefault();
    svgRef.current?.setPointerCapture(e.pointerId);
    const s = toSvg(e);
    drag.current = { id: n.id, dx: s.x - n.x, dy: s.y - n.y, moved: false };
  }

  // Клик по фону (не по узлу) — начать сдвиг (пан).
  function onSvgDown(e: RPointerEvent<SVGSVGElement>) {
    if (e.target !== svgRef.current) return;
    svgRef.current?.setPointerCapture(e.pointerId);
    pan.current = { sx: e.clientX, sy: e.clientY, vx: view.x, vy: view.y };
  }

  function onMove(e: RPointerEvent<SVGSVGElement>) {
    if (pan.current) {
      const rect = svgRef.current!.getBoundingClientRect();
      const sx = (VW / view.k) / rect.width, sy = (VH / view.k) / rect.height;
      const p = pan.current;
      setView((v) => ({ ...v, x: p.vx - (e.clientX - p.sx) * sx, y: p.vy - (e.clientY - p.sy) * sy }));
      return;
    }
    const d = drag.current;
    if (!d) return;
    const s = toSvg(e);
    // Большой «холст» — узлы можно таскать далеко за пределы базового окна (при отдалении
    // виден бо́льший белый лист); границы лишь страхуют от потери узла. Сброс — «Сбросить раскладку».
    const nx = Math.max(-PAD, Math.min(VW + PAD - W, s.x - d.dx));
    const ny = Math.max(-PAD, Math.min(VH + PAD, s.y - d.dy));
    const cur = byId(d.id);
    if (!cur) return;
    if (Math.abs(nx - cur.x) > 2 || Math.abs(ny - cur.y) > 2) d.moved = true;
    setNodes((ns) => ns.map((n) => (n.id === d.id ? { ...n, x: nx, y: ny } : n)));
  }

  function onUp(e: RPointerEvent<SVGSVGElement>) {
    if (pan.current) { svgRef.current?.releasePointerCapture(e.pointerId); pan.current = null; return; }
    const d = drag.current;
    if (!d) return;
    svgRef.current?.releasePointerCapture(e.pointerId);
    if (!d.moved) setSelected(d.id);
    drag.current = null;
  }

  if (!nodes.length) {
    return (
      <section className="panel on">
        <div className="graphwrap">
          <div style={{ padding: '48px 34px', color: 'var(--slate)', fontSize: 14, lineHeight: 1.5 }}>
            Для этого запроса в графе нет данных. Уточните формулировку — назовите материал или процесс
            (напр. «электроэкстракция никеля», «обессоливание воды»).
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="panel on">
      <div className="graphwrap">
        <div>
          <div className="gtoolbar">
            <button className="gbtn" onClick={() => setNodes(fresh())}>Сбросить раскладку</button>
            <button className="gbtn" onClick={() => zoomBy(1 / 1.2)} aria-label="Уменьшить масштаб">−</button>
            <span className="ghint" style={{ minWidth: 42, textAlign: 'center' }}>{Math.round(view.k * 100)}%</span>
            <button className="gbtn" onClick={() => zoomBy(1.2)} aria-label="Увеличить масштаб">+</button>
            <button className="gbtn" onClick={resetView}>Сбросить вид</button>
            <span className="ghint">колесо — масштаб · тяните фон — сдвиг · узлы — мышью</span>
          </div>
          <div className="canvas">
            <svg
              ref={svgRef} viewBox={`${view.x} ${view.y} ${VW / view.k} ${VH / view.k}`} width="100%" role="application"
              aria-label="Интерактивный граф знаний" style={{ display: 'block', touchAction: 'none', userSelect: 'none' }}
              onPointerDown={onSvgDown} onPointerMove={onMove} onPointerUp={onUp}
            >
              {edges.map((ed, i) => {
                const a = byId(ed.from)!, b = byId(ed.to)!;
                const hl = active === ed.from || active === ed.to;
                const cls = 'gedge' + (ed.kind === 'contra' ? ' contra' : '') + (hl ? ' hl' : '');
                return <line key={i} className={cls} x1={cx(a)} y1={cy(a)} x2={cx(b)} y2={cy(b)} />;
              })}
              {edges.map((ed, i) => {
                const a = byId(ed.from)!, b = byId(ed.to)!;
                return <text key={`l${i}`} className="elabel" x={(cx(a) + cx(b)) / 2} y={(cy(a) + cy(b)) / 2 - 4}>{ed.label}</text>;
              })}
              {nodes.map((n) => {
                const c = TYPE[n.type];
                const lines = labelLines(n);
                return (
                  <g
                    key={n.id} className={'gnode' + (n.id === selected ? ' sel' : '')} tabIndex={0}
                    transform={`translate(${n.x},${n.y})`}
                    onPointerDown={(e) => onDown(e, n)}
                    onPointerEnter={() => setHover(n.id)} onPointerLeave={() => setHover(null)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelected(n.id); } }}
                  >
                    <rect width={W} height={nodeH(n)} rx={7} fill={c.fill} stroke={c.stroke} />
                    <text className="lab" textAnchor="middle" fill={c.tx}>
                      {lines.map((ln, li) => <tspan key={li} x={W / 2} y={16 + li * LINE_H}>{ln}</tspan>)}
                    </text>
                    {n.sub && <text className="sub" x={W / 2} y={16 + lines.length * LINE_H} textAnchor="middle">{n.sub}</text>}
                  </g>
                );
              })}
            </svg>
          </div>
          <div className="legend">
            <span className="lg"><span className="sw" style={{ background: '#EAF1F8', border: '1px solid #1F5C8B' }} />Материал</span>
            <span className="lg"><span className="sw" style={{ background: '#fff', border: '1px solid #A96A38' }} />Процесс</span>
            <span className="lg"><span className="sw" style={{ background: '#EEF2F7', border: '1px solid #54657A' }} />Оборудование</span>
            <span className="lg"><span className="sw" style={{ background: '#F7EEDD', border: '1px solid #B0770C' }} />Условие</span>
            <span className="lg"><span className="sw" style={{ background: '#E7F2EC', border: '1px solid #2E7D53' }} />Вывод</span>
            <span className="lg"><span className="sw" style={{ background: 'var(--warn)' }} />Противоречие</span>
          </div>
        </div>
        <div>
          {sel && (
            <div className="aside">
              <h4>Узел: {sel.label}</h4>
              <div>
                {sel.props.map(([k, v]) => (
                  <div className="kv" key={k}><span className="k">{k}</span><span className="v">{v}</span></div>
                ))}
                {sel.gap && <div className="gap-note"><b>Пробел в знаниях</b>{sel.gap}</div>}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

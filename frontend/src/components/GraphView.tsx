import { useRef, useState } from 'react';
import type { PointerEvent as RPointerEvent } from 'react';
import { MOCK_GRAPH } from '../data/mock';
import type { GNode, NodeType } from '../types';

const VW = 640, VH = 400, W = 120, H = 44;

const TYPE: Record<NodeType, { fill: string; stroke: string; tx: string }> = {
  material: { fill: '#EAF1F8', stroke: '#1F5C8B', tx: '#1B2530' },
  process: { fill: '#FFFFFF', stroke: '#A96A38', tx: '#1B2530' },
  equipment: { fill: '#EEF2F7', stroke: '#54657A', tx: '#1B2530' },
  condition: { fill: '#F7EEDD', stroke: '#B0770C', tx: '#1B2530' },
  finding: { fill: '#E7F2EC', stroke: '#2E7D53', tx: '#2E7D53' },
  publication: { fill: '#EEF2F7', stroke: '#141E28', tx: '#1B2530' },
  expert: { fill: '#EEF2F7', stroke: '#141E28', tx: '#1B2530' },
};

const nodeH = (n: GNode) => (n.sub ? H : 40);
const cx = (n: GNode) => n.x + W / 2;
const cy = (n: GNode) => n.y + nodeH(n) / 2;
const fresh = () => MOCK_GRAPH.nodes.map((n) => ({ ...n }));

export default function GraphView() {
  const [nodes, setNodes] = useState<GNode[]>(fresh);
  const [selected, setSelected] = useState<string>('nf');
  const [hover, setHover] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const drag = useRef<{ id: string; dx: number; dy: number; moved: boolean } | null>(null);

  const byId = (id: string) => nodes.find((n) => n.id === id)!;
  const active = hover ?? selected;
  const sel = byId(selected);

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

  function onMove(e: RPointerEvent<SVGSVGElement>) {
    const d = drag.current;
    if (!d) return;
    const s = toSvg(e);
    const nx = Math.max(0, Math.min(VW - W, s.x - d.dx));
    const ny = Math.max(0, Math.min(VH - H, s.y - d.dy));
    const cur = byId(d.id);
    if (Math.abs(nx - cur.x) > 2 || Math.abs(ny - cur.y) > 2) d.moved = true;
    setNodes((ns) => ns.map((n) => (n.id === d.id ? { ...n, x: nx, y: ny } : n)));
  }

  function onUp(e: RPointerEvent<SVGSVGElement>) {
    const d = drag.current;
    if (!d) return;
    svgRef.current?.releasePointerCapture(e.pointerId);
    if (!d.moved) setSelected(d.id);
    drag.current = null;
  }

  return (
    <section className="panel on">
      <div className="graphwrap">
        <div>
          <div className="gtoolbar">
            <button className="gbtn" onClick={() => setNodes(fresh())}>Сбросить раскладку</button>
            <span className="ghint">Клик по узлу — детали справа · тяните узлы мышью · наведите — подсветка связей</span>
          </div>
          <div className="canvas">
            <svg
              ref={svgRef} viewBox={`0 0 ${VW} ${VH}`} width="100%" role="application"
              aria-label="Интерактивный граф знаний" style={{ display: 'block', touchAction: 'none', userSelect: 'none' }}
              onPointerMove={onMove} onPointerUp={onUp}
            >
              {MOCK_GRAPH.edges.map((ed, i) => {
                const a = byId(ed.from), b = byId(ed.to);
                const hl = active === ed.from || active === ed.to;
                const cls = 'gedge' + (ed.kind === 'contra' ? ' contra' : '') + (hl ? ' hl' : '');
                return <line key={i} className={cls} x1={cx(a)} y1={cy(a)} x2={cx(b)} y2={cy(b)} />;
              })}
              {MOCK_GRAPH.edges.map((ed, i) => {
                const a = byId(ed.from), b = byId(ed.to);
                return <text key={`l${i}`} className="elabel" x={(cx(a) + cx(b)) / 2} y={(cy(a) + cy(b)) / 2 - 4}>{ed.label}</text>;
              })}
              {nodes.map((n) => {
                const c = TYPE[n.type];
                return (
                  <g
                    key={n.id} className={'gnode' + (n.id === selected ? ' sel' : '')} tabIndex={0}
                    transform={`translate(${n.x},${n.y})`}
                    onPointerDown={(e) => onDown(e, n)}
                    onPointerEnter={() => setHover(n.id)} onPointerLeave={() => setHover(null)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelected(n.id); } }}
                  >
                    <rect width={W} height={nodeH(n)} rx={7} fill={c.fill} stroke={c.stroke} />
                    <text className="lab" x={W / 2} y={n.sub ? 19 : 24} textAnchor="middle" fill={c.tx}>{n.label}</text>
                    {n.sub && <text className="sub" x={W / 2} y={33} textAnchor="middle">{n.sub}</text>}
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
          <div className="aside">
            <h4>Узел: {sel.label}</h4>
            <div>
              {sel.props.map(([k, v]) => (
                <div className="kv" key={k}><span className="k">{k}</span><span className="v">{v}</span></div>
              ))}
              {sel.gap && <div className="gap-note"><b>Пробел в знаниях</b>{sel.gap}</div>}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

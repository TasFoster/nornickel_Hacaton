// Экспорт ответа в Markdown и JSON-LD (клиентская выгрузка). PDF — через печать браузера.
import type { AnswerData } from '../types';

function confRu(c: string): string {
  return c === 'high' ? 'высокая' : c === 'low' ? 'низкая' : 'средняя';
}

export function answerToMarkdown(a: AnswerData): string {
  const lines: string[] = [];
  lines.push(`# Литобзор: ответ на запрос`, '', `**Вопрос:** ${a.question}`, '');
  lines.push(
    `**Источников:** ${a.metrics.sources} · **Достоверность:** ${a.metrics.confidence} · ` +
    `**Консенсус:** ${a.metrics.consensus} · **Разногласий:** ${a.metrics.disputes}`,
    '',
  );
  if (a.consensus.length) {
    lines.push('## Консенсус — применимые методы', '');
    for (const m of a.consensus) {
      lines.push(`### ${m.name}${m.note ? ` — ${m.note}` : ''}`);
      if (m.desc) lines.push(m.desc);
      for (const n of m.nums) lines.push(`- ${n.label}: **${n.value}**`);
      lines.push(`- Достоверность: ${confRu(m.confidence)}; источников: ${m.sources}`, '');
    }
  }
  if (a.disputes.length) {
    lines.push('## Зоны разногласий', '');
    for (const d of a.disputes) lines.push(`- **${d.name}** (${d.tag}): ${d.desc}`);
    lines.push('');
  }
  if (a.sources.length) {
    lines.push('## Источники', '');
    for (const s of a.sources) {
      lines.push(`- [${s.geo}] ${s.title}${s.year ? ` (${s.year})` : ''} — ${s.kind}, достоверность ${confRu(s.confidence)}`);
    }
  }
  return lines.join('\n');
}

export function answerToJsonLd(a: AnswerData): object {
  return {
    '@context': { '@vocab': 'https://nornicel.example/schema#' },
    '@type': 'ResearchAnswer',
    question: a.question,
    overallConfidence: a.metrics.confidence,
    sourceCount: a.metrics.sources,
    methods: a.consensus.map((m) => ({
      '@type': 'Method', name: m.name, note: m.note, confidence: m.confidence,
      supportingSources: m.sources,
      parameters: m.nums.map((n) => ({ name: n.label, value: n.value })),
    })),
    disputes: a.disputes.map((d) => ({ '@type': 'Dispute', name: d.name, description: d.desc, scope: d.tag })),
    sources: a.sources.map((s) => ({
      '@type': 'ScholarlyArticle', name: s.title, datePublished: s.year,
      spatialCoverage: s.geo, confidence: s.confidence, genre: s.kind,
    })),
  };
}

export function download(filename: string, content: string, mime: string): void {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const el = document.createElement('a');
  el.href = url;
  el.download = filename;
  document.body.appendChild(el);
  el.click();
  el.remove();
  URL.revokeObjectURL(url);
}

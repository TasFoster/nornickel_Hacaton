// Клиент backend-API. Пока синтез структурированного ответа не готов (Фаза 2), запрос всё
// равно уходит на сервер (проверяем связь и получаем сгенерированный Cypher), а в UI
// показываем демо-структуру ответа. Как только backend начнёт возвращать синтез — здесь
// подставится реальный разбор, компоненты не изменятся.
import type { AnswerData, GraphData } from '../types';
import { MOCK_ANSWER, MOCK_GRAPH } from '../data/mock';

const BASE = '/api';

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

export async function fetchGraph(): Promise<GraphData> {
  // Фаза 2: GET /api/graph?center=…&depth=… Пока — демо-подграф.
  return MOCK_GRAPH;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const r = await fetch(`${BASE}/health`);
    return r.ok;
  } catch {
    return false;
  }
}

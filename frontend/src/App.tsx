import { useState } from 'react';
import NavRail from './components/NavRail';
import TopBar from './components/TopBar';
import SearchAnswer from './components/SearchAnswer';
import GraphView from './components/GraphView';
import Dashboard from './components/Dashboard';
import DataTools from './components/DataTools';
import { queryKnowledge, fetchGraph } from './api/client';
import { MOCK_ANSWER, MOCK_GRAPH } from './data/mock';
import type { AnswerData, GraphData } from './types';

export type Tab = 'search' | 'graph' | 'dash' | 'data';

export default function App() {
  const [tab, setTab] = useState<Tab>('search');
  const [input, setInput] = useState(MOCK_ANSWER.question);
  const [answer, setAnswer] = useState<AnswerData>(MOCK_ANSWER);
  const [live, setLive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [graph, setGraph] = useState<GraphData>(MOCK_GRAPH);
  const [graphKey, setGraphKey] = useState(0);

  async function runQuery() {
    if (!input.trim()) return;
    setLoading(true);
    const res = await queryKnowledge(input);
    setAnswer(res.answer);
    setLive(res.live);
    // Подгружаем подграф вокруг метода, наиболее РЕЛЕВАНТНОГО запросу (совпадение слов запроса
    // с названием метода важнее, число источников — лишь тай-брейк). Так граф отвечает вопросу.
    const kw = (input.toLowerCase().match(/[а-яёa-z]{4,}/gi) ?? []).map((w) => w.slice(0, 6));
    // Центр графа: процесс из ключевого вывода (он прямо отвечает на вопрос) приоритетнее, чем
    // просто совпавший по названию метод — иначе граф уходит в сторону (напр. «электролиз» меди
    // вместо «электроэкстракции никеля» из вывода про скорость католита).
    const fromFinding = res.answer.findings?.find((f) => f.process)?.process;
    const center = fromFinding
      ? fromFinding
      : res.answer.consensus.length
      ? res.answer.consensus
          .map((m) => ({ name: m.name, s: kw.filter((w) => m.name.toLowerCase().includes(w)).length * 100 + (m.sources || 0) }))
          .sort((a, b) => b.s - a.s)[0].name
      : undefined;
    // Граф всегда синхронен с ответом: есть результат — строим подграф; пусто — очищаем
    // (иначе оставался бы висеть граф от прошлого запроса и вводил в заблуждение).
    const g = center ? await fetchGraph(center) : { nodes: [], edges: [] };
    setGraph(g);
    setGraphKey((k) => k + 1);
    setLoading(false);
    setTab('search');
  }

  return (
    <div className="kg">
      <NavRail tab={tab} onTab={setTab} />
      <div className="work">
        <TopBar value={input} onChange={setInput} onSubmit={runQuery} loading={loading} live={live} />
        <nav className="tabs">
          <button className={tab === 'search' ? 'on' : ''} onClick={() => setTab('search')}>Поиск и ответ</button>
          <button className={tab === 'graph' ? 'on' : ''} onClick={() => setTab('graph')}>Граф знаний</button>
          <button className={tab === 'dash' ? 'on' : ''} onClick={() => setTab('dash')}>Дашборд</button>
          <button className={tab === 'data' ? 'on' : ''} onClick={() => setTab('data')}>Данные</button>
        </nav>
        <div className="scroll">
          {tab === 'search' && <SearchAnswer answer={answer} onShowGraph={() => setTab('graph')} />}
          {tab === 'graph' && <GraphView key={graphKey} data={graph} />}
          {tab === 'dash' && <Dashboard answer={answer} />}
          {tab === 'data' && <DataTools />}
          <div className="foot">
            <span>Nornicel R&amp;D Knowledge Graph — React</span>
            <span>Граф: Neo4j · Backend: Django + DRF · LLM: YandexGPT</span>
          </div>
        </div>
      </div>
    </div>
  );
}

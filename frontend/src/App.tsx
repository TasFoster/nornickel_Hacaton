import { useState } from 'react';
import NavRail from './components/NavRail';
import TopBar from './components/TopBar';
import SearchAnswer from './components/SearchAnswer';
import GraphView from './components/GraphView';
import Dashboard from './components/Dashboard';
import { queryKnowledge } from './api/client';
import { MOCK_ANSWER } from './data/mock';
import type { AnswerData } from './types';

export type Tab = 'search' | 'graph' | 'dash';

export default function App() {
  const [tab, setTab] = useState<Tab>('search');
  const [input, setInput] = useState(MOCK_ANSWER.question);
  const [answer, setAnswer] = useState<AnswerData>(MOCK_ANSWER);
  const [cypher, setCypher] = useState<string | undefined>(undefined);
  const [live, setLive] = useState(false);
  const [loading, setLoading] = useState(false);

  async function runQuery() {
    if (!input.trim()) return;
    setLoading(true);
    const res = await queryKnowledge(input);
    setAnswer(res.answer);
    setCypher(res.cypher);
    setLive(res.live);
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
        </nav>
        <div className="scroll">
          {tab === 'search' && <SearchAnswer answer={answer} cypher={cypher} onShowGraph={() => setTab('graph')} />}
          {tab === 'graph' && <GraphView />}
          {tab === 'dash' && <Dashboard />}
          <div className="foot">
            <span>Nornicel R&amp;D Knowledge Graph — React</span>
            <span>Граф: Neo4j · Backend: Django + DRF · LLM: YandexGPT</span>
          </div>
        </div>
      </div>
    </div>
  );
}

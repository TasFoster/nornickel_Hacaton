// Типы данных фронтенда: ответ синтеза и граф знаний.

export type Confidence = 'high' | 'medium' | 'low';
export type Geo = 'РФ' | 'Мир';

export interface MethodNum {
  label: string;
  value: string;
}

export interface ConsensusMethod {
  name: string;
  note: string;
  desc: string;
  nums: MethodNum[];
  confidence: Confidence;
  sources: number;
}

export interface Dispute {
  name: string;
  note: string;
  desc: string;
  tag: string;
}

export interface Source {
  kind: string;
  title: string;
  year: number;
  geo: Geo;
  confidence: Confidence;
}

export interface Recommendations {
  experts: string[];
  facilities: string[];
  similar: string[];
}

export interface KeyFinding {
  statement: string;
  process: string;
  sources: number;
}

export interface AnswerData {
  question: string;
  metrics: { sources: number; confidence: string; consensus: number; disputes: number };
  consensus: ConsensusMethod[];
  disputes: Dispute[];
  sources: Source[];
  findings?: KeyFinding[];
  gaps?: string[];
  recommendations?: Recommendations;
}

export type NodeType =
  | 'material' | 'process' | 'equipment' | 'condition' | 'finding' | 'publication' | 'expert';

export interface GNode {
  id: string;
  label: string;
  sub?: string;
  type: NodeType;
  x: number;
  y: number;
  props: [string, string][];
  gap?: string;
}

export interface GEdge {
  from: string;
  to: string;
  label: string;
  kind?: 'contra';
}

export interface GraphData {
  nodes: GNode[];
  edges: GEdge[];
}

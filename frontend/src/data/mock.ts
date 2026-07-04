// Демо-данные (сценарий кейса: обессоливание воды). Используются, пока backend не отдаёт
// синтезированный ответ (Фаза 2). Структура совпадает с типами API — при готовности синтеза
// клиент подставит реальные данные без изменения компонентов.
import type { AnswerData, GraphData } from '../types';

export const MOCK_ANSWER: AnswerData = {
  question:
    'Какие методы обессоливания воды подходят, если исходная вода содержит сульфаты, хлориды, Ca, Mg, Na по 200–300 мг/л, а требуемый сухой остаток — ≤ 1000 мг/дм³?',
  metrics: { sources: 14, confidence: 'Высокий', consensus: 3, disputes: 1 },
  consensus: [
    {
      name: 'Обратный осмос (RO)', note: 'обратноосмотическое обессоливание',
      desc: 'Наиболее универсальный метод при данной минерализации. Стабильно даёт сухой остаток ниже целевого.',
      nums: [
        { label: 'Сухой остаток после', value: '80–150 мг/дм³' },
        { label: 'Удаление SO₄²⁻', value: '97–99 %' },
      ],
      confidence: 'high', sources: 8,
    },
    {
      name: 'Нанофильтрация (NF)', note: 'для смягчения и снижения сульфатов',
      desc: 'Эффективна для многозарядных ионов (SO₄²⁻, Ca²⁺, Mg²⁺). Экономичнее RO по энергозатратам.',
      nums: [
        { label: 'Удаление SO₄²⁻', value: '90–98 %' },
        { label: 'Удаление Cl⁻', value: '20–50 %' },
      ],
      confidence: 'high', sources: 6,
    },
    {
      name: 'Ионный обмен', note: 'доочистка / умягчение',
      desc: 'Подходит как ступень доочистки; при данной концентрации самостоятельно — с высоким расходом реагентов.',
      nums: [
        { label: 'Целевой сухой остаток', value: '≤ 1000 мг/дм³' },
        { label: 'Роль', value: 'доочистка' },
      ],
      confidence: 'medium', sources: 4,
    },
  ],
  disputes: [
    {
      name: 'Целесообразность NF без RO', note: 'при сухом остатке у верхней границы',
      desc: 'Отчёт ГМК (2021) считает NF достаточной для достижения ≤ 1000 мг/дм³; зарубежная работа (2020) настаивает на связке NF→RO из-за проскока Cl⁻. Требуется пилот на реальной воде.',
      tag: 'РФ ↔ Мир',
    },
  ],
  sources: [
    { kind: 'Отчёт НИИ', title: 'Обессоливание оборотных вод обогатительной фабрики: пилотные испытания RO', year: 2023, geo: 'РФ', confidence: 'high' },
    { kind: 'Статья', title: 'Nanofiltration for sulfate removal in mine-affected water', year: 2020, geo: 'Мир', confidence: 'high' },
    { kind: 'Патент', title: 'Способ двухступенчатой очистки NF→RO с рекуперацией давления', year: 2021, geo: 'РФ', confidence: 'medium' },
    { kind: 'Диссертация', title: 'Ионообменное умягчение вод с высоким содержанием Ca/Mg', year: 2019, geo: 'РФ', confidence: 'medium' },
  ],
};

export const MOCK_GRAPH: GraphData = {
  nodes: [
    { id: 'cond', label: 'Сухой остаток', sub: '≤ 1000 мг/дм³', type: 'condition', x: 250, y: 14,
      props: [['Тип', 'Condition'], ['Параметр', 'dry_residue'], ['Ограничение', '≤ 1000 мг/дм³']] },
    { id: 'water', label: 'Вода', sub: 'SO₄ ≤ 300', type: 'material', x: 20, y: 182,
      props: [['Тип', 'Material'], ['SO₄²⁻', '200–300 мг/л'], ['Cl⁻', '200–300 мг/л'], ['Ca/Mg/Na', '200–300 мг/л']] },
    { id: 'ro', label: 'Обратный осмос', type: 'process', x: 250, y: 96,
      props: [['Тип', 'Process'], ['Удаление SO₄', '97–99 %'], ['Сухой остаток', '80–150 мг/дм³'], ['Источников', '8'], ['Достоверность', 'высокая']] },
    { id: 'nf', label: 'Нанофильтрация', type: 'process', x: 250, y: 182,
      props: [['Тип', 'Process'], ['Удаление SO₄', '90–98 %'], ['Удаление Cl⁻', '20–50 %'], ['Источников', '6'], ['Достоверность', 'высокая']],
      gap: 'Нет экспериментов: холодный климат + NF + оборотная вода фабрики.' },
    { id: 'ie', label: 'Ионный обмен', type: 'process', x: 250, y: 268,
      props: [['Тип', 'Process'], ['Роль', 'доочистка / умягчение'], ['Источников', '4'], ['Достоверность', 'средняя']] },
    { id: 'unit', label: 'RO-установка', type: 'equipment', x: 472, y: 96,
      props: [['Тип', 'Equipment'], ['Производительность', '100 м³/ч'], ['Рекуперация давления', 'да']] },
    { id: 'finding', label: 'Вывод', sub: 'остаток ≤ 1000', type: 'finding', x: 472, y: 196,
      props: [['Тип', 'Finding'], ['Эффект', 'сухой остаток ≤ 1000 мг/дм³'], ['Подтверждений', '12 из 14'], ['Достоверность', 'высокая']] },
  ],
  edges: [
    { from: 'water', to: 'ro', label: 'applied_for' },
    { from: 'water', to: 'nf', label: 'applied_for' },
    { from: 'water', to: 'ie', label: 'applied_for' },
    { from: 'ro', to: 'unit', label: 'uses_equipment' },
    { from: 'ro', to: 'finding', label: 'produces' },
    { from: 'nf', to: 'finding', label: 'produces' },
    { from: 'ro', to: 'cond', label: 'operates_at' },
    { from: 'nf', to: 'ie', label: 'contradicts', kind: 'contra' },
  ],
};

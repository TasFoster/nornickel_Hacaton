// Дашборд руководителя: покрытие знаний по доменам, зоны риска, активность, РФ vs мир.
// Пока на демо-метриках; подключается к аналитическим эндпоинтам в следующих фазах.

function Coverage({ dom, val, pct, low }: { dom: string; val: string; pct: number; low?: boolean }) {
  return (
    <div className="cov">
      <div className="top"><span className="dom">{dom}</span><span className="val">{val}</span></div>
      <div className={low ? 'bar low' : 'bar'}><span style={{ width: `${pct}%` }} /></div>
    </div>
  );
}

export default function Dashboard() {
  return (
    <section className="panel on">
      <div className="dgrid">
        <div className="card">
          <h3>Покрытие знаний по доменам</h3>
          <Coverage dom="Гидрометаллургия" val="312 источн. · 84%" pct={84} />
          <Coverage dom="Пирометаллургия" val="248 источн. · 71%" pct={71} />
          <Coverage dom="Экология и водоподготовка" val="176 источн. · 58%" pct={58} />
          <Coverage dom="Переработка отходов" val="54 источн. · 29%" pct={29} low />
        </div>

        <div className="card">
          <h3>Зоны риска</h3>
          <div className="risk-row">
            <div className="rt">Кучное выщелачивание в холодном климате<small>2 источника · нет экспериментов по выходу металла</small></div>
            <svg className="spark" viewBox="0 0 78 26"><polyline fill="none" stroke="#B23A2E" strokeWidth={1.8} points="0,20 13,18 26,21 39,17 52,19 65,22 78,20" /></svg>
            <span className="tag crit">пробел</span>
          </div>
          <div className="risk-row">
            <div className="rt">Оптимальная скорость циркуляции католита<small>противоречие: 0.1 vs 0.3 м/с</small></div>
            <svg className="spark" viewBox="0 0 78 26"><polyline fill="none" stroke="#B0770C" strokeWidth={1.8} points="0,8 13,14 26,7 39,16 52,9 65,15 78,10" /></svg>
            <span className="tag warn">разногласие</span>
          </div>
          <div className="risk-row">
            <div className="rt">Закачка шахтных вод в глубокие горизонты<small>мало ТЭП по зарубежной практике</small></div>
            <svg className="spark" viewBox="0 0 78 26"><polyline fill="none" stroke="#B0770C" strokeWidth={1.8} points="0,18 13,16 26,15 39,13 52,14 65,11 78,9" /></svg>
            <span className="tag warn">низкое покрытие</span>
          </div>
        </div>

        <div className="card">
          <h3>Активность направлений</h3>
          <Coverage dom="Новые публикации за 30 дней" val="+37" pct={62} />
          <Coverage dom="Эксперименты в работе" val="18" pct={45} />
          <Coverage dom="Верифицировано экспертами" val="92%" pct={92} />
        </div>

        <div className="card">
          <h3>Отечественная vs мировая практика</h3>
          <Coverage dom="Обессоливание воды" val="РФ 9 · Мир 5" pct={64} />
          <Coverage dom="Электроэкстракция Ni" val="РФ 21 · Мир 34" pct={38} />
          <Coverage dom="Au/Ag/МПГ: штейн↔шлак" val="РФ 15 · Мир 12" pct={56} />
        </div>
      </div>
    </section>
  );
}

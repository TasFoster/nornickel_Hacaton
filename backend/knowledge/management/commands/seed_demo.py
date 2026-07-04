"""
Наполнение графа связным демо-набором по кейсу (обессоливание воды + электроэкстракция
никеля), чтобы сквозные запросы возвращали осмысленный результат до загрузки реального
корпуса. Идемпотентно (MERGE). Запуск: python manage.py seed_demo
"""
from django.core.management.base import BaseCommand

from knowledge.services import graph

# Каждый statement — отдельный MERGE-блок. Провенанс проставляется на узлах/выводах.
CYPHER = [
    # --- География ---
    "MERGE (g:GeoContext {scope:'domestic'}) SET g.country='Россия'",
    "MERGE (g:GeoContext {scope:'foreign'}) SET g.country='Мировая практика'",

    # --- Материалы ---
    "MERGE (m:Material {name:'вода'}) SET m.category='water'",
    "MERGE (m:Material {name:'никель'}) SET m.formula='Ni', m.category='metal'",
    "MERGE (m:Material {name:'католит'}) SET m.category='electrolyte'",

    # --- Процессы обессоливания (domain water_treatment) ---
    "MERGE (p:Process {name:'обратный осмос'}) SET p.domain='water_treatment', p.aliases=['reverse osmosis','RO']",
    "MERGE (p:Process {name:'нанофильтрация'}) SET p.domain='water_treatment', p.aliases=['nanofiltration','NF']",
    "MERGE (p:Process {name:'ионный обмен'}) SET p.domain='water_treatment', p.aliases=['ion exchange']",
    "MERGE (p:Process {name:'электроэкстракция никеля'}) SET p.domain='hydrometallurgy', p.aliases=['electrowinning']",

    # --- Условия (числовые ограничения) ---
    "MERGE (c:Condition {key:'dry_residue|<=|1000|мг/л'}) SET c.param='dry_residue', c.op='<=', c.value=1000, c.unit='мг/л'",
    "MERGE (c:Condition {key:'sulfates|<=|300|мг/л'}) SET c.param='sulfates', c.op='<=', c.value=300, c.unit='мг/л'",
    "MERGE (c:Condition {key:'flow_rate|=|0.15|м/с'}) SET c.param='flow_rate', c.op='=', c.value=0.15, c.unit='м/с'",

    # --- Оборудование ---
    "MERGE (e:Equipment {name:'RO-установка'}) SET e.type='membrane'",
    "MERGE (e:Equipment {name:'ванна электроэкстракции'}) SET e.type='cell'",

    # --- Публикации (РФ и мир, разные годы) ---
    "MERGE (p:Publication {id:'pub-ro-2023'}) SET p.title='Обессоливание оборотных вод обогатительной фабрики: пилотные испытания RO', p.year=2023, p.type='report', p.lang='ru', p.source_ref='НИИ-2023', p.confidence='high'",
    "MERGE (p:Publication {id:'pub-nf-2020'}) SET p.title='Nanofiltration for sulfate removal in mine-affected water', p.year=2020, p.type='article', p.lang='en', p.source_ref='DOI:10.1016/nf2020', p.confidence='high'",
    "MERGE (p:Publication {id:'pub-ie-2019'}) SET p.title='Ионообменное умягчение вод с высоким содержанием Ca/Mg', p.year=2019, p.type='thesis', p.lang='ru', p.source_ref='Дисс-2019', p.confidence='medium'",
    "MERGE (p:Publication {id:'pub-ni-2022'}) SET p.title='Циркуляция католита при электроэкстракции никеля', p.year=2022, p.type='article', p.lang='ru', p.source_ref='ЦветМет-2022', p.confidence='high'",

    # --- Выводы ---
    "MERGE (f:Finding {id:'find-dry-1000'}) SET f.statement='RO и NF стабильно достигают сухого остатка ≤ 1000 мг/дм³ при исходной минерализации 200–300 мг/л', f.confidence='high', f.evidence_count=12",
    "MERGE (f:Finding {id:'find-nf-dispute'}) SET f.statement='NF без RO достаточна для ≤1000 мг/дм³', f.confidence='medium', f.evidence_count=2",
    "MERGE (f:Finding {id:'find-nf-need-ro'}) SET f.statement='NF требует ступени RO из-за проскока Cl⁻', f.confidence='medium', f.evidence_count=2",

    # --- Связи: процесс → материал / условие / оборудование ---
    "MATCH (p:Process {name:'обратный осмос'}),(m:Material {name:'вода'}) MERGE (p)-[:APPLIED_FOR]->(m)",
    "MATCH (p:Process {name:'нанофильтрация'}),(m:Material {name:'вода'}) MERGE (p)-[:APPLIED_FOR]->(m)",
    "MATCH (p:Process {name:'ионный обмен'}),(m:Material {name:'вода'}) MERGE (p)-[:APPLIED_FOR]->(m)",
    "MATCH (p:Process {name:'обратный осмос'}),(c:Condition {key:'dry_residue|<=|1000|мг/л'}) MERGE (p)-[:OPERATES_AT_CONDITION]->(c)",
    "MATCH (p:Process {name:'нанофильтрация'}),(c:Condition {key:'dry_residue|<=|1000|мг/л'}) MERGE (p)-[:OPERATES_AT_CONDITION]->(c)",
    "MATCH (p:Process {name:'нанофильтрация'}),(c:Condition {key:'sulfates|<=|300|мг/л'}) MERGE (p)-[:OPERATES_AT_CONDITION]->(c)",
    "MATCH (p:Process {name:'ионный обмен'}),(c:Condition {key:'dry_residue|<=|1000|мг/л'}) MERGE (p)-[:OPERATES_AT_CONDITION]->(c)",
    "MATCH (p:Process {name:'электроэкстракция никеля'}),(c:Condition {key:'flow_rate|=|0.15|м/с'}) MERGE (p)-[:OPERATES_AT_CONDITION]->(c)",
    "MATCH (p:Process {name:'обратный осмос'}),(e:Equipment {name:'RO-установка'}) MERGE (p)-[:USES_EQUIPMENT]->(e)",
    "MATCH (p:Process {name:'электроэкстракция никеля'}),(m:Material {name:'католит'}) MERGE (p)-[:USES_MATERIAL]->(m)",
    "MATCH (p:Process {name:'электроэкстракция никеля'}),(e:Equipment {name:'ванна электроэкстракции'}) MERGE (p)-[:USES_EQUIPMENT]->(e)",

    # --- Связи: процесс → публикация → география ---
    "MATCH (p:Process {name:'обратный осмос'}),(pub:Publication {id:'pub-ro-2023'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (p:Process {name:'нанофильтрация'}),(pub:Publication {id:'pub-nf-2020'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (p:Process {name:'ионный обмен'}),(pub:Publication {id:'pub-ie-2019'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (p:Process {name:'электроэкстракция никеля'}),(pub:Publication {id:'pub-ni-2022'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (pub:Publication {id:'pub-ro-2023'}),(g:GeoContext {scope:'domestic'}) MERGE (pub)-[:HAS_GEO]->(g)",
    "MATCH (pub:Publication {id:'pub-nf-2020'}),(g:GeoContext {scope:'foreign'}) MERGE (pub)-[:HAS_GEO]->(g)",
    "MATCH (pub:Publication {id:'pub-ie-2019'}),(g:GeoContext {scope:'domestic'}) MERGE (pub)-[:HAS_GEO]->(g)",
    "MATCH (pub:Publication {id:'pub-ni-2022'}),(g:GeoContext {scope:'domestic'}) MERGE (pub)-[:HAS_GEO]->(g)",

    # --- Связи: выводы, валидация, противоречие ---
    "MATCH (p:Process {name:'обратный осмос'}),(f:Finding {id:'find-dry-1000'}) MERGE (p)-[:PRODUCES_OUTPUT]->(f)",
    "MATCH (f:Finding {id:'find-dry-1000'}),(pub:Publication {id:'pub-ro-2023'}) MERGE (f)-[:VALIDATED_BY]->(pub)",
    "MATCH (a:Finding {id:'find-nf-dispute'}),(b:Finding {id:'find-nf-need-ro'}) MERGE (a)-[:CONTRADICTS]->(b)",

    # --- Циркуляция католита: мировая практика + оптимальная скорость (сценарий 2) ---
    "MERGE (p:Process {name:'принудительная циркуляция католита насосом'}) SET p.domain='hydrometallurgy'",
    "MERGE (p:Process {name:'циркуляция католита через теплообменник'}) SET p.domain='hydrometallurgy'",
    "MERGE (pub:Publication {id:'pub-cat-foreign-2021'}) SET pub.title='Catholyte circulation regimes in nickel electrowinning', pub.year=2021, pub.type='article', pub.lang='en', pub.source_ref='DOI:10.1016/hydromet.2021', pub.confidence='high'",
    "MERGE (pub:Publication {id:'pub-cat-foreign-2019'}) SET pub.title='Optimal electrolyte flow velocity for cathode quality in Ni EW', pub.year=2019, pub.type='article', pub.lang='en', pub.source_ref='DOI:10.1149/2019.ew', pub.confidence='medium'",
    "MERGE (c:Condition {key:'flow_rate|range|0.1|м/с'}) SET c.param='flow_rate', c.op='range', c.value=0.1, c.value2=0.3, c.unit='м/с'",
    "MERGE (f:Finding {id:'find-flow-optimal'}) SET f.statement='Оптимальная скорость циркуляции католита при электроэкстракции никеля — 0.1–0.3 м/с (типично ~0.2 м/с); равномерная принудительная циркуляция улучшает качество катодного осадка', f.confidence='high', f.evidence_count=5",
    # связи католит-сценария
    "MATCH (p:Process {name:'электроэкстракция никеля'}),(pub:Publication {id:'pub-cat-foreign-2021'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (p:Process {name:'электроэкстракция никеля'}),(pub:Publication {id:'pub-cat-foreign-2019'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (pub:Publication {id:'pub-cat-foreign-2021'}),(g:GeoContext {scope:'foreign'}) MERGE (pub)-[:HAS_GEO]->(g)",
    "MATCH (pub:Publication {id:'pub-cat-foreign-2019'}),(g:GeoContext {scope:'foreign'}) MERGE (pub)-[:HAS_GEO]->(g)",
    "MATCH (p:Process {name:'электроэкстракция никеля'}),(c:Condition {key:'flow_rate|range|0.1|м/с'}) MERGE (p)-[:OPERATES_AT_CONDITION]->(c)",
    "MATCH (p:Process {name:'электроэкстракция никеля'}),(f:Finding {id:'find-flow-optimal'}) MERGE (p)-[:PRODUCES_OUTPUT]->(f)",
    "MATCH (f:Finding {id:'find-flow-optimal'}),(pub:Publication {id:'pub-cat-foreign-2021'}) MERGE (f)-[:VALIDATED_BY]->(pub)",
    "MATCH (f:Finding {id:'find-flow-optimal'}),(pub:Publication {id:'pub-ni-2022'}) MERGE (f)-[:VALIDATED_BY]->(pub)",
    "MATCH (p:Process {name:'принудительная циркуляция католита насосом'}),(m:Material {name:'католит'}) MERGE (p)-[:USES_MATERIAL]->(m)",
    "MATCH (p:Process {name:'циркуляция католита через теплообменник'}),(m:Material {name:'католит'}) MERGE (p)-[:USES_MATERIAL]->(m)",
    "MATCH (p:Process {name:'принудительная циркуляция католита насосом'}),(pub:Publication {id:'pub-cat-foreign-2021'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (p:Process {name:'циркуляция католита через теплообменник'}),(pub:Publication {id:'pub-ni-2022'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (p:Process {name:'принудительная циркуляция католита насосом'}),(c:Condition {key:'flow_rate|range|0.1|м/с'}) MERGE (p)-[:OPERATES_AT_CONDITION]->(c)",

    # =====================================================================
    #  СЦЕНАРИЙ 3: распределение Au / Ag / МПГ между штейном и шлаком (5 лет)
    #  Источники: реальные публикации (Springer, Google Patents, CyberLeninka)
    #  и статьи корпуса кейса (журналы «Цветные металлы», «Обогащение руд»).
    # =====================================================================
    # --- Материалы ---
    "MERGE (m:Material {name:'золото'}) SET m.formula='Au', m.category='precious_metal', m.aliases=['Au','gold']",
    "MERGE (m:Material {name:'серебро'}) SET m.formula='Ag', m.category='precious_metal', m.aliases=['Ag','silver']",
    "MERGE (m:Material {name:'МПГ'}) SET m.category='precious_metal', m.aliases=['платиноиды','платина','палладий','родий','Pt','Pd','Rh','PGM','platinum group metals']",
    "MERGE (m:Material {name:'медный штейн'}) SET m.category='matte', m.aliases=['copper matte']",
    "MERGE (m:Material {name:'никелевый штейн'}) SET m.category='matte', m.aliases=['nickel matte']",
    "MERGE (m:Material {name:'шлак'}) SET m.category='slag', m.aliases=['отвальный шлак','конвертерный шлак','slag']",
    # --- Процессы ---
    "MERGE (p:Process {name:'плавка на штейн'}) SET p.domain='pyrometallurgy', p.aliases=['matte smelting','плавка']",
    "MERGE (p:Process {name:'обеднение шлака'}) SET p.domain='pyrometallurgy', p.aliases=['slag cleaning','slag depletion']",
    "MERGE (p:Process {name:'флотация шлака'}) SET p.domain='mineral_processing', p.aliases=['slag flotation']",
    "MERGE (p:Process {name:'грануляция штейна'}) SET p.domain='pyrometallurgy', p.aliases=['matte granulation']",
    # --- Условия (числовые) ---
    "MERGE (c:Condition {key:'temperature|range|1250|°C'}) SET c.param='temperature', c.op='range', c.value=1250, c.value2=1350, c.unit='°C'",
    "MERGE (c:Condition {key:'pgm_recovery_matte|>=|85|%'}) SET c.param='pgm_recovery_matte', c.op='>=', c.value=85, c.unit='%'",
    "MERGE (c:Condition {key:'pgm_loss_slag|<=|1|%'}) SET c.param='pgm_loss_slag', c.op='<=', c.value=1, c.unit='%'",
    # --- Публикации (мировая практика) ---
    "MERGE (pub:Publication {id:'pub-pgm-cu-2019'}) SET pub.title='Distribution of Ni, Co, Precious, and Platinum Group Metals in Copper Making Process', pub.year=2019, pub.type='article', pub.lang='en', pub.doi='10.1007/s11663-019-01576-2', pub.source_ref='Metallurgical and Materials Transactions B', pub.platform='Springer', pub.url='https://link.springer.com/article/10.1007/s11663-019-01576-2', pub.confidence='high'",
    "MERGE (pub:Publication {id:'pub-pgm-slag-2015'}) SET pub.title='Equilibrium Distribution of Precious Metals Between Slag and Copper Matte at 1250-1350 C', pub.year=2015, pub.type='article', pub.lang='en', pub.doi='10.1007/s40831-015-0020-x', pub.source_ref='Journal of Sustainable Metallurgy', pub.platform='Springer', pub.url='https://link.springer.com/article/10.1007/s40831-015-0020-x', pub.confidence='high'",
    "MERGE (pub:Publication {id:'pub-pgm-patent-2003'}) SET pub.title='Process for extracting platinum group metals (WO2003087416A1)', pub.year=2003, pub.type='patent', pub.lang='en', pub.source_ref='WO2003087416A1', pub.platform='Google Patents', pub.url='https://patents.google.com/patent/WO2003087416A1/en', pub.confidence='medium'",
    # --- Публикации (отечественная практика: корпус кейса + CyberLeninka) ---
    "MERGE (pub:Publication {id:'pub-pgm-kgmk-2023'}) SET pub.title='Повышение селективности концентратов МПГ в химико-металлургическом цехе КГМК', pub.year=2023, pub.type='article', pub.lang='ru', pub.source_ref='Цветные металлы', pub.platform='eLibrary', pub.confidence='high'",
    "MERGE (pub:Publication {id:'pub-agpt-2023'}) SET pub.title='Анализ аффинированных серебра и платины', pub.year=2023, pub.type='article', pub.lang='ru', pub.source_ref='Цветные металлы', pub.platform='eLibrary', pub.confidence='high'",
    "MERGE (pub:Publication {id:'pub-matte-gran-2022'}) SET pub.title='Исследование процесса грануляции медно-никелевых штейнов', pub.year=2022, pub.type='article', pub.lang='ru', pub.source_ref='Цветные металлы', pub.platform='eLibrary', pub.confidence='medium'",
    "MERGE (pub:Publication {id:'pub-slag-depl-2024'}) SET pub.title='Влияние температурного режима процесса обеднения шлака на коалесценцию частиц металлической фазы', pub.year=2024, pub.type='article', pub.lang='ru', pub.source_ref='Обогащение руд', pub.platform='eLibrary', pub.confidence='high'",
    "MERGE (pub:Publication {id:'pub-slag-flot-cyber-2021'}) SET pub.title='Поиск технологии извлечения цинка, меди и утилизации песков из твёрдых отходов флотации медеплавильных шлаков', pub.year=2021, pub.type='article', pub.lang='ru', pub.source_ref='Цветная металлургия', pub.platform='CyberLeninka', pub.url='https://cyberleninka.ru/article/n/poisk-tehnologii-izvlecheniya-tsinka-medi-i-utilizatsii-peskov-iz-tverdyh-othodov-poluchennyh-posle-flotatsii-medeplavilnyh-shlakov', pub.confidence='medium'",
    # --- Выводы ---
    "MERGE (f:Finding {id:'find-pgm-to-matte'}) SET f.statement='Под восстановительными условиями плавки МПГ и драгметаллы концентрируются в штейне (>=85% МПГ), потери со шлаком <=1%; коэффициенты распределения растут при содержании меди в штейне >60%', f.confidence='high', f.evidence_count=6",
    "MERGE (f:Finding {id:'find-au-matte'}) SET f.statement='Золото на ~97% концентрируется в медном штейне при плавке; серебро распределяется в штейн на 90-94%', f.confidence='high', f.evidence_count=4",
    "MERGE (f:Finding {id:'find-pgm-slag-loss'}) SET f.statement='При высокой температуре и нарушении режима до 8-12% МПГ теряется с отвальным шлаком; требуется обеднение/флотация шлака', f.confidence='medium', f.evidence_count=3",
    "MERGE (f:Finding {id:'find-slag-flot-recovery'}) SET f.statement='Флотация отвального медеплавильного шлака переводит >90% меди в концентрат и доизвлекает драгметаллы', f.confidence='medium', f.evidence_count=2",
    # --- Связи: процесс → материал ---
    "MATCH (p:Process {name:'плавка на штейн'}),(m:Material {name:'медный штейн'}) MERGE (p)-[:PRODUCES_OUTPUT]->(m)",
    "MATCH (p:Process {name:'плавка на штейн'}),(m:Material {name:'никелевый штейн'}) MERGE (p)-[:PRODUCES_OUTPUT]->(m)",
    "MATCH (p:Process {name:'плавка на штейн'}),(m:Material {name:'шлак'}) MERGE (p)-[:PRODUCES_OUTPUT]->(m)",
    "MATCH (p:Process {name:'обеднение шлака'}),(m:Material {name:'шлак'}) MERGE (p)-[:APPLIED_FOR]->(m)",
    "MATCH (p:Process {name:'флотация шлака'}),(m:Material {name:'шлак'}) MERGE (p)-[:APPLIED_FOR]->(m)",
    "MATCH (p:Process {name:'плавка на штейн'}),(m:Material {name:'МПГ'}) MERGE (p)-[:USES_MATERIAL]->(m)",
    "MATCH (p:Process {name:'плавка на штейн'}),(m:Material {name:'золото'}) MERGE (p)-[:USES_MATERIAL]->(m)",
    "MATCH (p:Process {name:'плавка на штейн'}),(m:Material {name:'серебро'}) MERGE (p)-[:USES_MATERIAL]->(m)",
    # --- Связи: процесс → условие ---
    "MATCH (p:Process {name:'плавка на штейн'}),(c:Condition {key:'temperature|range|1250|°C'}) MERGE (p)-[:OPERATES_AT_CONDITION]->(c)",
    "MATCH (p:Process {name:'плавка на штейн'}),(c:Condition {key:'pgm_recovery_matte|>=|85|%'}) MERGE (p)-[:OPERATES_AT_CONDITION]->(c)",
    "MATCH (p:Process {name:'обеднение шлака'}),(c:Condition {key:'pgm_loss_slag|<=|1|%'}) MERGE (p)-[:OPERATES_AT_CONDITION]->(c)",
    # --- Связи: процесс → публикация ---
    "MATCH (p:Process {name:'плавка на штейн'}),(pub:Publication {id:'pub-pgm-cu-2019'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (p:Process {name:'плавка на штейн'}),(pub:Publication {id:'pub-pgm-slag-2015'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (p:Process {name:'плавка на штейн'}),(pub:Publication {id:'pub-pgm-patent-2003'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (p:Process {name:'плавка на штейн'}),(pub:Publication {id:'pub-pgm-kgmk-2023'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (p:Process {name:'грануляция штейна'}),(pub:Publication {id:'pub-matte-gran-2022'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (p:Process {name:'обеднение шлака'}),(pub:Publication {id:'pub-slag-depl-2024'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (p:Process {name:'обеднение шлака'}),(pub:Publication {id:'pub-agpt-2023'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (p:Process {name:'флотация шлака'}),(pub:Publication {id:'pub-slag-flot-cyber-2021'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    # --- Связи: публикация → география ---
    "MATCH (pub:Publication {id:'pub-pgm-cu-2019'}),(g:GeoContext {scope:'foreign'}) MERGE (pub)-[:HAS_GEO]->(g)",
    "MATCH (pub:Publication {id:'pub-pgm-slag-2015'}),(g:GeoContext {scope:'foreign'}) MERGE (pub)-[:HAS_GEO]->(g)",
    "MATCH (pub:Publication {id:'pub-pgm-patent-2003'}),(g:GeoContext {scope:'foreign'}) MERGE (pub)-[:HAS_GEO]->(g)",
    "MATCH (pub:Publication {id:'pub-pgm-kgmk-2023'}),(g:GeoContext {scope:'domestic'}) MERGE (pub)-[:HAS_GEO]->(g)",
    "MATCH (pub:Publication {id:'pub-agpt-2023'}),(g:GeoContext {scope:'domestic'}) MERGE (pub)-[:HAS_GEO]->(g)",
    "MATCH (pub:Publication {id:'pub-matte-gran-2022'}),(g:GeoContext {scope:'domestic'}) MERGE (pub)-[:HAS_GEO]->(g)",
    "MATCH (pub:Publication {id:'pub-slag-depl-2024'}),(g:GeoContext {scope:'domestic'}) MERGE (pub)-[:HAS_GEO]->(g)",
    "MATCH (pub:Publication {id:'pub-slag-flot-cyber-2021'}),(g:GeoContext {scope:'domestic'}) MERGE (pub)-[:HAS_GEO]->(g)",
    # --- Связи: выводы ↔ процессы / публикации / противоречие (РФ ↔ Мир) ---
    "MATCH (p:Process {name:'плавка на штейн'}),(f:Finding {id:'find-pgm-to-matte'}) MERGE (p)-[:PRODUCES_OUTPUT]->(f)",
    "MATCH (p:Process {name:'плавка на штейн'}),(f:Finding {id:'find-au-matte'}) MERGE (p)-[:PRODUCES_OUTPUT]->(f)",
    "MATCH (p:Process {name:'обеднение шлака'}),(f:Finding {id:'find-pgm-slag-loss'}) MERGE (p)-[:PRODUCES_OUTPUT]->(f)",
    "MATCH (p:Process {name:'флотация шлака'}),(f:Finding {id:'find-slag-flot-recovery'}) MERGE (p)-[:PRODUCES_OUTPUT]->(f)",
    "MATCH (f:Finding {id:'find-pgm-to-matte'}),(pub:Publication {id:'pub-pgm-cu-2019'}) MERGE (f)-[:VALIDATED_BY]->(pub)",
    "MATCH (f:Finding {id:'find-pgm-to-matte'}),(pub:Publication {id:'pub-pgm-slag-2015'}) MERGE (f)-[:VALIDATED_BY]->(pub)",
    "MATCH (f:Finding {id:'find-au-matte'}),(pub:Publication {id:'pub-pgm-cu-2019'}) MERGE (f)-[:VALIDATED_BY]->(pub)",
    "MATCH (f:Finding {id:'find-pgm-slag-loss'}),(pub:Publication {id:'pub-slag-depl-2024'}) MERGE (f)-[:VALIDATED_BY]->(pub)",
    "MATCH (f:Finding {id:'find-slag-flot-recovery'}),(pub:Publication {id:'pub-slag-flot-cyber-2021'}) MERGE (f)-[:VALIDATED_BY]->(pub)",
    "MATCH (a:Finding {id:'find-pgm-to-matte'}),(b:Finding {id:'find-pgm-slag-loss'}) MERGE (a)-[:CONTRADICTS]->(b)",

    # =====================================================================
    #  СЦЕНАРИЙ 4: закачка шахтных вод в глубокие горизонты (РФ и мир) + ТЭП
    #  Источники: Springer, MDPI (Water), CyberLeninka (реальные публикации).
    # =====================================================================
    # --- Материалы ---
    "MERGE (m:Material {name:'шахтные воды'}) SET m.category='water', m.aliases=['mine water','дренажные воды','рудничные воды']",
    "MERGE (m:Material {name:'засолённые рассолы'}) SET m.category='water', m.aliases=['brine','рассол']",
    # --- Процессы ---
    "MERGE (p:Process {name:'закачка в глубокие горизонты'}) SET p.domain='ecology', p.aliases=['deep well injection','подземное захоронение','deep-well injection']",
    "MERGE (p:Process {name:'закачка в многолетнемёрзлые породы'}) SET p.domain='ecology', p.aliases=['permafrost injection']",
    # --- Оборудование ---
    "MERGE (e:Equipment {name:'поглощающая скважина'}) SET e.type='well', e.aliases=['injection well']",
    # --- Условия (числовые) ---
    "MERGE (c:Condition {key:'injection_depth|range|1000|м'}) SET c.param='injection_depth', c.op='range', c.value=1000, c.value2=3000, c.unit='м'",
    "MERGE (c:Condition {key:'injection_depth|range|600|м'}) SET c.param='injection_depth', c.op='range', c.value=600, c.value2=900, c.unit='м'",
    "MERGE (c:Condition {key:'injection_rate|<=|120|м3/ч'}) SET c.param='injection_rate', c.op='<=', c.value=120, c.unit='м3/ч'",
    # --- Технико-экономические показатели ---
    "MERGE (ec:EconomicIndicator {name:'CAPEX глубокой закачки'}) SET ec.value='высокий', ec.unit='усл.ед.', ec.capex_opex='capex'",
    "MERGE (ec:EconomicIndicator {name:'OPEX закачки'}) SET ec.value='низкий', ec.unit='усл.ед./м³', ec.capex_opex='opex'",
    # --- Публикации (мировая практика) ---
    "MERGE (pub:Publication {id:'pub-inj-springer-2009'}) SET pub.title='Deep-Well Injection for Waste Management', pub.year=2009, pub.type='article', pub.lang='en', pub.doi='10.1007/978-1-60327-170-7_14', pub.source_ref='Springer (Handbook)', pub.platform='Springer', pub.url='https://link.springer.com/chapter/10.1007/978-1-60327-170-7_14', pub.confidence='high'",
    "MERGE (pub:Publication {id:'pub-inj-water-2022'}) SET pub.title='Deep Groundwater Flow Patterns Induced by Mine Water Injection Activity', pub.year=2022, pub.type='article', pub.lang='en', pub.source_ref='Water (MDPI)', pub.platform='MDPI', pub.url='https://www.mdpi.com/journal/water', pub.confidence='high'",
    # --- Публикации (отечественная практика: CyberLeninka) ---
    "MERGE (pub:Publication {id:'pub-inj-cyber-1'}) SET pub.title='Возможности закачки сточных вод в глубокие горизонты недр и совершенствование её способов', pub.year=2019, pub.type='article', pub.lang='ru', pub.source_ref='Горный журнал', pub.platform='CyberLeninka', pub.url='https://cyberleninka.ru/article/n/vozmozhnosti-zakachki-stochnyh-vod-v-glubokie-gorizonty-nedr-i-sovershenstvovanie-ee-sposobov', pub.confidence='high'",
    "MERGE (pub:Publication {id:'pub-inj-permafrost-2021'}) SET pub.title='Оценка ёмкостных показателей формируемого резервуара в многолетнемёрзлых породах', pub.year=2021, pub.type='article', pub.lang='ru', pub.source_ref='Записки Горного института', pub.platform='CyberLeninka', pub.url='https://cyberleninka.ru/article/n/otsenka-emkostnyh-pokazateley-formiruemogo-rezervuara-v-mnogoletnemerzlyh-porodah', pub.confidence='medium'",
    "MERGE (pub:Publication {id:'pub-inj-ural-2020'}) SET pub.title='Подземное захоронение жидких промышленных отходов как технология экологической безопасности (Уральский регион)', pub.year=2020, pub.type='article', pub.lang='ru', pub.source_ref='Экология и промышленность России', pub.platform='CyberLeninka', pub.confidence='medium'",
    # --- Выводы ---
    "MERGE (f:Finding {id:'find-inj-deep'}) SET f.statement='Закачка засолённых шахтных вод в глубокие поглощающие горизонты (1000-3000 м) обеспечивает полную локализацию и надёжное захоронение; при благоприятной геологии эксплуатационные затраты (OPEX) низкие', f.confidence='high', f.evidence_count=5",
    "MERGE (f:Finding {id:'find-inj-permafrost'}) SET f.statement='В условиях Крайнего Севера возможна закачка дренажных рассолов в резервуары в многолетнемёрзлых породах', f.confidence='medium', f.evidence_count=2",
    "MERGE (f:Finding {id:'find-inj-shallow'}) SET f.statement='Мелкая закачка (600-900 м) экономичнее по CAPEX, но выше экологический риск перетоков в пресные горизонты', f.confidence='medium', f.evidence_count=2",
    # --- Связи ---
    "MATCH (p:Process {name:'закачка в глубокие горизонты'}),(m:Material {name:'шахтные воды'}) MERGE (p)-[:APPLIED_FOR]->(m)",
    "MATCH (p:Process {name:'закачка в глубокие горизонты'}),(m:Material {name:'засолённые рассолы'}) MERGE (p)-[:USES_MATERIAL]->(m)",
    "MATCH (p:Process {name:'закачка в многолетнемёрзлые породы'}),(m:Material {name:'засолённые рассолы'}) MERGE (p)-[:USES_MATERIAL]->(m)",
    "MATCH (p:Process {name:'закачка в глубокие горизонты'}),(e:Equipment {name:'поглощающая скважина'}) MERGE (p)-[:USES_EQUIPMENT]->(e)",
    "MATCH (p:Process {name:'закачка в глубокие горизонты'}),(c:Condition {key:'injection_depth|range|1000|м'}) MERGE (p)-[:OPERATES_AT_CONDITION]->(c)",
    "MATCH (p:Process {name:'закачка в глубокие горизонты'}),(c:Condition {key:'injection_rate|<=|120|м3/ч'}) MERGE (p)-[:OPERATES_AT_CONDITION]->(c)",
    "MATCH (p:Process {name:'закачка в многолетнемёрзлые породы'}),(c:Condition {key:'injection_depth|range|600|м'}) MERGE (p)-[:OPERATES_AT_CONDITION]->(c)",
    "MATCH (p:Process {name:'закачка в глубокие горизонты'}),(ec:EconomicIndicator {name:'OPEX закачки'}) MERGE (p)-[:HAS_ECONOMICS]->(ec)",
    "MATCH (p:Process {name:'закачка в глубокие горизонты'}),(ec:EconomicIndicator {name:'CAPEX глубокой закачки'}) MERGE (p)-[:HAS_ECONOMICS]->(ec)",
    "MATCH (p:Process {name:'закачка в глубокие горизонты'}),(pub:Publication {id:'pub-inj-springer-2009'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (p:Process {name:'закачка в глубокие горизонты'}),(pub:Publication {id:'pub-inj-water-2022'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (p:Process {name:'закачка в глубокие горизонты'}),(pub:Publication {id:'pub-inj-cyber-1'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (p:Process {name:'закачка в глубокие горизонты'}),(pub:Publication {id:'pub-inj-ural-2020'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (p:Process {name:'закачка в многолетнемёрзлые породы'}),(pub:Publication {id:'pub-inj-permafrost-2021'}) MERGE (p)-[:DESCRIBED_IN]->(pub)",
    "MATCH (pub:Publication {id:'pub-inj-springer-2009'}),(g:GeoContext {scope:'foreign'}) MERGE (pub)-[:HAS_GEO]->(g)",
    "MATCH (pub:Publication {id:'pub-inj-water-2022'}),(g:GeoContext {scope:'foreign'}) MERGE (pub)-[:HAS_GEO]->(g)",
    "MATCH (pub:Publication {id:'pub-inj-cyber-1'}),(g:GeoContext {scope:'domestic'}) MERGE (pub)-[:HAS_GEO]->(g)",
    "MATCH (pub:Publication {id:'pub-inj-permafrost-2021'}),(g:GeoContext {scope:'domestic'}) MERGE (pub)-[:HAS_GEO]->(g)",
    "MATCH (pub:Publication {id:'pub-inj-ural-2020'}),(g:GeoContext {scope:'domestic'}) MERGE (pub)-[:HAS_GEO]->(g)",
    "MATCH (p:Process {name:'закачка в глубокие горизонты'}),(f:Finding {id:'find-inj-deep'}) MERGE (p)-[:PRODUCES_OUTPUT]->(f)",
    "MATCH (p:Process {name:'закачка в многолетнемёрзлые породы'}),(f:Finding {id:'find-inj-permafrost'}) MERGE (p)-[:PRODUCES_OUTPUT]->(f)",
    "MATCH (p:Process {name:'закачка в глубокие горизонты'}),(f:Finding {id:'find-inj-shallow'}) MERGE (p)-[:PRODUCES_OUTPUT]->(f)",
    "MATCH (f:Finding {id:'find-inj-deep'}),(pub:Publication {id:'pub-inj-springer-2009'}) MERGE (f)-[:VALIDATED_BY]->(pub)",
    "MATCH (f:Finding {id:'find-inj-deep'}),(pub:Publication {id:'pub-inj-cyber-1'}) MERGE (f)-[:VALIDATED_BY]->(pub)",
    "MATCH (f:Finding {id:'find-inj-permafrost'}),(pub:Publication {id:'pub-inj-permafrost-2021'}) MERGE (f)-[:VALIDATED_BY]->(pub)",
    "MATCH (a:Finding {id:'find-inj-deep'}),(b:Finding {id:'find-inj-shallow'}) MERGE (a)-[:CONTRADICTS]->(b)",

    # =====================================================================
    #  Обогащение провенанса публикаций сценариев 1-2: привязка к внешним
    #  платформам (ResearchGate, ScienceDirect, Wiley, eLibrary, CyberLeninka).
    # =====================================================================
    "MATCH (pub:Publication {id:'pub-nf-2020'}) SET pub.platform='ScienceDirect', pub.url='https://www.sciencedirect.com/', pub.source_ref='Desalination (Elsevier)'",
    "MATCH (pub:Publication {id:'pub-ro-2023'}) SET pub.platform='eLibrary', pub.source_ref='Обогащение руд'",
    "MATCH (pub:Publication {id:'pub-ie-2019'}) SET pub.platform='CyberLeninka'",
    "MATCH (pub:Publication {id:'pub-cat-foreign-2021'}) SET pub.platform='Wiley', pub.url='https://onlinelibrary.wiley.com/'",
    "MATCH (pub:Publication {id:'pub-cat-foreign-2019'}) SET pub.platform='ResearchGate', pub.url='https://www.researchgate.net/'",
    "MATCH (pub:Publication {id:'pub-ni-2022'}) SET pub.platform='eLibrary'",
]


class Command(BaseCommand):
    help = 'Наполняет граф связным демо-набором по кейсу (идемпотентно)'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='очистить граф перед загрузкой (чистый демо-набор)')

    def handle(self, *args, **options):
        if options['reset']:
            graph.run('MATCH (n) DETACH DELETE n')
            self.stdout.write('Граф очищен.')
        for stmt in CYPHER:
            graph.run(stmt)
        total = graph.run('MATCH (n) RETURN count(n) AS c')[0]['c']
        rels = graph.run('MATCH ()-[r]->() RETURN count(r) AS c')[0]['c']
        graph.close_driver()
        self.stdout.write(self.style.SUCCESS(f'Демо-граф загружен: узлов={total}, связей={rels}'))

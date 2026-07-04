// Схема графа знаний: ограничения уникальности + индексы.
// Запускается через `python manage.py graph_init`. Идемпотентно (IF NOT EXISTS).

// --- Уникальные ключи по меткам ---
CREATE CONSTRAINT material_name IF NOT EXISTS FOR (n:Material) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT process_name IF NOT EXISTS FOR (n:Process) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT equipment_name IF NOT EXISTS FOR (n:Equipment) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT property_name IF NOT EXISTS FOR (n:Property) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT publication_id IF NOT EXISTS FOR (n:Publication) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT experiment_id IF NOT EXISTS FOR (n:Experiment) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT expert_name IF NOT EXISTS FOR (n:Expert) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT facility_name IF NOT EXISTS FOR (n:Facility) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT finding_id IF NOT EXISTS FOR (n:Finding) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT condition_key IF NOT EXISTS FOR (n:Condition) REQUIRE n.key IS UNIQUE;

// --- Диапазонные индексы для числовых фильтров (концентрации, температуры, скорости) ---
CREATE INDEX condition_param IF NOT EXISTS FOR (n:Condition) ON (n.param);
CREATE INDEX condition_value IF NOT EXISTS FOR (n:Condition) ON (n.value);
CREATE INDEX publication_year IF NOT EXISTS FOR (n:Publication) ON (n.year);
CREATE INDEX geo_scope IF NOT EXISTS FOR (n:GeoContext) ON (n.scope);

// --- Полнотекстовый индекс для мультиязычного поиска по имени и синонимам ---
CREATE FULLTEXT INDEX entity_fulltext IF NOT EXISTS
FOR (n:Material|Process|Equipment|Property|Publication|Finding)
ON EACH [n.name, n.aliases];

// --- Vector index для семантического поиска (эмбеддинги публикаций/выводов) ---
// Размерность подстроить под провайдера эмбеддингов.
CREATE VECTOR INDEX publication_embedding IF NOT EXISTS
FOR (n:Publication) ON (n.embedding)
OPTIONS { indexConfig: { `vector.dimensions`: 1024, `vector.similarity_function`: 'cosine' } };

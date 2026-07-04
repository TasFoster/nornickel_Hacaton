"""
Тесты, не требующие сети и Neo4j: парсинг вывода модели и нормализация.
Запуск: python manage.py test knowledge
"""
from django.test import SimpleTestCase

from knowledge.services.extractor import _safe_parse
from knowledge.services.normalize import canonicalize_term, normalize_unit


class SafeParseTests(SimpleTestCase):
    def test_extracts_entities_relations_conditions(self):
        raw = (
            'Результат: {"entities":[{"type":"Material","name":"вода"}],'
            '"relations":[{"type":"APPLIED_FOR","from":"обратный осмос","to":"вода"}],'
            '"conditions":[{"param":"dry_residue","op":"<=","value":1000,"unit":"мг/дм3"}]}'
        )
        r = _safe_parse(raw)
        self.assertEqual(len(r.entities), 1)
        self.assertEqual(r.entities[0]['name'], 'вода')
        self.assertEqual(r.relations[0]['from'], 'обратный осмос')  # alias 'from' сохранён
        self.assertEqual(r.conditions[0]['value'], 1000.0)

    def test_garbage_returns_empty(self):
        r = _safe_parse('модель не вернула JSON')
        self.assertEqual(r.entities, [])
        self.assertEqual(r.conditions, [])

    def test_bad_number_condition_dropped(self):
        # Некорректное число в ограничении недопустимо → элемент отбрасывается.
        raw = '{"conditions":[{"param":"sulfates","op":"<=","value":"≤300","unit":"мг/л"}]}'
        self.assertEqual(_safe_parse(raw).conditions, [])

    def test_invalid_op_dropped(self):
        raw = '{"conditions":[{"param":"t","op":"около","value":80,"unit":"C"}]}'
        self.assertEqual(_safe_parse(raw).conditions, [])

    def test_json_inside_code_fence(self):
        raw = '```json\n{"entities":[{"type":"Process","name":"выщелачивание"}]}\n```'
        self.assertEqual(len(_safe_parse(raw).entities), 1)


class NormalizeTests(SimpleTestCase):
    def test_synonym_to_canonical(self):
        self.assertEqual(canonicalize_term('electrowinning'), 'электроэкстракция')
        self.assertEqual(canonicalize_term('ПВП'), 'печь взвешенной плавки')

    def test_unit_conversion(self):
        self.assertEqual(normalize_unit(1, 'г/л'), (1000.0, 'мг/л'))
        self.assertEqual(normalize_unit(500, 'мг/дм3'), (500.0, 'мг/л'))

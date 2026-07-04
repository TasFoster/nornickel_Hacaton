"""
Загрузка корпуса в граф: читает документы (txt/md/pdf/docx) из файла или каталога,
разбивает на чанки, извлекает знания LLM-экстрактором, нормализует термины/единицы и делает
идемпотентный upsert (MERGE) с провенансом.

Примеры:
  python manage.py ingest                          # демо-фрагмент
  python manage.py ingest --source ../data/samples/demo-water.txt
  python manage.py ingest --source ../data/corpus --limit 20
"""
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

from knowledge.services import graph
from knowledge.services.extractor import LlmExtractor
from knowledge.services.normalize import canonicalize_term, normalize_unit
from knowledge.services.graph_upsert import upsert_extraction
from knowledge.services.documents import read_document, iter_documents, chunk_text

DEMO_TEXT = (
    'Электроэкстракция никеля (electrowinning) ведётся при скорости циркуляции католита '
    '0.15 м/с. Требуемый сухой остаток воды ≤ 1000 мг/дм3.'
)


class Command(BaseCommand):
    help = 'Извлекает знания из корпуса и загружает в граф (идемпотентный upsert)'

    def add_arguments(self, parser):
        parser.add_argument('--source', default='demo', help='demo | путь к файлу | путь к каталогу')
        parser.add_argument('--limit', type=int, default=0, help='ограничить число документов (0 = без лимита)')

    def handle(self, *args, **options):
        extractor = LlmExtractor()
        docs = self._collect(options['source'], options['limit'])
        if not docs:
            self.stderr.write('Нет документов для загрузки.')
            return

        totals = {'entities': 0, 'conditions': 0, 'relations': 0}
        for ref, text in docs:
            chunks = chunk_text(text)
            for chunk in chunks:
                result = extractor.extract(chunk, source_ref=ref, lang='ru')
                for e in result.entities:
                    e['name'] = canonicalize_term(e.get('name', ''))
                for c in result.conditions:
                    value, unit = normalize_unit(float(c.get('value', 0)), c.get('unit', ''))
                    c['value'], c['unit'] = value, unit
                prov = {
                    'source_ref': ref, 'confidence': 'medium',
                    'actualized_at': timezone.now().isoformat(), 'extraction': 'llm',
                }
                counts = upsert_extraction(result, prov)
                for k in totals:
                    totals[k] += counts[k]
            self.stdout.write(f'  {ref}: чанков={len(chunks)}')

        graph.close_driver()
        self.stdout.write(self.style.SUCCESS(
            f"Итого загружено: узлов={totals['entities']} условий={totals['conditions']} "
            f"связей={totals['relations']}"
        ))

    def _collect(self, source: str, limit: int) -> list[tuple[str, str]]:
        if source == 'demo':
            return [('demo', DEMO_TEXT)]
        p = Path(source)
        if p.is_dir():
            files = list(iter_documents(p))
            if limit:
                files = files[:limit]
            return [(str(f), read_document(f)) for f in files]
        if p.is_file():
            return [(str(p), read_document(p))]
        self.stderr.write(f'Источник не найден: {source}')
        return []

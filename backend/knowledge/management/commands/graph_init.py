"""
Инициализация схемы графа: применяет ограничения и индексы из schema.cypher.
Запуск: python manage.py graph_init
"""
from pathlib import Path

from django.core.management.base import BaseCommand

from knowledge.services import graph

SCHEMA_PATH = Path(__file__).resolve().parents[2] / 'graph' / 'schema.cypher'


class Command(BaseCommand):
    help = 'Применяет constraints и индексы Neo4j из knowledge/graph/schema.cypher'

    def handle(self, *args, **options):
        sql = SCHEMA_PATH.read_text(encoding='utf-8')
        # Разбиваем на отдельные statements по ';', отбрасывая строки-комментарии.
        statements = []
        for chunk in sql.split(';'):
            lines = [ln for ln in chunk.splitlines() if not ln.strip().startswith('//')]
            stmt = '\n'.join(lines).strip()
            if stmt:
                statements.append(stmt)

        for stmt in statements:
            head = stmt.splitlines()[0]
            try:
                graph.run(stmt)
                self.stdout.write(self.style.SUCCESS(f'OK:   {head}'))
            except Exception as exc:  # noqa: BLE001
                self.stdout.write(self.style.ERROR(f'FAIL: {head}\n      {exc}'))

        graph.close_driver()
        self.stdout.write(self.style.SUCCESS('Схема графа инициализирована.'))

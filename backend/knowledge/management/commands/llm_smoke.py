"""
Smoke-тест LLM-провайдера: короткий запрос к модели через провайдер-агностичный слой.
Запуск: python manage.py llm_smoke
Проверяет, что выбранный в .env провайдер (по умолчанию YandexGPT) реально отвечает.
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from knowledge.services.llm import get_llm


class Command(BaseCommand):
    help = 'Проверка связи с LLM-провайдером (короткий запрос)'

    def handle(self, *args, **options):
        self.stdout.write(f"Провайдер: {settings.LLM['provider']}  модель: {settings.LLM['model']}")
        try:
            out = get_llm().chat(
                system='Ты — лаконичный ассистент. Отвечай кратко на русском.',
                user='Ответь одним коротким предложением, что связь с моделью работает.',
                max_tokens=100,
            )
        except Exception as exc:  # noqa: BLE001
            self.stdout.write(self.style.ERROR(f'ОШИБКА вызова LLM: {exc}'))
            return
        self.stdout.write(self.style.SUCCESS('Ответ модели:'))
        self.stdout.write(out)

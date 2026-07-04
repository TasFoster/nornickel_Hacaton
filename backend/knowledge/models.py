"""
Реляционные модели (Django ORM) для части, которую НЕ хранит граф: аудит действий
и ролевой доступ (требования кейса по ИБ). Граф знаний живёт в Neo4j.
"""
from django.conf import settings
from django.db import models


class QueryLog(models.Model):
    """Аудит запросов к графу: кто, что спросил, какой Cypher сгенерирован, сколько строк."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    question = models.TextField()
    cypher = models.TextField(blank=True)
    row_count = models.IntegerField(default=0)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.created_at:%Y-%m-%d %H:%M} · {self.question[:50]}'

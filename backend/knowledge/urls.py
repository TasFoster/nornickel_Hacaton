"""Маршруты API приложения knowledge."""
from django.urls import path

from knowledge import views

urlpatterns = [
    path('health', views.health, name='health'),
    path('query', views.query, name='query'),
    path('graph', views.subgraph, name='subgraph'),
    # TODO(день 1): path('ingest', views.ingest) — загрузка документа в пайплайн.
]

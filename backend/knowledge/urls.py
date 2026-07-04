"""Маршруты API приложения knowledge."""
from django.urls import path

from knowledge import views

urlpatterns = [
    path('health', views.health, name='health'),
    path('query', views.query, name='query'),
    path('graph', views.subgraph, name='subgraph'),
    path('ingest', views.ingest, name='ingest'),  # загрузка документа (PDF/DOCX/XLSX/CSV/TXT/MD)
    path('fact', views.fact, name='fact'),         # ручная корректировка графа экспертом
]

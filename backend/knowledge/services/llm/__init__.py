"""
Провайдер-агностичный LLM-слой.

Публичное API: get_llm() и get_embedder() — фабрики, читающие провайдера из настроек.
Бизнес-код (extractor, nl2cypher) зависит только от интерфейсов base.LLMClient/Embedder,
а не от конкретного вендора. Смена модели = правка .env, без изменения кода.
"""
from .base import LLMClient, Embedder
from .factory import get_llm, get_embedder

__all__ = ['LLMClient', 'Embedder', 'get_llm', 'get_embedder']

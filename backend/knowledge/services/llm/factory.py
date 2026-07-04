"""
Фабрики провайдеров. Читают выбор из настроек Django (которые берут его из .env) и
возвращают нужный адаптер. Клиенты кэшируются на процесс.

Провайдер меняется одной переменной окружения LLM_PROVIDER — код бизнес-логики не трогаем.
"""
from django.conf import settings

from .base import LLMClient, Embedder

_llm: LLMClient | None = None
_embedder: Embedder | None = None

# Провайдеры, говорящие на OpenAI-совместимом протоколе (один адаптер на всех).
_OPENAI_COMPATIBLE = {'yandex', 'openai', 'openai_compat', 'local', 'ollama', 'vllm'}


def get_llm() -> LLMClient:
    global _llm
    if _llm is None:
        cfg = settings.LLM
        provider = cfg['provider']
        if provider in _OPENAI_COMPATIBLE:
            from .openai_compatible import OpenAICompatibleClient
            _llm = OpenAICompatibleClient(
                api_key=cfg['api_key'], base_url=cfg['api_base'], model=cfg['model']
            )
        else:
            raise ValueError(f'Неизвестный LLM_PROVIDER: {provider!r}')
    return _llm


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        cfg = settings.EMBEDDINGS
        provider = cfg['provider']
        if provider == 'local_e5':
            from .embeddings import LocalE5Embedder
            _embedder = LocalE5Embedder(cfg['model'])
        elif provider == 'yandex':
            from .embeddings import YandexEmbedder
            _embedder = YandexEmbedder(
                api_key=settings.LLM['api_key'], folder_id=settings.LLM['folder_id']
            )
        else:
            raise ValueError(f'Неизвестный EMBED_PROVIDER: {provider!r}')
    return _embedder


def reset_cache() -> None:
    """Сбросить кэш клиентов (для тестов переключения провайдера)."""
    global _llm, _embedder
    _llm = None
    _embedder = None

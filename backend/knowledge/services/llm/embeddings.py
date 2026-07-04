"""
Адаптеры эмбеддингов для семантического поиска.

По умолчанию — локальный multilingual-e5 (офлайн, ноль зависимости от внешнего API).
Опция — Yandex Embeddings. Тяжёлые зависимости (sentence-transformers/torch) импортируются
лениво, чтобы не требоваться, пока семантический поиск не используется (Фаза 2).
"""
from .base import Embedder


class LocalE5Embedder(Embedder):
    """Локальная модель intfloat/multilingual-e5-* через sentence-transformers."""

    def __init__(self, model_name: str = 'intfloat/multilingual-e5-large'):
        from sentence_transformers import SentenceTransformer  # ленивый импорт
        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        # e5 требует префиксы; для документов — 'passage: '. Нормализуем для косинуса.
        prefixed = [f'passage: {t}' for t in texts]
        vectors = self._model.encode(prefixed, normalize_embeddings=True)
        return vectors.tolist()


class YandexEmbedder(Embedder):
    """Yandex Embeddings (text-search-doc). Опциональная альтернатива локальной модели."""

    def __init__(self, api_key: str, folder_id: str):
        import requests  # ленивый импорт
        self._requests = requests
        self._api_key = api_key
        self._folder_id = folder_id
        self._url = 'https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding'

    def embed(self, texts: list[str]) -> list[list[float]]:
        model_uri = f'emb://{self._folder_id}/text-search-doc/latest'
        headers = {'Authorization': f'Api-Key {self._api_key}'}
        out: list[list[float]] = []
        for text in texts:
            resp = self._requests.post(
                self._url, headers=headers,
                json={'modelUri': model_uri, 'text': text}, timeout=30,
            )
            resp.raise_for_status()
            out.append(resp.json()['embedding'])
        return out

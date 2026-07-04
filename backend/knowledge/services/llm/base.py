"""Доменные интерфейсы (порты) LLM-слоя. Реализации — в адаптерах."""
from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Тонкий порт генеративной модели. Один метод — чат-запрос, возвращает текст."""

    @abstractmethod
    def chat(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> str:
        """Выполнить запрос к модели и вернуть текстовый ответ."""
        raise NotImplementedError


class Embedder(ABC):
    """Порт модели эмбеддингов для семантического поиска."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Вернуть векторные представления для списка текстов."""
        raise NotImplementedError

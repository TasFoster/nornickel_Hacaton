"""
Основной адаптер — любой OpenAI-совместимый эндпоинт (`/v1/chat/completions`).

Покрывает сразу несколько провайдеров без изменения кода:
- YandexGPT (официальный OpenAI-совместимый endpoint) — наш текущий рабочий провайдер;
- self-host open-weight модели через Ollama/vLLM;
- любой «прокси base_url + ключ».
Переключение между ними — только через .env (base_url/model/key).
"""
from openai import OpenAI

from .base import LLMClient


class OpenAICompatibleClient(LLMClient):
    def __init__(self, api_key: str, base_url: str, model: str):
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def chat(self, system: str, user: str, *, max_tokens: int = 2048, temperature: float = 0.0) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ],
        )
        return resp.choices[0].message.content or ''

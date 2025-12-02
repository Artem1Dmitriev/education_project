# app/core/providers/ollama_client.py
import httpx
from typing import Optional, List, Dict, Any
import json


class OllamaClient:
    def __init__(self, base_url: str = "http://ollama:11434"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def chat_completion(
            self,
            messages: List[Dict[str, str]],
            model: str = "llama3.2:latest",  # или "mistral", "codellama"
            temperature: float = 0.7,
            max_tokens: Optional[int] = None,
            **kwargs
    ) -> Dict[str, Any]:
        """Отправка запроса в Ollama API"""
        try:
            # Конвертируем сообщения в формат Ollama
            prompt = self._format_messages(messages)

            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens or 1024,
                }
            }

            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()

            result = response.json()

            # Эмулируем ответ в формате OpenAI для совместимости
            return {
                "content": result.get("response", ""),
                "model_used": model,
                "finish_reason": "stop",
                "input_tokens": result.get("prompt_eval_count", 0),
                "output_tokens": result.get("eval_count", 0),
                "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
            }

        except Exception as e:
            raise Exception(f"Ollama API error: {str(e)}")

    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Конвертируем OpenAI формат сообщений в промпт для Ollama"""
        formatted = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                formatted.append(f"System: {content}")
            elif role == "user":
                formatted.append(f"User: {content}")
            elif role == "assistant":
                formatted.append(f"Assistant: {content}")

        return "\n".join(formatted)

    async def list_models(self) -> List[str]:
        """Получить список доступных моделей"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except:
            return []

    async def health_check(self) -> bool:
        """Проверить доступность Ollama"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except:
            return False


# Создаем синглтон
ollama_client = OllamaClient()
# app/core/chat/calculation/tokenizer.py
import logging
from typing import List, Dict, Optional
import tiktoken  # Для оценки токенов OpenAI моделей

logger = logging.getLogger(__name__)


class TokenizerService:
    """Сервис для работы с токенизацией"""

    def __init__(self):
        self.encoders = {}

    def _get_encoder(self, model_name: str) -> Optional[tiktoken.Encoding]:
        """Получить кодировщик для модели"""
        try:
            if model_name in self.encoders:
                return self.encoders[model_name]

            # Пытаемся найти кодировщик для модели
            encoder = tiktoken.encoding_for_model(model_name)
            self.encoders[model_name] = encoder
            return encoder
        except KeyError:
            # Для не-OpenAI моделей используем приблизительный подсчет
            return None

    def estimate_tokens(self, messages: List[Dict], model_name: str) -> int:
        """
        Оценить количество токенов для сообщений

        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "text"}]
            model_name: Название модели

        Returns:
            Примерное количество токенов
        """
        encoder = self._get_encoder(model_name)

        if encoder:
            # Точный подсчет для OpenAI моделей
            tokens_per_message = 3  # Каждое сообщение добавляет 3 токена
            tokens_per_name = 1  # Имя добавляет 1 токен

            num_tokens = 0
            for message in messages:
                num_tokens += tokens_per_message
                for key, value in message.items():
                    if key == "content":
                        num_tokens += len(encoder.encode(value))
                    elif key == "name":
                        num_tokens += tokens_per_name
            num_tokens += 3  # Каждый ответ начинается с assistant
            return num_tokens
        else:
            # Приблизительный подсчет для других моделей
            return self._estimate_tokens_fallback(messages)

    def _estimate_tokens_fallback(self, messages: List[Dict]) -> int:
        """Приблизительная оценка токенов (4 символа = 1 токен)"""
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        return total_chars // 4

    def check_context_limit(
            self,
            messages: List[Dict],
            model_name: str,
            max_context_window: int
    ) -> bool:
        """Проверить, не превышает ли запрос лимит контекста"""
        estimated_tokens = self.estimate_tokens(messages, model_name)
        return estimated_tokens <= max_context_window
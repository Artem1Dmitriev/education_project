# app/core/chat/prompt/service.py
import hashlib
import json
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class PromptService:
    """Сервис для работы с промптами"""

    def __init__(self):
        self.hash_version = "v1"

    def calculate_hash(self, messages: List[Dict[str, str]]) -> str:
        """
        Вычисление хеша промпта

        Args:
            messages: Список сообщений

        Returns:
            Хеш промпта
        """
        try:
            normalized_messages = []
            for msg in messages:
                normalized_msg = {
                    "role": msg.get("role", "").strip().lower(),
                    "content": msg.get("content", "").strip(),
                }
                normalized_messages.append(
                    json.dumps(normalized_msg, sort_keys=True, separators=(',', ':'))
                )

            normalized_messages.sort()
            text_repr = f"{self.hash_version}:{':'.join(normalized_messages)}"

            return hashlib.blake2s(
                text_repr.encode(),
                digest_size=16
            ).hexdigest()

        except Exception as e:
            logger.error(f"Failed to calculate prompt hash: {e}")
            # Возвращаем fallback хеш
            return hashlib.md5(str(messages).encode()).hexdigest()

    def normalize_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Нормализация сообщений"""
        normalized = []
        for msg in messages:
            normalized.append({
                "role": msg.get("role", "user").strip().lower(),
                "content": msg.get("content", "").strip()
            })
        return normalized
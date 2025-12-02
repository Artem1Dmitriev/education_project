# app/core/providers/mock_client.py
import random
import asyncio  # <-- ДОБАВЬТЕ ЭТОТ ИМПОРТ!
from typing import Optional, List, Dict, Any
import time


class MockClient:
    """Мок-клиент для тестирования без реальных API"""

    def __init__(self):
        self.responses = [
            "Привет! Я тестовый AI ассистент. Как я могу помочь?",
            "Это тестовый ответ для демонстрации работы системы.",
            "Запрос успешно обработан. В реальной системе здесь был бы ответ от нейросети.",
            "Система работает корректно. Вы можете протестировать различные функции.",
            "Добро пожаловать в AI Gateway Framework! Все системы функционируют нормально.",
            "На основе вашего запроса я сгенерировал тестовый ответ. В реальной системе это был бы ответ от нейросети OpenAI, Anthropic или другой модели.",
            "Это демонстрационный ответ, который показывает, что система маршрутизации запросов работает корректно.",
            "Ваш запрос был обработан успешно. Токены посчитаны, ответ сохранен в базу данных.",
            "Тестовая модель 'mock-model' обработала ваш запрос. В продакшене здесь был бы ответ от GPT-4, Claude или другой модели.",
            "В AI Gateway Framework используется интеллектуальный роутинг для выбора оптимальной модели под ваш запрос."
        ]

    async def chat_completion(
            self,
            messages: List[Dict[str, str]],
            model: str = "mock-model",
            temperature: float = 0.7,
            max_tokens: Optional[int] = None,
            **kwargs
    ) -> Dict[str, Any]:
        """Возвращает мок-ответ для тестирования"""
        # Имитируем задержку сети
        await asyncio.sleep(random.uniform(0.1, 0.5))

        last_message = messages[-1]["content"] if messages else ""

        # Генерируем "умный" ответ на основе ввода
        lower_msg = last_message.lower()

        if "привет" in lower_msg:
            response = "Привет! Рад вас видеть в AI Gateway Framework!"
        elif "погод" in lower_msg:
            response = "Сегодня отличная погода для программирования и тестирования AI систем!"
        elif "помощ" in lower_msg or "help" in lower_msg:
            response = "Я могу помочь протестировать работу AI Gateway Framework. Попробуйте отправить разные запросы!"
        elif "код" in lower_msg or "code" in lower_msg:
            response = "```python\nprint('Hello, AI Gateway!')\n```\nВот простой пример кода на Python."
        elif "сколько стоит" in lower_msg or "стоимость" in lower_msg:
            response = "Это тестовая модель, поэтому стоимость = 0. В реальной системе стоимость рассчитывается на основе использованных токенов."
        elif "время" in lower_msg:
            response = f"Текущее время: {time.strftime('%H:%M:%S')}. Это тестовый ответ."
        else:
            response = random.choice(self.responses)

        # Эмулируем подсчет токенов (примерно 1 токен = 0.75 слова на английском)
        all_text = " ".join([msg["content"] for msg in messages])
        input_tokens = int(len(all_text.split()) * 0.75)
        output_tokens = int(len(response.split()) * 0.75)

        return {
            "content": response,
            "model_used": model,
            "finish_reason": "stop",
            "input_tokens": max(1, input_tokens),
            "output_tokens": max(1, output_tokens),
            "total_tokens": max(2, input_tokens + output_tokens),
        }


# Создаем синглтон
mock_client = MockClient()
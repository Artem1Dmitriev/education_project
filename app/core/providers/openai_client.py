# app/core/providers/openai_client.py
import openai
from typing import Optional, List, Dict, Any
from app.core.config import settings


class OpenAIClient:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.client = openai.AsyncOpenAI(api_key=self.api_key)

    async def chat_completion(
            self,
            messages: List[Dict[str, str]],
            model: str = "gpt-4o",
            temperature: float = 0.7,
            max_tokens: Optional[int] = None,
            **kwargs
    ) -> Dict[str, Any]:
        """Отправка запроса в OpenAI API"""
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            return {
                "content": response.choices[0].message.content,
                "model_used": response.model,
                "finish_reason": response.choices[0].finish_reason,
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")


# Создаем синглтон
openai_client = OpenAIClient()
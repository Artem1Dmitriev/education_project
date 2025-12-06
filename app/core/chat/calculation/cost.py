# app/core/cost_calculation/cost.py
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class CostCalculator:
    """Калькулятор стоимости запросов к LLM"""

    @staticmethod
    def calculate_input_cost(input_tokens: int, price_per_1k: float) -> float:
        """Рассчитать стоимость входящих токенов"""
        return input_tokens * price_per_1k / 1000 if price_per_1k else 0.0

    @staticmethod
    def calculate_output_cost(output_tokens: int, price_per_1k: float) -> float:
        """Рассчитать стоимость исходящих токенов"""
        return output_tokens * price_per_1k / 1000 if price_per_1k else 0.0

    @classmethod
    def calculate_total_cost(
            cls,
            input_tokens: int,
            output_tokens: int,
            model_config: Dict[str, Any]
    ) -> Dict[str, float]:
        """Рассчитать полную стоимость запроса"""
        input_price = model_config.get("input_price_per_1k", 0.0)
        output_price = model_config.get("output_price_per_1k", 0.0)

        input_cost = cls.calculate_input_cost(input_tokens, input_price)
        output_cost = cls.calculate_output_cost(output_tokens, output_price)
        total_cost = input_cost + output_cost

        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_price_per_1k": input_price,
            "output_price_per_1k": output_price
        }

    @classmethod
    def calculate_cost_for_provider_response(
            cls,
            provider_response,
            model_config: Dict[str, Any]
    ) -> Dict[str, float]:
        """Рассчитать стоимость на основе ответа провайдера"""
        return cls.calculate_total_cost(
            input_tokens=getattr(provider_response, 'input_tokens', 0),
            output_tokens=getattr(provider_response, 'output_tokens', 0),
            model_config=model_config
        )
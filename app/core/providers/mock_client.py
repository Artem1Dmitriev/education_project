
import asyncio 
import random 
import time 
from typing import List ,Dict ,Optional 
from .base import BaseProvider ,ProviderResponse 


class MockProvider (BaseProvider ):
    """Mock провайдер для тестирования"""

    @property 
    def provider_name (self )->str :
        return "MockAI"

    def __init__ (self ,**kwargs ):
        super ().__init__ (**kwargs )
        self .responses =[
        "Привет! Я тестовый AI ассистент. Как я могу помочь?",
        "Это тестовый ответ для демонстрации работы системы.",
        "Запрос успешно обработан. В реальной системе здесь был бы ответ от нейросети.",
        "Система работает корректно. Вы можете протестировать различные функции.",
        "Добро пожаловать в AI Gateway Framework! Все системы функционируют нормально.",
        ]

    async def chat_completion (
    self ,
    messages :List [Dict [str ,str ]],
    model :str ,
    temperature :float =0.7 ,
    max_tokens :Optional [int ]=None ,
    **kwargs 
    )->ProviderResponse :
        """Возвращает мок-ответ для тестирования"""

        await asyncio .sleep (random .uniform (0.1 ,0.5 ))

        last_message =messages [-1 ]["content"]if messages else ""
        lower_msg =last_message .lower ()


        if "привет"in lower_msg :
            response ="Привет! Рад вас видеть в AI Gateway Framework!"
        elif "погод"in lower_msg :
            response ="Сегодня отличная погода для программирования и тестирования AI систем!"
        elif "помощ"in lower_msg or "help"in lower_msg :
            response ="Я могу помочь протестировать работу AI Gateway Framework. Попробуйте отправить разные запросы!"
        elif "код"in lower_msg or "code"in lower_msg :
            response ="```python\nprint('Hello, AI Gateway!')\n```\nВот простой пример кода на Python."
        elif "сколько стоит"in lower_msg or "стоимость"in lower_msg :
            response ="Это тестовая модель, поэтому стоимость = 0. В реальной системе стоимость рассчитывается на основе использованных токенов."
        elif "время"in lower_msg :
            response =f"Текущее время: {time .strftime ('%H:%M:%S')}. Это тестовый ответ."
        else :
            response =random .choice (self .responses )


        all_text =" ".join ([msg ["content"]for msg in messages ])
        input_tokens =int (len (all_text .split ())*0.75 )
        output_tokens =int (len (response .split ())*0.75 )

        return ProviderResponse (
        content =response ,
        model_used =model ,
        provider_name =self .provider_name ,
        input_tokens =max (1 ,input_tokens ),
        output_tokens =max (1 ,output_tokens ),
        finish_reason ="stop"
        )

    async def health_check (self )->bool :
        """Mock всегда здоров"""
        return True 
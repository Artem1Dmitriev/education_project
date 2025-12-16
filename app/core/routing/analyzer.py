
"""
Анализатор промпта для определения его характеристик.
"""
import re 
import logging 
from typing import List 

from app .schemas import ChatMessage 
from .types import PromptComplexity ,PromptAnalysis 

logger =logging .getLogger (__name__ )


class PromptAnalyzer :
    """
    Анализирует промпт для определения его характеристик.
    """


    PROMPT_TYPE_PATTERNS ={
    'code_generation':[
    r'code',r'програм',r'алгоритм',r'функци',r'класс',
    r'импорт',r'синтаксис',r'компиляц',r'отладк'
    ],
    'translation':[
    r'перевод',r'translate',r'language',r'язык',
    r'на английск',r'на русск'
    ],
    'summarization':[
    r'сумм',r'summary',r'кратко',r'основн',
    r'в двух словах',r'резюме'
    ],
    'analysis':[
    r'анализ',r'analysis',r'сравн',r'compare',
    r'исследован',r'изуч'
    ],
    'creative_writing':[
    r'творч',r'creative',r'стих',r'story',
    r'рассказ',r'поэ',r'проза'
    ],
    'qa':[
    r'вопрос',r'question',r'ответ',r'answer',
    r'почему',r'как',r'что'
    ],
    }


    INSTRUCTION_PATTERNS =[
    r'используй.*формат',
    r'отвечай.*язык',
    r'не упоминай',
    r'включи.*пример',
    r'структур.*ответ',
    r'сначала.*потом',
    r'ограничь.*словами',
    r'формат.*json',
    r'формат.*xml',
    r'формат.*markdown',
    r'следующий.*шаг',
    r'обязательно.*включи',
    r'исключи.*информацию',
    ]

    def analyze (self ,messages :List [ChatMessage ])->PromptAnalysis :
        """
        Анализирует промпт для определения его характеристик.

        Args:
            messages: Список сообщений

        Returns:
            PromptAnalysis: Результат анализа
        """
        try :

            full_prompt =self ._combine_messages (messages )


            token_estimate =self ._estimate_tokens (full_prompt )


            complexity =self ._determine_complexity (token_estimate )


            prompt_type =self ._determine_type (full_prompt )


            has_specific_instructions =self ._has_specific_instructions (full_prompt )


            preview =self ._create_preview (full_prompt )

            return PromptAnalysis (
            token_estimate =token_estimate ,
            complexity =complexity ,
            prompt_type =prompt_type ,
            has_specific_instructions =has_specific_instructions ,
            text_length =len (full_prompt ),
            message_count =len (messages ),
            preview =preview 
            )

        except Exception as e :
            logger .error (f"Error analyzing prompt: {e }")

            return self ._get_default_analysis ()

    def _combine_messages (self ,messages :List [ChatMessage ])->str :
        """Объединяет все сообщения в один текст"""
        return "\n".join ([msg .content for msg in messages ])

    def _estimate_tokens (self ,text :str )->int :
        """
        Оценивает количество токенов в тексте.
        Приблизительная оценка: 1 токен ≈ 3 символа
        """






        words =text .split ()


        avg_word_length =sum (len (word )for word in words )/max (len (words ),1 )

        if avg_word_length <=4 :
            token_estimate =len (text )//4 
        elif avg_word_length <=6 :
            token_estimate =len (text )//3 
        else :
            token_estimate =len (text )//2 

        return max (token_estimate ,1 )

    def _determine_complexity (self ,token_estimate :int )->PromptComplexity :
        """Определяет уровень сложности промпта"""
        if token_estimate <100 :
            return PromptComplexity .SIMPLE 
        elif token_estimate <500 :
            return PromptComplexity .STANDARD 
        elif token_estimate <1500 :
            return PromptComplexity .COMPLEX 
        else :
            return PromptComplexity .ADVANCED 

    def _determine_type (self ,prompt :str )->str :
        """Определяет тип промпта"""
        prompt_lower =prompt .lower ()

        for prompt_type ,patterns in self .PROMPT_TYPE_PATTERNS .items ():
            for pattern in patterns :
                if re .search (pattern ,prompt_lower ):
                    return prompt_type 

        return 'general'

    def _has_specific_instructions (self ,prompt :str )->bool :
        """Проверяет наличие специфических инструкций в промпте"""
        prompt_lower =prompt .lower ()

        for pattern in self .INSTRUCTION_PATTERNS :
            if re .search (pattern ,prompt_lower ):
                return True 

        return False 

    def _create_preview (self ,prompt :str ,max_length :int =500 )->str :
        """Создает превью промпта"""
        if len (prompt )<=max_length :
            return prompt 

        return prompt [:max_length ]+"..."

    def _get_default_analysis (self )->PromptAnalysis :
        """Возвращает анализ по умолчанию"""
        return PromptAnalysis (
        token_estimate =100 ,
        complexity =PromptComplexity .SIMPLE ,
        prompt_type ='general',
        has_specific_instructions =False ,
        text_length =0 ,
        message_count =0 ,
        preview =""
        )



def create_prompt_analyzer ()->PromptAnalyzer :
    return PromptAnalyzer ()


__all__ =['PromptAnalyzer','create_prompt_analyzer']

"""
Система оценки моделей по нескольким критериям.
"""
import logging 
from typing import Dict ,List ,Optional 

from .types import (
ModelCandidate ,
ModelScore ,
ScoreWeights ,
PromptAnalysis ,
PromptComplexity 
)

logger =logging .getLogger (__name__ )


class ModelScorer :
    """
    Оценивает модели по нескольким критериям.
    """

    def __init__ (self ,weights :ScoreWeights ):
        """
        Args:
            weights: Веса критериев оценки
        """
        if not weights .validate ():
            raise ValueError ("Weights must sum to 1.0")

        self .weights =weights 

    def score_candidates (
    self ,
    candidates :List [ModelCandidate ],
    prompt_analysis :PromptAnalysis ,
    provider_loads :Dict [str ,float ]
    )->List [ModelScore ]:
        """
        Оценивает кандидатов.

        Args:
            candidates: Список кандидатов
            prompt_analysis: Анализ промпта
            provider_loads: Нагрузка на провайдеров

        Returns:
            Список оценок моделей
        """
        model_scores =[]

        for candidate in candidates :
            try :
                score =self ._score_candidate (
                candidate ,prompt_analysis ,provider_loads 
                )

                if score :
                    model_scores .append (score )

            except Exception as e :
                logger .warning (f"Error scoring candidate {candidate .name }: {e }")
                continue 

        return model_scores 

    def _score_candidate (
    self ,
    candidate :ModelCandidate ,
    prompt_analysis :PromptAnalysis ,
    provider_loads :Dict [str ,float ]
    )->Optional [ModelScore ]:
        """Оценивает одного кандидата"""

        cost_score =self ._calculate_cost_score (candidate ,prompt_analysis )


        complexity_score =self ._calculate_complexity_score (candidate ,prompt_analysis )


        context_score =self ._calculate_context_score (candidate ,prompt_analysis )


        priority_score =self ._calculate_priority_score (candidate )


        load_score =self ._calculate_load_score (candidate ,provider_loads )


        final_score =(
        cost_score *self .weights .cost +
        complexity_score *self .weights .complexity +
        context_score *self .weights .context +
        priority_score *self .weights .priority +
        load_score *self .weights .load 
        )


        estimated_cost =self ._estimate_cost (candidate ,prompt_analysis )


        reasoning =self ._generate_reasoning (
        candidate ,prompt_analysis ,
        cost_score ,complexity_score ,context_score ,
        priority_score ,load_score ,final_score 
        )

        return ModelScore (
        model_name =candidate .name ,
        provider_name =candidate .provider_name ,
        score =final_score ,
        cost_score =cost_score ,
        complexity_score =complexity_score ,
        context_score =context_score ,
        priority_score =priority_score ,
        load_score =load_score ,
        final_score =final_score ,
        estimated_cost =estimated_cost ,
        reasoning =reasoning 
        )

    def _calculate_cost_score (
    self ,
    candidate :ModelCandidate ,
    prompt_analysis :PromptAnalysis 
    )->float :
        """Оценивает модель по стоимости"""

        avg_price =(candidate .input_price +candidate .output_price )/2 



        if avg_price <=0.001 :
            return 1.0 
        elif avg_price <=0.01 :
            return 0.8 
        elif avg_price <=0.05 :
            return 0.6 
        elif avg_price <=0.1 :
            return 0.4 
        else :
            return 0.2 

    def _calculate_complexity_score (
    self ,
    candidate :ModelCandidate ,
    prompt_analysis :PromptAnalysis 
    )->float :
        """Оценивает соответствие модели сложности промпта"""
        complexity =prompt_analysis .complexity 
        context_window =candidate .context_window 


        if complexity ==PromptComplexity .SIMPLE :
            return 0.9 

        elif complexity ==PromptComplexity .STANDARD :
            if context_window >=4000 :
                return 0.8 
            else :
                return 0.6 

        elif complexity ==PromptComplexity .COMPLEX :
            if context_window >=8000 :
                return 0.9 
            elif context_window >=4000 :
                return 0.7 
            else :
                return 0.4 

        else :
            if context_window >=16000 :
                return 1.0 
            elif context_window >=8000 :
                return 0.8 
            else :
                return 0.3 

    def _calculate_context_score (
    self ,
    candidate :ModelCandidate ,
    prompt_analysis :PromptAnalysis 
    )->float :
        """Оценивает модель по размеру контекста"""
        context_window =candidate .context_window 
        required_context =prompt_analysis .token_estimate *1.5 

        if required_context ==0 :
            return 1.0 

        ratio =context_window /required_context 

        if ratio >=3.0 :
            return 1.0 
        elif ratio >=2.0 :
            return 0.9 
        elif ratio >=1.5 :
            return 0.8 
        elif ratio >=1.2 :
            return 0.6 
        elif ratio >=1.0 :
            return 0.4 
        else :
            return 0.1 

    def _calculate_priority_score (self ,candidate :ModelCandidate )->float :
        """Оценивает модель по приоритету"""
        priority =candidate .priority 


        return min (max ((priority -1 )/9 ,0 ),1 )

    def _calculate_load_score (
    self ,
    candidate :ModelCandidate ,
    provider_loads :Dict [str ,float ]
    )->float :
        """Оценивает модель по нагрузке на провайдера"""
        load =provider_loads .get (candidate .provider_name ,0.0 )


        return 1.0 -load 

    def _estimate_cost (
    self ,
    candidate :ModelCandidate ,
    prompt_analysis :PromptAnalysis 
    )->float :
        """Оценивает стоимость выполнения запроса"""
        input_tokens =prompt_analysis .token_estimate 
        output_tokens =input_tokens 

        input_price_per_token =candidate .input_price /1000 
        output_price_per_token =candidate .output_price /1000 

        input_cost =input_tokens *input_price_per_token 
        output_cost =output_tokens *output_price_per_token 

        return input_cost +output_cost 

    def _generate_reasoning (
    self ,
    candidate :ModelCandidate ,
    prompt_analysis :PromptAnalysis ,
    cost_score :float ,
    complexity_score :float ,
    context_score :float ,
    priority_score :float ,
    load_score :float ,
    final_score :float 
    )->List [str ]:
        """Генерирует объяснение оценки"""
        reasoning =[]


        reasoning .append (f"Model: {candidate .name } ({candidate .provider_name })")


        reasoning .extend (self ._get_score_explanations (
        cost_score ,complexity_score ,context_score ,
        priority_score ,load_score 
        ))

        reasoning .append (f"Final score: {final_score :.3f}")

        return reasoning 

    def _get_score_explanations (
    self ,
    cost_score :float ,
    complexity_score :float ,
    context_score :float ,
    priority_score :float ,
    load_score :float 
    )->List [str ]:
        """Возвращает объяснения для каждого критерия"""
        explanations =[]


        if cost_score >=0.8 :
            explanations .append ("✓ Excellent cost efficiency")
        elif cost_score >=0.6 :
            explanations .append ("✓ Good cost efficiency")
        elif cost_score >=0.4 :
            explanations .append ("~ Moderate cost")
        else :
            explanations .append ("✗ Higher than average cost")


        if complexity_score >=0.8 :
            explanations .append ("✓ Well-suited for prompt complexity")
        elif complexity_score >=0.6 :
            explanations .append ("✓ Adequate for prompt complexity")
        else :
            explanations .append ("~ May struggle with prompt complexity")


        if context_score >=0.8 :
            explanations .append ("✓ Ample context window")
        elif context_score >=0.6 :
            explanations .append ("✓ Sufficient context window")
        else :
            explanations .append ("~ Limited context window")


        if priority_score >=0.8 :
            explanations .append ("✓ High priority model")
        elif priority_score >=0.6 :
            explanations .append ("✓ Medium priority model")
        else :
            explanations .append ("~ Low priority model")


        if load_score >=0.8 :
            explanations .append ("✓ Low provider load")
        elif load_score >=0.6 :
            explanations .append ("~ Moderate provider load")
        else :
            explanations .append ("✗ High provider load")

        return explanations 



def create_model_scorer (
cost_weight :float =0.30 ,
complexity_weight :float =0.25 ,
context_weight :float =0.20 ,
priority_weight :float =0.15 ,
load_weight :float =0.10 
)->ModelScorer :
    weights =ScoreWeights (
    cost =cost_weight ,
    complexity =complexity_weight ,
    context =context_weight ,
    priority =priority_weight ,
    load =load_weight 
    )
    return ModelScorer (weights )


__all__ =['ModelScorer','create_model_scorer']
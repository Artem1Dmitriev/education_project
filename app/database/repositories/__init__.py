# app/database/repositories/__init__.py
from .user_repo import UserRepository
from .provider_repo import ProviderRepository
from .model_repo import ModelRepository
from .request_repo import RequestRepository
from .response_repo import ResponseRepository

from app.database.models import User, Provider, AIModel, Request, Response
from app.schemas import (
    UserCreate, UserUpdate,
    ProviderCreate, ProviderUpdate,
    ModelCreate, ModelUpdate,
    RequestCreate, RequestUpdate,
    ResponseCreate, ResponseUpdate
)

# Словарь для маппинга типов моделей на классы репозиториев
REPOSITORY_MAP = {
    "user": (UserRepository, User),
    "provider": (ProviderRepository, Provider),
    "model": (ModelRepository, AIModel),
    "request": (RequestRepository, Request),
    "response": (ResponseRepository, Response),
}

# Словарь для схем
SCHEMA_MAP = {
    "user": {"create": UserCreate, "update": UserUpdate},
    "provider": {"create": ProviderCreate, "update": ProviderUpdate},
    "model": {"create": ModelCreate, "update": ModelUpdate},
    "request": {"create": RequestCreate, "update": RequestUpdate},
    "response": {"create": ResponseCreate, "update": ResponseUpdate},
}


def get_repository(model_type: str, session):
    """
    Фабрика для получения репозитория по типу модели

    Args:
        model_type: тип модели ('user', 'provider', 'model', 'request', 'response')
        session: асинхронная сессия SQLAlchemy

    Returns:
        Экземпляр соответствующего репозитория

    Raises:
        ValueError: если тип модели неизвестен
    """
    if model_type not in REPOSITORY_MAP:
        raise ValueError(
            f"Unknown model type: {model_type}. "
            f"Available types: {list(REPOSITORY_MAP.keys())}"
        )

    repo_class, model_class = REPOSITORY_MAP[model_type]
    return repo_class(model_class, session)


def get_repository_class(model_type: str):
    """
    Получить класс репозитория по типу модели

    Args:
        model_type: тип модели

    Returns:
        Класс репозитория
    """
    if model_type not in REPOSITORY_MAP:
        raise ValueError(f"Unknown model type: {model_type}")

    return REPOSITORY_MAP[model_type][0]


def get_model_class(model_type: str):
    """
    Получить класс модели по типу модели

    Args:
        model_type: тип модели

    Returns:
        Класс SQLAlchemy модели
    """
    if model_type not in REPOSITORY_MAP:
        raise ValueError(f"Unknown model type: {model_type}")

    return REPOSITORY_MAP[model_type][1]


def get_schemas(model_type: str):
    """
    Получить схемы Pydantic для модели

    Args:
        model_type: тип модели

    Returns:
        Словарь с схемами create и update
    """
    if model_type not in SCHEMA_MAP:
        raise ValueError(f"Unknown model type: {model_type}")

    return SCHEMA_MAP[model_type]


# Экспортируем все репозитории для прямого импорта
__all__ = [
    'UserRepository',
    'ProviderRepository',
    'ModelRepository',
    'RequestRepository',
    'ResponseRepository',
    'get_repository',
    'get_repository_class',
    'get_model_class',
    'get_schemas',
]
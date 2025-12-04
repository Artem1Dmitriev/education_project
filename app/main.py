# app/main.py
import uvicorn
from app.application.app_factory import create_app
from app.application.config import settings

# Создаем приложение
app = create_app()


def run():
    """Функция для запуска через poetry scripts"""
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.APP_DEBUG else "warning",
    )


if __name__ == "__main__":
    run()
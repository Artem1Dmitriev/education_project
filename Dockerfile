FROM python:3.11-slim

WORKDIR /app

# Устанавливаем Poetry
RUN pip install poetry==1.7.0

# Копируем зависимости
COPY pyproject.toml poetry.lock* /app/

# Устанавливаем зависимости
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Копируем код
COPY . /app

# Создаем пользователя для безопасности
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
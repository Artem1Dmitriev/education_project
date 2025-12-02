FROM python:3.11-slim

WORKDIR /app

# Устанавливаем Poetry
RUN pip install poetry==1.7.0

# 1. Копируем только файлы зависимостей
COPY pyproject.toml poetry.lock* ./

# 2. Временно создаем пустую папку app
RUN mkdir -p app && echo "# Placeholder" > app/__init__.py

# 3. Устанавливаем зависимости
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# 4. Копируем остальной код (перезаписываем временную папку app)
COPY . .

# Создаем пользователя для безопасности
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["poetry", "run", "start"]
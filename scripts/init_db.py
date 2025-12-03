# scripts/init_db.py
import asyncio
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database.session import engine


async def create_schema():
    """Создание схемы и всех объектов БД"""
    async with engine.connect() as conn:
        print("🔄 Создаем схему ai_framework...")

        # 1. Создаем схему
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS ai_framework"))
        await conn.commit()

        print("✅ Схема создана")

        # 2. Создаем все таблицы через SQLAlchemy
        print("🔄 Создаем таблицы...")
        from app.database.models import Base
        async with engine.begin() as transaction:
            await transaction.run_sync(Base.metadata.create_all)

        print("✅ Таблицы созданы")

        # 3. Создаем индексы (которые не создались автоматически)
        print("🔄 Создаем дополнительные индексы...")
        indexes_sql = [
            # Индексы из PDF (страницы 18-20)
            "CREATE INDEX IF NOT EXISTS idx_providers_active ON ai_framework.providers(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_models_provider ON ai_framework.ai_models(provider_id)",
            "CREATE INDEX IF NOT EXISTS idx_models_availability ON ai_framework.ai_models(is_available)",
            "CREATE INDEX IF NOT EXISTS idx_models_price ON ai_framework.ai_models(input_price_per_1k, output_price_per_1k)",
            "CREATE INDEX IF NOT EXISTS idx_api_keys_provider ON ai_framework.api_keys(provider_id)",
            "CREATE INDEX IF NOT EXISTS idx_api_keys_active ON ai_framework.api_keys(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_api_keys_primary ON ai_framework.api_keys(is_primary)",
            "CREATE INDEX IF NOT EXISTS idx_requests_user ON ai_framework.requests(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_requests_model ON ai_framework.requests(model_id)",
            "CREATE INDEX IF NOT EXISTS idx_requests_timestamp ON ai_framework.requests(request_timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_requests_status ON ai_framework.requests(status)",
            "CREATE INDEX IF NOT EXISTS idx_requests_prompt_hash ON ai_framework.requests(prompt_hash)",
            "CREATE INDEX IF NOT EXISTS idx_requests_user_timestamp ON ai_framework.requests(user_id, request_timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_requests_status_time ON ai_framework.requests(status, request_timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_files_request ON ai_framework.files(request_id)",
            "CREATE INDEX IF NOT EXISTS idx_files_user ON ai_framework.files(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_files_processing_status ON ai_framework.files(processing_status)",
            "CREATE INDEX IF NOT EXISTS idx_responses_request ON ai_framework.responses(request_id)",
            "CREATE INDEX IF NOT EXISTS idx_responses_timestamp ON ai_framework.responses(response_timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_responses_cached ON ai_framework.responses(is_cached)",
            "CREATE INDEX IF NOT EXISTS idx_cache_request_hash ON ai_framework.cache(request_hash)",
            "CREATE INDEX IF NOT EXISTS idx_cache_similarity ON ai_framework.cache(similarity_score)",
            "CREATE INDEX IF NOT EXISTS idx_cache_expires ON ai_framework.cache(expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_cache_last_accessed ON ai_framework.cache(last_accessed)",
            "CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp ON ai_framework.error_logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_error_logs_type ON ai_framework.error_logs(error_type)",
            "CREATE INDEX IF NOT EXISTS idx_error_logs_request ON ai_framework.error_logs(request_id)",
            "CREATE INDEX IF NOT EXISTS idx_error_logs_user ON ai_framework.error_logs(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_stats_period ON ai_framework.usage_statistics(period_start, period_end)",
            "CREATE INDEX IF NOT EXISTS idx_stats_user_period ON ai_framework.usage_statistics(user_id, period_start)",
            "CREATE INDEX IF NOT EXISTS idx_stats_provider_period ON ai_framework.usage_statistics(provider_id, period_start)",
            "CREATE INDEX IF NOT EXISTS idx_stats_composite ON ai_framework.usage_statistics(period_start, user_id, provider_id)",
            "CREATE INDEX IF NOT EXISTS idx_settings_category ON ai_framework.system_settings(category)",
            "CREATE INDEX IF NOT EXISTS idx_settings_key ON ai_framework.system_settings(setting_key)",
            "CREATE INDEX IF NOT EXISTS idx_api_keys_active_primary ON ai_framework.api_keys(is_active, is_primary) WHERE is_active = TRUE AND is_primary = TRUE",
            "CREATE INDEX IF NOT EXISTS idx_models_available_cheap ON ai_framework.ai_models(is_available, input_price_per_1k, output_price_per_1k) WHERE is_available = TRUE",
        ]

        for sql in indexes_sql:
            try:
                await conn.execute(text(sql))
                print(f"  ✅ {sql[:50]}...")
            except Exception as e:
                print(f"  ⚠️  Ошибка при создании индекса: {e}")

        await conn.commit()
        print("✅ Индексы созданы")

        # 4. Создаем представления
        print("🔄 Создаем представления...")
        views_sql = [
            # Представление user_usage_stats
            """
            CREATE OR REPLACE VIEW ai_framework.user_usage_stats AS
            SELECT
                u.user_id,
                u.username,
                u.email,
                COUNT(r.request_id) as total_requests,
                COALESCE(SUM(r.input_tokens), 0) as total_input_tokens,
                COALESCE(SUM(r.output_tokens), 0) as total_output_tokens,
                COALESCE(SUM(r.total_cost), 0) as total_cost,
                MAX(r.request_timestamp) as last_request_date
            FROM ai_framework.users u
            LEFT JOIN ai_framework.requests r ON u.user_id = r.user_id
            GROUP BY u.user_id, u.username, u.email
            """,

            # Представление model_performance_stats
            """
            CREATE OR REPLACE VIEW ai_framework.model_performance_stats AS
            SELECT
                p.provider_id,
                p.provider_name,
                m.model_id,
                m.model_name,
                COUNT(r.request_id) as request_count,
                AVG(r.input_tokens) as avg_input_tokens,
                AVG(r.output_tokens) as avg_output_tokens,
                AVG(r.total_cost) as avg_cost_per_request,
                COALESCE(SUM(r.total_cost), 0) as total_cost,
                COUNT(el.error_id) as error_count,
                CASE
                    WHEN COUNT(r.request_id) > 0 THEN
                        (COUNT(r.request_id) - COUNT(el.error_id)) * 100.0 / COUNT(r.request_id)
                    ELSE 100
                END as success_rate
            FROM ai_framework.ai_models m
            JOIN ai_framework.providers p ON m.provider_id = p.provider_id
            LEFT JOIN ai_framework.requests r ON m.model_id = r.model_id
            LEFT JOIN ai_framework.error_logs el ON r.request_id = el.request_id
            GROUP BY p.provider_id, p.provider_name, m.model_id, m.model_name
            """,

            # Представление cache_efficiency_stats
            """
            CREATE OR REPLACE VIEW ai_framework.cache_efficiency_stats AS
            SELECT
                DATE(r.request_timestamp) as request_date,
                COUNT(r.request_id) as total_requests,
                COUNT(rc.response_id) as cached_responses,
                CASE
                    WHEN COUNT(r.request_id) > 0 THEN
                        COUNT(rc.response_id) * 100.0 / COUNT(r.request_id)
                    ELSE 0
                END as cache_hit_rate
            FROM ai_framework.requests r
            LEFT JOIN ai_framework.responses rc ON r.request_id = rc.request_id AND rc.is_cached = true
            GROUP BY DATE(r.request_timestamp)
            """,

            # Представление для мониторинга блокировок
            """
            CREATE OR REPLACE VIEW ai_framework.lock_monitor AS
            SELECT
                pid,
                usename as username,
                query,
                state,
                age(clock_timestamp(), query_start) as query_age
            FROM pg_stat_activity
            WHERE state != 'idle'
            AND query NOT ILIKE '%pg_stat_activity%'
            AND datname = current_database()
            """
        ]

        for sql in views_sql:
            try:
                await conn.execute(text(sql))
                print(f"  ✅ Представление создано")
            except Exception as e:
                print(f"  ⚠️  Ошибка при создании представления: {e}")

        await conn.commit()
        print("✅ Представления созданы")

        # 5. Создаем функции
        print("🔄 Создаем функции...")
        functions_sql = [
            # Функция для расчета стоимости запроса
            """
            CREATE OR REPLACE FUNCTION ai_framework.calculate_request_cost(
                p_input_tokens INTEGER,
                p_output_tokens INTEGER,
                p_input_price DECIMAL,
                p_output_price DECIMAL
            )
            RETURNS DECIMAL AS $$
            BEGIN
                RETURN (p_input_tokens * p_input_price / 1000) +
                       (p_output_tokens * p_output_price / 1000);
            END;
            $$ LANGUAGE plpgsql;
            """,

            # Функция для поиска в кеше по семантическому сходству
            """
            CREATE OR REPLACE FUNCTION ai_framework.find_similar_cached_response(
                p_request_hash VARCHAR(64),
                p_similarity_threshold DECIMAL DEFAULT 0.85
            )
            RETURNS TABLE(
                cache_id UUID,
                response_content TEXT,
                similarity_score DECIMAL
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT
                    c.cache_id,
                    r.content as response_content,
                    c.similarity_score
                FROM ai_framework.cache c
                JOIN ai_framework.responses r ON c.response_id = r.response_id
                WHERE c.similarity_score >= p_similarity_threshold
                    AND c.request_hash = p_request_hash
                    AND (c.expires_at IS NULL OR c.expires_at > CURRENT_TIMESTAMP)
                ORDER BY c.similarity_score DESC
                LIMIT 1;
            END;
            $$ LANGUAGE plpgsql;
            """,

            # Функция для ротации API ключей
            """
            CREATE OR REPLACE FUNCTION ai_framework.rotate_api_key(
                p_provider_name VARCHAR(50)
            )
            RETURNS TEXT AS $$
            DECLARE
                v_active_key TEXT;
                v_key_id UUID;
            BEGIN
                -- Находим наименее использованный активный ключ
                SELECT ak.api_key_encrypted, ak.key_id INTO v_active_key, v_key_id
                FROM ai_framework.api_keys ak
                JOIN ai_framework.providers p ON ak.provider_id = p.provider_id
                WHERE p.provider_name = p_provider_name
                    AND ak.is_active = true
                    AND (ak.usage_limit_usd IS NULL OR ak.current_usage_usd < ak.usage_limit_usd)
                ORDER BY ak.current_usage_usd ASC
                LIMIT 1;

                -- Если нашли ключ, возвращаем его
                IF v_active_key IS NOT NULL THEN
                    -- Обновляем счетчик использования
                    UPDATE ai_framework.api_keys
                    SET requests_count = requests_count + 1,
                        last_used = CURRENT_TIMESTAMP
                    WHERE key_id = v_key_id;

                    RETURN v_active_key;
                ELSE
                    -- Если активных ключей нет, логируем ошибку
                    INSERT INTO ai_framework.error_logs (
                        error_type, 
                        error_message, 
                        error_code
                    ) VALUES (
                        'API_KEY_ERROR',
                        'No available API keys for provider: ' || p_provider_name,
                        'NO_ACTIVE_KEYS'
                    );
                    RETURN NULL;
                END IF;
            END;
            $$ LANGUAGE plpgsql;
            """,

            # Функция для получения оптимальной модели
            """
            CREATE OR REPLACE FUNCTION ai_framework.get_optimal_model(
                p_required_context INTEGER,
                p_max_cost_per_1k DECIMAL
            )
            RETURNS TABLE(
                model_id UUID,
                model_name VARCHAR,
                provider_name VARCHAR,
                total_cost_estimate DECIMAL
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT
                    m.model_id,
                    m.model_name,
                    p.provider_name,
                    (m.input_price_per_1k + m.output_price_per_1k) as total_cost_estimate
                FROM ai_framework.ai_models m
                JOIN ai_framework.providers p ON m.provider_id = p.provider_id
                WHERE m.context_window >= p_required_context
                    AND (m.input_price_per_1k + m.output_price_per_1k) <= p_max_cost_per_1k
                    AND m.is_available = TRUE
                    AND p.is_active = TRUE
                ORDER BY total_cost_estimate ASC
                LIMIT 1;
            END;
            $$ LANGUAGE plpgsql;
            """,

            # Триггерная функция для обновления использования API-ключей
            """
            CREATE OR REPLACE FUNCTION ai_framework.update_api_key_usage()
            RETURNS TRIGGER AS $$
            BEGIN
                IF NEW.total_cost IS NOT NULL THEN
                    UPDATE ai_framework.api_keys
                    SET current_usage_usd = current_usage_usd + NEW.total_cost,
                        last_used = CURRENT_TIMESTAMP
                    WHERE key_id = NEW.api_key_id;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        ]

        for sql in functions_sql:
            try:
                await conn.execute(text(sql))
                print(f"  ✅ Функция создана")
            except Exception as e:
                print(f"  ⚠️  Ошибка при создании функции: {e}")

        await conn.commit()
        print("✅ Функции созданы")

        # 6. Создаем триггеры
        print("🔄 Создаем триггеры...")
        triggers_sql = [
            """
            DROP TRIGGER IF EXISTS trigger_update_api_usage ON ai_framework.requests;
            CREATE TRIGGER trigger_update_api_usage
                AFTER UPDATE OF total_cost ON ai_framework.requests
                FOR EACH ROW
                EXECUTE FUNCTION ai_framework.update_api_key_usage();
            """
        ]

        for sql in triggers_sql:
            try:
                await conn.execute(text(sql))
                print(f"  ✅ Триггер создан")
            except Exception as e:
                print(f"  ⚠️  Ошибка при создании триггера: {e}")

        await conn.commit()
        print("✅ Триггеры созданы")

        # 7. Создаем роли пользователей
        print("🔄 Создаем роли пользователей...")
        roles_sql = [
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'framework_admin') THEN
                    CREATE ROLE framework_admin WITH LOGIN PASSWORD 'Admin@Secure123!';
                END IF;

                IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'framework_app') THEN
                    CREATE ROLE framework_app WITH LOGIN PASSWORD 'App@Secure456!';
                END IF;

                IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'read_only_user') THEN
                    CREATE ROLE read_only_user WITH LOGIN PASSWORD 'ReadOnly@Secure789!';
                END IF;
            END
            $$;
            """,
            """
            GRANT CONNECT ON DATABASE ai_framework_db TO framework_admin, framework_app, read_only_user;
            GRANT USAGE ON SCHEMA ai_framework TO framework_admin, framework_app, read_only_user;
            GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ai_framework TO framework_app;
            GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ai_framework TO framework_admin;
            GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ai_framework TO framework_admin;
            GRANT SELECT ON ALL TABLES IN SCHEMA ai_framework TO read_only_user;
            GRANT USAGE ON SEQUENCE ai_framework.request_number_seq TO framework_app, framework_admin;
            """
        ]

        for sql in roles_sql:
            try:
                await conn.execute(text(sql))
                print(f"  ✅ Роли созданы")
            except Exception as e:
                print(f"  ⚠️  Ошибка при создании ролей: {e}")

        await conn.commit()
        print("✅ Роли созданы")


async def seed_initial_data():
    """Заполнение начальными данными"""
    async with engine.connect() as conn:
        print("\n🔄 Заполняем начальными данными...")

        # Проверяем, есть ли уже данные
        result = await conn.execute(text("SELECT COUNT(*) FROM ai_framework.providers"))
        count = result.scalar()

        if count > 0:
            print("⚠️  Данные уже существуют, пропускаем...")
            return

        # Добавляем провайдеров
        providers_sql = """
        INSERT INTO ai_framework.providers (provider_id, provider_name, base_url, auth_type, is_active) VALUES
            (gen_random_uuid(), 'OpenAI', 'https://api.openai.com/v1', 'Bearer', true),
            (gen_random_uuid(), 'Anthropic', 'https://api.anthropic.com/v1', 'X-API-Key', true),
            (gen_random_uuid(), 'Google Gemini', 'https://generativelanguage.googleapis.com/v1', 'APIKey', true),
            (gen_random_uuid(), 'Local Ollama', 'http://localhost:11434/v1', 'Bearer', true);
        """
        await conn.execute(text(providers_sql))
        print("  ✅ Провайдеры добавлены")

        # Добавляем модели
        models_sql = """
        INSERT INTO ai_framework.ai_models (model_id, provider_id, model_name, context_window, input_price_per_1k, output_price_per_1k, is_available) VALUES
            (gen_random_uuid(), (SELECT provider_id FROM ai_framework.providers WHERE provider_name = 'OpenAI'), 'gpt-4o', 128000, 0.005, 0.015, true),
            (gen_random_uuid(), (SELECT provider_id FROM ai_framework.providers WHERE provider_name = 'OpenAI'), 'gpt-4-turbo', 128000, 0.010, 0.030, true),
            (gen_random_uuid(), (SELECT provider_id FROM ai_framework.providers WHERE provider_name = 'Anthropic'), 'claude-3-opus-20240229', 200000, 0.015, 0.075, true),
            (gen_random_uuid(), (SELECT provider_id FROM ai_framework.providers WHERE provider_name = 'Google Gemini'), 'gemini-1.5-pro', 1000000, 0.0035, 0.0105, true);
        """
        await conn.execute(text(models_sql))
        print("  ✅ Модели добавлены")

        # Добавляем тестового пользователя
        users_sql = """
        INSERT INTO ai_framework.users (user_id, username, email, is_active) VALUES
            (gen_random_uuid(), 'test_user', 'test@example.com', true);
        """
        await conn.execute(text(users_sql))
        print("  ✅ Тестовый пользователь добавлен")

        # Добавляем системные настройки
        settings_sql = """
        INSERT INTO ai_framework.system_settings (setting_key, setting_value, setting_type, category, description) VALUES
            ('default_temperature', '0.7', 'float', 'model', 'Температура по умолчанию для моделей'),
            ('default_max_tokens', '2000', 'integer', 'model', 'Максимальное количество токенов по умолчанию'),
            ('cache_enabled', 'true', 'boolean', 'cache', 'Включено ли кеширование'),
            ('cache_ttl_days', '30', 'integer', 'cache', 'Время жизни кеша в днях'),
            ('similarity_threshold', '0.85', 'float', 'cache', 'Порог сходства для семантического поиска');
        """
        await conn.execute(text(settings_sql))
        print("  ✅ Системные настройки добавлены")

        await conn.commit()
        print("✅ Начальные данные добавлены")


async def analyze_tables():
    """Анализ таблиц для оптимизации запросов"""
    async with engine.connect() as conn:
        print("\n🔄 Анализируем таблицы...")

        tables = [
            'users', 'providers', 'ai_models', 'api_keys', 'requests',
            'files', 'responses', 'cache', 'error_logs', 'usage_statistics',
            'system_settings'
        ]

        for table in tables:
            try:
                await conn.execute(text(f"ANALYZE ai_framework.{table}"))
                print(f"  ✅ Таблица {table} проанализирована")
            except Exception as e:
                print(f"  ⚠️  Ошибка при анализе таблицы {table}: {e}")

        await conn.commit()
        print("✅ Анализ таблиц завершен")


async def verify_structure():
    """Проверка созданной структуры"""
    async with engine.connect() as conn:
        print("\n🔍 Проверяем структуру БД...")

        # Проверяем количество таблиц
        result = await conn.execute(text("""
            SELECT COUNT(*) as table_count
            FROM information_schema.tables
            WHERE table_schema = 'ai_framework'
        """))
        table_count = result.scalar()
        print(f"📊 Таблиц в схеме: {table_count}")

        # Список таблиц
        result = await conn.execute(text("""
            SELECT table_name, COUNT(*) as column_count
            FROM information_schema.columns
            WHERE table_schema = 'ai_framework'
            GROUP BY table_name
            ORDER BY table_name
        """))

        print("📋 Список таблиц и колонок:")
        for row in result:
            print(f"  - {row.table_name}: {row.column_count} колонок")

        # Проверяем индексы
        result = await conn.execute(text("""
            SELECT COUNT(*) as index_count
            FROM pg_indexes
            WHERE schemaname = 'ai_framework'
        """))
        index_count = result.scalar()
        print(f"📊 Индексов: {index_count}")

        # Проверяем представления
        result = await conn.execute(text("""
            SELECT COUNT(*) as view_count
            FROM information_schema.views
            WHERE table_schema = 'ai_framework'
        """))
        view_count = result.scalar()
        print(f"📊 Представлений: {view_count}")

        print("\n🎉 Проверка завершена успешно!")


async def main():
    """Основная функция"""
    print("🚀 Начинаем создание структуры БД...")

    try:
        # 1. Создаем схему и таблицы
        await create_schema()

        # 2. Заполняем начальными данными
        await seed_initial_data()

        # 3. Анализируем таблицы
        await analyze_tables()

        # 4. Проверяем структуру
        await verify_structure()

        print("\n✨ Структура БД успешно создана и настроена!")
        print(f"📊 База данных: {engine.url.database}")
        print(f"👤 Пользователь: {engine.url.username}")

    except Exception as e:
        print(f"\n❌ Ошибка при создании структуры БД: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
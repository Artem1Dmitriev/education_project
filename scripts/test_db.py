# scripts/test_db_connection.py
import asyncio
from sqlalchemy import text
from app.database.session import engine


async def test_connection():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"✅ Database connection successful: {result.scalar()}")

            # Проверим существование схемы
            result = await conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = 'ai_framework'
            """))
            if result.scalar():
                print("✅ Schema 'ai_framework' exists")
            else:
                print("❌ Schema 'ai_framework' does not exist")

    except Exception as e:
        print(f"❌ Database connection failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_connection())
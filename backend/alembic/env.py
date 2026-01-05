# alembic/env.py
import asyncio
from logging.config import fileConfig
from typing import Any

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, async_engine_from_config
from sqlalchemy import MetaData  # Добавляем для naming convention

from alembic import context

# Импортируем конфиг до использования context.config
from app.core.config import settings
from app.models import Base

# ======================
# 1. SETUP NAMING CONVENTION (КРИТИЧЕСКИ ВАЖНО!)
# ======================
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Создаем метаданные с соглашением об именовании
metadata = MetaData(naming_convention=convention)
target_metadata = Base.metadata  # Используем метаданные из ваших моделей

# ======================
# 2. ПРАВИЛЬНАЯ НАСТРОЙКА КОНФИГУРАЦИИ
# ======================
config = context.config

# Устанавливаем URL базы данных из настроек
section = config.config_ini_section
config.set_section_option(section, "sqlalchemy.url", settings.db.DATABASE_URL)

# Настройка логирования
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ======================
# 3. ФУНКЦИИ МИГРАЦИЙ
# ======================
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Сравнивать типы колонок
        compare_server_default=True,  # Сравнивать серверные значения по умолчанию
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Выполняет миграции с существующим соединением."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Запускает асинхронные миграции."""
    connectable: AsyncEngine = async_engine_from_config(
        config.get_section(section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,  # Используем SQLAlchemy 2.0 стиль
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    try:
        asyncio.run(run_async_migrations())
    except Exception as e:
        print(f"❌ Error during migrations: {e}")
        raise


# ======================
# 4. ВЫБОР РЕЖИМА
# ======================
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
# app/database.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings


class DatabaseHelper:
    def __init__(
            self, 
            url: str,
            echo: bool = True,
            pool_size: int = 5,
            max_overflow: int = 10,
    ):
        self.engine: AsyncEngine = create_async_engine(
            url=url,
            echo=echo,
            pool_size=pool_size,
            max_overflow=max_overflow,
        )
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    async def dispose(self):
        """Закрывает все соединения с базой данных"""
        await self.engine.dispose()
    
    async def session_getter(self) -> AsyncGenerator[AsyncSession, None]:
        """Генератор для получения сессии БД в FastAPI зависимостях"""
        async with self.session_factory() as session:
            yield session


db_helper = DatabaseHelper(
    url=settings.db.DATABASE_URL,
    echo=settings.db.DB_ECHO,
    pool_size=settings.db.DB_POOL_SIZE,
    max_overflow=settings.db.DB_MAX_OVERFLOW,
)
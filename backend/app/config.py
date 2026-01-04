# app/config.py
from pydantic_settings import BaseSettings
from pydantic import BaseModel


class DataBaseConfig(BaseModel):

    # Настройки базы данных
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "shop"
    DB_USER: str = "user"
    DB_PASSWORD: str = "password"
    DB_ECHO: bool = True  
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    @property
    def DATABASE_URL(self) -> str:
        """Формирует URL для подключения к БД"""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"       

    naming_convention: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
    }

class Settings(BaseSettings):
    app_name: str = "AIO Edication"
    debug: bool = True
    cors_origins: list = [
        "http://localhost:5137",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5137"
    ]
    static_dir: str = "static"
    images_dir: str = "static/images"

    db: DataBaseConfig = DataBaseConfig()

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
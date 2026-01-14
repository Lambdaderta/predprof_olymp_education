# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field, SecretStr
from typing import List, Optional, Any
from functools import lru_cache
import os

class DataBaseConfig(BaseModel):
    # Все поля обязательные, без значений по умолчанию!
    DB_HOST: str = Field(..., description="Database host")
    DB_PORT: int = Field(5432, description="Database port")
    DB_NAME: str = Field(..., description="Database name")
    DB_USER: str = Field(..., description="Database user")
    DB_PASSWORD: SecretStr = Field(..., description="Database password")  # SecretStr скрывает значение в логах
    DB_ECHO: bool = Field(False, description="Enable SQL echo")
    DB_POOL_SIZE: int = Field(5, description="Database pool size")
    DB_MAX_OVERFLOW: int = Field(10, description="Database max overflow")

    @property
    def DATABASE_URL(self) -> str:
        # SecretStr.get_secret_value() чтобы получить реальное значение
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"       

    naming_convention: dict[str, str] = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }

class MinIOConfig(BaseModel):
    MINIO_ENDPOINT: str = Field(..., description="MinIO endpoint")
    MINIO_ACCESS_KEY: str = Field(..., description="MinIO access key")
    MINIO_SECRET_KEY: SecretStr = Field(..., description="MinIO secret key")
    MINIO_SECURE: bool = Field(False, description="Use HTTPS for MinIO")
    MINIO_BUCKET_NAME: str = Field("aio-edu", description="MinIO bucket name")
    
    @property
    def minio_url(self) -> str:
        protocol = "https" if self.MINIO_SECURE else "http"
        return f"{protocol}://{self.MINIO_ENDPOINT}"

class AIConfig(BaseModel):
    AI_API_BASE: str = Field(..., description="AI API base URL")
    AI_DEFAULT_MODEL: str = Field("local-model", description="Default AI model")
    AI_TIMEOUT: int = Field(60, description="AI request timeout in seconds")

class SecurityConfig(BaseModel):
    JWT_SECRET_KEY: SecretStr = Field(..., description="JWT secret key")  # Обязательное поле!
    JWT_ALGORITHM: str = Field("HS256", description="JWT algorithm")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, description="Access token expiration")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, description="Refresh token expiration")

class Settings(BaseSettings):
    app_name: str = Field("AIO Education", description="Application name")
    debug: bool = Field(False, description="Debug mode")
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5137",
            "http://localhost:3000",
        ],
        description="CORS origins"
    )
    static_dir: str = Field("static", description="Static files directory")
    images_dir: str = Field("static/images", description="Images directory")

    db: DataBaseConfig
    minio: MinIOConfig
    ai: AIConfig
    security: SecurityConfig

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = False
        env_nested_delimiter = '__'  # Для вложенных объектов

@lru_cache()
def get_settings() -> Settings:
    """Кэшированный экземпляр настроек"""
    return Settings()

settings = get_settings()
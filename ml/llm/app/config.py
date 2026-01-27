from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Пути
    models_dir: str = "./models"
    llama_cpp_path: str = "./llama.cpp/build/bin/llama-server"
    
    # Таймауты
    inactivity_timeout: int = 30
    health_check_timeout: int = 30
    
    # Ресурсы
    cpu_threads: Optional[int] = None
    n_gpu_layers: int = 0  
    
    # Логирование
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()
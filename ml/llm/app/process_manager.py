import asyncio
import logging
import httpx
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
import socket

logger = logging.getLogger(__name__)

class ProcessManager:
    def __init__(
        self,
        llama_cpp_path: str = None,
        models_dir: str = None,
        inactivity_timeout: int = 60
    ):
        # Берем из переменных окружения, если не передано
        self.llama_cpp_path = Path(llama_cpp_path or os.getenv("LLAMA_CPP_PATH", "./llama.cpp/build/bin/llama-server"))
        self.models_dir = Path(models_dir or os.getenv("MODELS_DIR", "./models"))
        
        # Делаем пути абсолютными
        if not self.llama_cpp_path.is_absolute():
            self.llama_cpp_path = Path.cwd() / self.llama_cpp_path
        if not self.models_dir.is_absolute():
            self.models_dir = Path.cwd() / self.models_dir
        
        # Проверяем права на выполнение
        if not os.access(self.llama_cpp_path, os.X_OK):
            os.chmod(self.llama_cpp_path, 0o755)
        
        # Словарь для хранения информации о запущенных серверах
        self.active_servers: Dict[str, dict] = {}
        self.lock = asyncio.Lock()
        
        # Автоматически обнаруживаем модели
        self.model_configs = self._discover_models()
        logger.info(f"Discovered {len(self.model_configs)} models")
    
    def _discover_models(self) -> Dict[str, dict]:
        """Автоматическое обнаружение моделей в папке models"""
        configs = {}
        
        if not self.models_dir.exists():
            logger.warning(f"Models directory {self.models_dir} does not exist")
            return configs
        
        # Ищем все .gguf файлы
        for file in self.models_dir.glob("*.gguf"):
            model_name = file.stem
            mmproj = self._find_mmproj(model_name)
            
            configs[model_name] = {
                "model_path": str(file.absolute()),
                "model_file": file.name,
                "ctx_size": 4096,
                "n_gpu_layers": 0,
                "mmproj": mmproj
            }
            
            # Пытаемся определить оптимальный размер контекста по имени файла
            if "32k" in model_name.lower():
                configs[model_name]["ctx_size"] = 32768
            elif "16k" in model_name.lower():
                configs[model_name]["ctx_size"] = 16384
            elif "8k" in model_name.lower():
                configs[model_name]["ctx_size"] = 8192
            elif "4k" in model_name.lower():
                configs[model_name]["ctx_size"] = 4096
            
            logger.info(f"Discovered model: {model_name} (ctx: {configs[model_name]['ctx_size']})")
        
        return configs
    
    def _find_mmproj(self, model_name: str) -> Optional[str]:
        """Находит mmproj файл для VLM моделей"""
        # Варианты имен mmproj файлов
        candidates = [
            f"{model_name}.mmproj",
            f"{model_name.replace('-f16', '').replace('-Q4_K_M', '')}.mmproj",
            f"{model_name.split('-')[0]}.mmproj",
        ]
        
        for candidate in candidates:
            mmproj_path = self.models_dir / candidate
            if mmproj_path.exists():
                return str(mmproj_path.absolute())
        
        # Ищем любой mmproj файл
        for file in self.models_dir.glob("*.mmproj"):
            return str(file.absolute())
        
        return None
    
    def get_available_models(self) -> List[str]:
        """Возвращает список доступных моделей"""
        return list(self.model_configs.keys())
    
    def get_model_config(self, model_name: str) -> dict:
        """Возвращает конфигурацию модели"""
        config = self.model_configs.get(model_name)
        if not config:
            raise ValueError(f"Model {model_name} not found")
        return config
    
    async def get_server_for_model(self, model_name: str) -> str:
        """Запускает сервер для модели или возвращает существующий"""
        async with self.lock:
            # Если сервер уже запущен, обновляем активность и возвращаем URL
            if model_name in self.active_servers:
                self.active_servers[model_name]["last_activity"] = datetime.now()
                return f"http://127.0.0.1:{self.active_servers[model_name]['port']}"
            
            # Запускаем новый сервер
            port = await self._find_free_port()
            server_info = await self._start_server(model_name, port)
            self.active_servers[model_name] = server_info
            
            return f"http://127.0.0.1:{port}"
    
    async def _find_free_port(self) -> int:
        """Находит свободный порт"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]
    
    async def _start_server(self, model_name: str, port: int) -> dict:
        """Запускает llama.cpp сервер для модели"""
        config = self.get_model_config(model_name)
        
        # Формируем команду с базовыми параметрами
        cmd = [
            str(self.llama_cpp_path.absolute()),
            "-m", config["model_path"],
            "--port", str(port),
            "--host", "127.0.0.1",
            "--ctx-size", str(config["ctx_size"]),
            "--n-predict", "-1",
            "--threads", str(min(os.cpu_count() or 4, 8)),
            "--batch-size", "512",
            "--keep", "0",
            # Используем настройку из конфига вместо жесткого значения
            "--n-gpu-layers", str(config.get("n_gpu_layers", 0)),
        ]
        
        # Добавляем mmproj если есть (для VLM)
        if config["mmproj"]:
            cmd.extend(["--mmproj", config["mmproj"]])
        
        logger.info(f"Starting llama.cpp server for {model_name} on port {port}")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        # Запускаем процесс
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Запускаем задачи для логирования stdout/stderr
        asyncio.create_task(self._log_output(process.stdout, f"{model_name}-stdout"))
        asyncio.create_task(self._log_output(process.stderr, f"{model_name}-stderr"))
        
        # Ждем готовности сервера (увеличиваем таймаут)
        await self._wait_for_server(port)
        
        return {
            "process": process,
            "port": port,
            "model_name": model_name,
            "last_activity": datetime.now()
        }
    
    async def _log_output(self, pipe, prefix: str):
        """Логирует вывод процесса"""
        try:
            while True:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, pipe.readline
                )
                if not line:
                    break
                line = line.strip()
                if line:
                    # Логируем только важные сообщения
                    if "error" in line.lower() or "warning" in line.lower() or "ready" in line.lower():
                        logger.info(f"[{prefix}] {line}")
                    else:
                        logger.debug(f"[{prefix}] {line}")
        except Exception as e:
            logger.error(f"Error logging output for {prefix}: {e}")
    
    async def _wait_for_server(self, port: int, timeout: int = 120):
        """Ожидает готовности сервера с увеличенным таймаутом"""
        url = f"http://127.0.0.1:{port}/health"
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            while time.time() - start_time < timeout:
                try:
                    response = await client.get(url, timeout=5.0)
                    if response.status_code == 200:
                        logger.info(f"Server on port {port} is ready")
                        return
                except (httpx.ConnectError, httpx.TimeoutException):
                    # Ждем перед следующей попыткой
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.warning(f"Health check error: {e}")
                    await asyncio.sleep(1)
            
            # Если не дождались, пытаемся получить логи ошибок
            logger.error(f"Server failed to start within {timeout} seconds")
            raise TimeoutError(f"Server failed to start within {timeout} seconds")
    
    async def update_activity(self, model_name: str) -> str:
        """Обновляет время активности модели и возвращает URL сервера"""
        async with self.lock:
            if model_name in self.active_servers:
                self.active_servers[model_name]["last_activity"] = datetime.now()
                return f"http://127.0.0.1:{self.active_servers[model_name]['port']}"
            else:
                # Если сервер не запущен, запускаем его
                return await self.get_server_for_model(model_name)
    
    async def cleanup_inactive(self):
        """Останавливает неактивные серверы"""
        async with self.lock:
            now = datetime.now()
            servers_to_remove = []
            
            for model_name, info in self.active_servers.items():
                inactive_time = (now - info["last_activity"]).total_seconds()
                
                if inactive_time > self.inactivity_timeout:
                    logger.info(f"Stopping inactive server for {model_name} "
                              f"(inactive for {inactive_time:.1f}s)")
                    await self._stop_server(info["process"])
                    servers_to_remove.append(model_name)
            
            for model_name in servers_to_remove:
                if model_name in self.active_servers:
                    del self.active_servers[model_name]
    
    async def _stop_server(self, process: subprocess.Popen):
        """Останавливает процесс сервера"""
        try:
            # Отправляем SIGTERM
            process.terminate()
            
            # Ждем завершения
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Принудительно завершаем
                process.kill()
                process.wait()
                    
        except Exception as e:
            logger.error(f"Error stopping process: {e}")
    
    async def cleanup_all(self):
        """Останавливает все серверы при завершении"""
        async with self.lock:
            for model_name, info in self.active_servers.items():
                logger.info(f"Stopping server for {model_name}")
                await self._stop_server(info["process"])
            self.active_servers.clear()
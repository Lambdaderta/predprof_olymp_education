import asyncio
import subprocess
import os

async def run_command(cmd: list[str]) -> tuple[int, str, str]:
    """Запускает команду и возвращает результат"""
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    return (
        process.returncode,
        stdout.decode() if stdout else "",
        stderr.decode() if stderr else ""
    )

def check_llama_cpp() -> bool:
    """Проверяет наличие llama.cpp сервера"""
    import subprocess
    import sys
    
    try:
        # Пытаемся найти сервер в разных местах
        possible_paths = [
            "./llama.cpp/build/bin/llama-server",
            "./llama.cpp/build/bin/llama-server",
        ]
        
        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return True
        
        # Пытаемся запустить который в PATH
        result = subprocess.run(["which", "llama-server"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return True
            
        return False
    except:
        return False
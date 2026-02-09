#!/usr/bin/env python3
"""
Запуск сервера llama.cpp OpenAI API
"""
import os
import sys
import uvicorn

if __name__ == "__main__":
    # Проверяем наличие llama.cpp
    llama_path = "llama-server"
    if not os.path.exists(llama_path):
        print(f"ERROR: llama.cpp server not found at {llama_path}")
        print("Please build it first:")
        print("  cd llama.cpp && mkdir build && cd build")
        print("  cmake .. -DLLAMA_BUILD_SERVER=ON")
        print("  make -j$(nproc)")
        sys.exit(1)
    
    # Проверяем наличие моделей
    models_dir = "./models"
    if not os.path.exists(models_dir):
        print(f"WARNING: Models directory {models_dir} not found")
        os.makedirs(models_dir, exist_ok=True)
        print(f"Created {models_dir}. Please add your .gguf models there.")
    
    # Запускаем сервер
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info",
        timeout_keep_alive=300  # Увеличиваем keep-alive таймаут
    )
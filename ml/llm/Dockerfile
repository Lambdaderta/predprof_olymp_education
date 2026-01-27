FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости для llama.cpp
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем только необходимые файлы
COPY requirements.txt .
COPY run.py .
COPY app/ ./app/

# Копируем собранный llama-server
COPY llama.cpp/build/bin/llama-server /usr/local/bin/llama-server
RUN chmod +x /usr/local/bin/llama-server

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Создаем директорию для моделей
RUN mkdir -p /models

# Переменные окружения по умолчанию
ENV MODELS_DIR=/models
ENV LLAMA_CPP_PATH=/usr/local/bin/llama-server
ENV PORT=8000
ENV HOST=0.0.0.0
ENV LOG_LEVEL=INFO
ENV INACTIVITY_TIMEOUT=60

# Открываем порт
EXPOSE 8000

# Запускаем приложение
CMD ["python", "run.py"]
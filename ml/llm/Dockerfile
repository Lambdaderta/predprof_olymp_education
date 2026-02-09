FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 curl\
    && rm -rf /var/lib/apt/lists/*

# Копируем ПРЕДВАРИТЕЛЬНО СОБРАННЫЙ бинарник
COPY llama-server /usr/local/bin/llama-server
RUN chmod +x /usr/local/bin/llama-server

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /models

ENV MODELS_DIR=/models
ENV LLAMA_CPP_PATH=/usr/local/bin/llama-server
ENV PORT=8000
ENV HOST=0.0.0.0

EXPOSE 8000

CMD ["python", "run.py"]
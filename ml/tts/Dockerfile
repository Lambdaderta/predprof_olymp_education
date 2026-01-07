FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Создаем виртуальное окружение (рекомендуется)
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Проверяем установку uvicorn
RUN which uvicorn || echo "uvicorn not found in PATH"

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Run the application с явным указанием интерпретатора
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
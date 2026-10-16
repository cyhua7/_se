FROM python:3.11-slim

WORKDIR /app

# 安裝系統相依套件
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Python 相關套件
RUN pip install --no-cache-dir fastapi uvicorn psycopg2-binary

COPY app /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
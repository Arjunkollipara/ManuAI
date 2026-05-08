FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        curl \
    && python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --only-binary :all: \
        numpy==1.26.2 pandas==2.1.3 \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip freeze > /app/requirements.lock \
    && apt-get purge -y gcc g++ \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Create required directories
RUN mkdir -p logs data/raw data/staged data/curated \
    data/vector_store ml/models documents

# Expose the default application port for local and container runtimes
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s \
    --start-period=60s \
    CMD ["sh", "-c", "curl -fsS http://127.0.0.1:${PORT:-8000}/health || exit 1"]

# Start command
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${UVICORN_WORKERS:-1} --proxy-headers --forwarded-allow-ips='*' --access-log --log-level info"]

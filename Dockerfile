FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
# Pre-install lightweight CPU-only PyTorch wheel.
# Prevents downloading 2.8GB+ of unused CUDA/Triton/Nvidia GPU binaries on servers,
# cutting container build time from 12+ minutes down to ~30 seconds.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend /app

ENV PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    DEBUG=false \
    PRODUCTION_DATA_INTEGRITY_MODE=true

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

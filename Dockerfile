# Production Dockerfile for Nyaya Darshana
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    ENVIRONMENT=production \
    NYAYA_DATA_DIR=/var/lib/nyaya \
    RAW_DIR=/var/lib/nyaya/uploads \
    NYAYA_LOG_DIR=/var/lib/nyaya/logs \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
RUN groupadd --system --gid 10001 nyaya \
    && useradd --system --uid 10001 --gid nyaya --create-home nyaya \
    && mkdir -p /var/lib/nyaya/uploads /var/lib/nyaya/logs \
    && chown -R nyaya:nyaya /var/lib/nyaya /app
COPY --chown=nyaya:nyaya . .
RUN python scripts/release_preflight.py --repository-only

USER nyaya

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl --fail --silent "http://127.0.0.1:${PORT:-8000}/health" > /dev/null || exit 1

# Start server
CMD ["sh", "-c", "python scripts/release_preflight.py --environment-only && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1} --proxy-headers --forwarded-allow-ips=${FORWARDED_ALLOW_IPS:-127.0.0.1}"]

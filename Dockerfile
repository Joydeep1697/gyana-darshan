# Production Dockerfile for Nyaya Darshan
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Environment setup
ENV PORT=8000
ENV HOST=0.0.0.0
ENV ENVIRONMENT=production
ENV HF_HUB_OFFLINE=1
ENV TRANSFORMERS_OFFLINE=1

EXPOSE 8000

# Start server
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

# syntax=docker/dockerfile:1
FROM python:3.11-slim-bookworm

# Configure environment settings
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    TESSERACT_BIN=/usr/bin/tesseract \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata \
    HF_HOME=/app/backend/data/huggingface \
    PYTHONPATH=/app/backend

WORKDIR /app

# Install system dependencies:
# - tesseract-ocr with English and Nepali traineddata
# - curl for Railway container healthchecks
# - ca-certificates for secure HTTPS egress (Gemini API, Hugging Face)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-nep \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/share/tesseract-ocr/5/tessdata /usr/share/tessdata

# Install Python dependencies first for optimal Docker layer caching
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy curated static knowledge assets required at runtime
COPY data/okf /app/data/okf
COPY data/knowledge /app/data/knowledge

# Copy backend application codebase
COPY backend /app/backend

# Create runtime directories for Railway persistent volume mount (/app/backend/data)
RUN mkdir -p /app/backend/data/uploads \
             /app/backend/data/vectors \
             /app/backend/data/huggingface

EXPOSE ${PORT}

# Start FastAPI via Uvicorn on 0.0.0.0:$PORT
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]


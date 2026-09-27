FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies required for PDF parsing and OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install requirements in order per RULES.md §5.3
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY requirements-ml.txt .
RUN pip install --no-cache-dir -r requirements-ml.txt

# Copy application source code
COPY app/ ./app/
COPY rag/ ./rag/
COPY data/ ./data/

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

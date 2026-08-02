# =============================================================================
# 🐍 PYTHON / DJANGO BACKEND DOCKERFILE (RENDER READY — 512MB RAM OPTIMIZED)
# =============================================================================
FROM python:3.11-slim

# Set environment variables for Render memory efficiency
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WEB_CONCURRENCY=1 \
    PORT=8000

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy & install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . /app/

# Expose port 8000
EXPOSE 8000

# Collect static & start Gunicorn with 1 worker + 2 threads to prevent OOM
CMD ["sh", "-c", "python manage.py collectstatic --noinput && python -m gunicorn src_backend.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 2 --timeout 120"]

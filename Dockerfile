# =============================================================================
# 🐍 DJANGO BACKEND DOCKERFILE (RENDER READY)
# =============================================================================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies
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

# Run collectstatic & start Gunicorn
CMD ["sh", "-c", "python manage.py collectstatic --noinput && gunicorn src_backend.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3"]

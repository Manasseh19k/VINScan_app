FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for building some packages (psycopg2, Pillow, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

# Copy project
COPY . /app

# Collect static files (if any)
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

# Use shell form to allow PORT env var expansion (Railway provides $PORT)
CMD ["sh", "-c", "gunicorn vin_project.wsgi --workers 4 --bind 0.0.0.0:${PORT:-8000} --timeout 120"]

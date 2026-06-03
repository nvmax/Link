FROM python:3.12-slim

# Set runtime/build-time environment flags
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install critical system libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy remaining source code files (respecting .dockerignore)
COPY . .

# Create a non-root system user and configure directory ownership
RUN useradd -u 10001 -m appuser && \
    mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

USER appuser

# Expose backend API daemon control port
EXPOSE 8001

# Docker native healthcheck using standard python urllib.request
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"

# Start the unified backend (discord bot + management API)
CMD ["python", "main.py"]

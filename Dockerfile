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

# Expose backend API daemon control port
EXPOSE 8001

# Start the unified backend (discord bot + management API)
CMD ["python", "main.py"]

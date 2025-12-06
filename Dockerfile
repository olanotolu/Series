# Series Hackathon - Production Dockerfile
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p audio_files dlq

# Set environment variables (can be overridden)
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Health check (HTTP endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the consumer
CMD ["python", "consumer.py"]


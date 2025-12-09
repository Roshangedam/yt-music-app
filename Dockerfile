# ============================================================================
# FILE: Dockerfile (Simple - All-in-One)
# ============================================================================
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Always upgrade to latest versions (YouTube APIs change frequently)
RUN pip install --no-cache-dir --upgrade yt-dlp ytmusicapi
RUN pip install pydantic[email]
# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
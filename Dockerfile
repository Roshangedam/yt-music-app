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

# Force install latest yt-dlp (CRITICAL: YouTube bot detection bypass)
# This must run AFTER requirements.txt to override any pinned versions
RUN pip uninstall -y yt-dlp && pip install --no-cache-dir --upgrade yt-dlp
RUN pip install --no-cache-dir --upgrade ytmusicapi
RUN pip install pydantic[email]


# Verify yt-dlp version (should be 2024.12.x or newer)
RUN python -c "import yt_dlp; print(f'yt-dlp version: {yt_dlp.version.__version__}')"
# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p logs

# Make startup script executable
RUN chmod +x start.sh

# Expose port (Cloud Run uses PORT env variable, default to 8000)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run application (use startup script for Cloud Run compatibility)
CMD ["./start.sh"]
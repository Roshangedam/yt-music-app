# ============================================================================
# FILE: Dockerfile (Simple - All-in-One)
# Includes Playwright for browser automation in Cloud/Docker
# ============================================================================
FROM python:3.11-slim

# Install system dependencies including Playwright requirements
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    # Playwright dependencies for Chromium
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
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

# Install Playwright browsers (chromium only - smaller size)
RUN playwright install chromium --with-deps || echo "Playwright browser install skipped"

# Verify versions
RUN python -c "import yt_dlp; print(f'yt-dlp version: {yt_dlp.version.__version__}')"
RUN python -c "try:\n    from playwright.sync_api import sync_playwright\n    print('Playwright installed successfully')\nexcept ImportError:\n    print('Playwright not available - will use HTTP fallback')"

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p logs

# Make startup script executable
RUN chmod +x start.sh

# Environment variables for Playwright in container
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0

# Expose port (Cloud Run uses PORT env variable, default to 8000)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run application (use startup script for Cloud Run compatibility)
CMD ["./start.sh"]
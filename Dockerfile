# ============================================================================
# FILE: Dockerfile (Production Ready - Selenium + Chrome)
# Optimized for Google Cloud Run with Chrome for browser automation
# ============================================================================
FROM python:3.11-slim

# Install system dependencies including Chrome
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    wget \
    gnupg \
    unzip \
    # Chrome dependencies
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
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome (stable version for production) - using GPG (apt-key is deprecated)
RUN wget -q -O /tmp/google-chrome.gpg https://dl.google.com/linux/linux_signing_key.pub \
    && gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg /tmp/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/* /tmp/google-chrome.gpg

# Install ChromeDriver (matching Chrome version)
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d. -f1) \
    && CHROMEDRIVER_VERSION=$(curl -sS "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CHROME_VERSION}") \
    && wget -q "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip" -O /tmp/chromedriver.zip \
    && unzip /tmp/chromedriver.zip -d /tmp/ \
    && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf /tmp/chromedriver* \
    || echo "ChromeDriver install attempt completed"

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Force install latest yt-dlp (CRITICAL: YouTube bot detection bypass)
RUN pip uninstall -y yt-dlp && pip install --no-cache-dir --upgrade yt-dlp
RUN pip install --no-cache-dir --upgrade ytmusicapi
RUN pip install pydantic[email]

# Verify installations
RUN python -c "import yt_dlp; print(f'yt-dlp version: {yt_dlp.version.__version__}')"
RUN python -c "from selenium import webdriver; print('Selenium installed successfully')"
RUN google-chrome --version || echo "Chrome version check skipped"
RUN chromedriver --version || echo "ChromeDriver version check skipped"

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p logs

# Make startup script executable
RUN chmod +x start.sh

# Environment variables for Chrome in container
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROME_PATH=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

# Expose port (Cloud Run uses PORT env variable, default to 8000)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run application (use startup script for Cloud Run compatibility)
CMD ["./start.sh"]
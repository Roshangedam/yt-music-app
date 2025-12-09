#!/bin/bash
# Startup script for Cloud Run compatibility

# Use PORT environment variable if set (Cloud Run), otherwise default to 8000
PORT=${PORT:-8000}

echo "Starting YouTube Music Streaming API on port $PORT"

# Run uvicorn with the configured port
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT


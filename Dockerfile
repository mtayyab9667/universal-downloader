# Universal Video Downloader - Production Container
FROM python:3.11-slim

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency requirements
COPY requirements.txt requirements.txt
COPY backend/requirements.txt backend_requirements.txt

# Install python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r backend_requirements.txt

# Copy project files
COPY downloader/ /app/downloader/
COPY backend/ /app/backend/

# Set working directory to backend
WORKDIR /app/backend

# Create cache directory
RUN mkdir -p /app/backend/cache && chmod 777 /app/backend/cache

# Hugging Face Spaces uses port 7860 by default (Render uses $PORT or 8000)
ENV PORT=7860
EXPOSE 7860

# Run FastAPI with Uvicorn
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-7860}"]

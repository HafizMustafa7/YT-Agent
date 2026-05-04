FROM python:3.11-slim

# Install system dependencies (FFmpeg restored — required for stitching segments and probing durations)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsm6 \
    libxext6 \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# DEVOPS-1: create a non-root user so the container doesn't run as root
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and hand ownership to the non-root user
COPY . .
RUN chown -R appuser:appgroup /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Switch to non-root user before running the app
USER appuser

# Expose the API port
EXPOSE 8000

# Start the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

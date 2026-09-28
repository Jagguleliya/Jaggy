FROM python:3.11-slim

# Install system dependencies (FFmpeg, git, build essentials)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose server port
EXPOSE 8000

# Command to launch web app server
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Discord voice & audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg build-essential libffi-dev libsodium-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files to container
COPY . .

# Launch application using Render's dynamic PORT
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
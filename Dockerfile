# --- Stage 1: Build Next.js Dashboard ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/viper-audio-core

# Copy package definitions and install dependencies
COPY viper-audio-core/package*.json ./
COPY viper-audio-core/pnpm-lock.yaml* ./
RUN npm install

# Copy frontend source code and compile static build (/out)
COPY viper-audio-core/ ./
RUN npm run build

# --- Stage 2: Python Runtime with Audio Support ---
FROM python:3.11-slim

# Install FFmpeg (required for voice playback) and C build tools for PyNaCl
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    libffi-dev \
    libsodium-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy compiled Next.js static files from Stage 1
COPY --from=frontend-builder /app/viper-audio-core/out ./viper-audio-core/out

# Copy Discord bot source code
COPY bot.py commands.py embeds.py ./

# Set default port for Render web services
ENV PORT=3000
EXPOSE 3000

# Launch combined FastAPI web dashboard and Discord bot
CMD ["python", "bot.py"]
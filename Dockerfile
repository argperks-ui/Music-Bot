# --- Stage 1: Build Next.js Dashboard ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/Git-Music-Dashboard

# Copy package definitions and install dependencies
COPY Git-Music-Dashboard/package*.json ./
COPY Git-Music-Dashboard/pnpm-lock.yaml* ./
RUN npm install

# Copy frontend source code and compile static build (/out)
COPY Git-Music-Dashboard/ ./
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
COPY --from=frontend-builder /app/Git-Music-Dashboard/out ./Git-Music-Dashboard/out

# Copy Discord bot source code
COPY bot.py commands.py embeds.py ./

# Set default port for Render web services
ENV PORT=3000
EXPOSE 3000

# Launch combined FastAPI web dashboard and Discord bot
CMD ["python", "bot.py"]
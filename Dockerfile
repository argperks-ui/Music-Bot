# Stage 1: Build Next.js Dashboard static export
FROM node:20-alpine AS frontend-builder
WORKDIR /app/Git-Music-Dashboard

COPY Git-Music-Dashboard/package*.json ./
COPY Git-Music-Dashboard/pnpm-lock.yaml* ./
COPY Git-Music-Dashboard/yarn.lock* ./
RUN npm install

COPY Git-Music-Dashboard/ ./
RUN npm run build

# Stage 2: Python Runtime & Bot Server
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg build-essential libffi-dev libsodium-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 1. Copy repository source code FIRST
COPY . .

# 2. Copy compiled static frontend AFTER so COPY . . cannot overwrite it
COPY --from=frontend-builder /app/Git-Music-Dashboard/out ./Git-Music-Dashboard/out

ENV PORT=3000
EXPOSE 3000

CMD ["python", "bot.py"]
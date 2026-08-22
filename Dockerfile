# Frontend Builder Stage
FROM node:18 AS frontend-builder
WORKDIR /app/music-bot

COPY "music bot/package*.json" ./
COPY "music bot/pnpm-lock.yaml*" ./
COPY "music bot/yarn.lock*" ./
RUN npm install

COPY "music bot/" ./
RUN npm run build

# Backend Stage
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg build-essential libffi-dev libsodium-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend-builder /app/music-bot/dist ./dist

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
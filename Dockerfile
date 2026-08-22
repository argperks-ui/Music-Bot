# Frontend Builder Stage
FROM node:18 AS frontend-builder
WORKDIR /app

COPY package*.json pnpm-lock.yaml* yarn.lock* ./
RUN npm install

COPY . .
RUN npm run build

# Python Backend Stage
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg build-essential libffi-dev libsodium-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
FROM node:18-slim

# Install system dependencies for FFmpeg, Opus codec, and Python runtime
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    libopus0 \
    libopus-dev \
    libffi-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Node.js dashboard dependencies
COPY package*.json ./
RUN npm install --production

# Copy and install Python bot dependencies
COPY requirements.txt ./
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy project files
COPY . .

# Grant execution permissions to launch script
RUN chmod +x start.sh

EXPOSE 3000

CMD ["./start.sh"]
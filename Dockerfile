FROM python:3.11-slim

# Install system dependencies, Git, FFmpeg, and Node.js
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files first to leverage caching
COPY requirements.txt package.json ./

# Install Python and Node dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN npm install

# Copy the rest of your project files
COPY . .

# Grant execution permission to the start script
RUN chmod +x start.sh

# Run the startup script
CMD ["./start.sh"]
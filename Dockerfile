FROM python:3.11-slim AS base
WORKDIR /app

# Install Node.js for building frontend
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY package*.json ./

# Build frontend
RUN npm ci && npm run build

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Expose port
EXPOSE 8000

# Run: Python starts first, then serves dist/
CMD ["python", "-c", "import subprocess; subprocess.run(['npm', 'run', 'build']); import uvicorn; uvicorn.run('main:app', host='0.0.0.0', port=8000)"]

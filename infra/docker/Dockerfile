FROM python:3.11-slim

# Set proxy for build
ENV http_proxy=http://10.157.59.75:7890
ENV https_proxy=http://10.157.59.75:7890
ENV HTTP_PROXY=http://10.157.59.75:7890
ENV HTTPS_PROXY=http://10.157.59.75:7890

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /var/lib/tokenmachine/models /var/log/tokenmachine

# Expose ports
EXPOSE 8000 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

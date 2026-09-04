# Production Dockerfile for Midgley Self-Hosted Container
FROM python:3.11-slim

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependencies manifest & install
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copy application source
COPY . .

# Default environment configuration: Blank-slate National Wholesale RBOB
ENV MIDGLEY_ENABLED_REGIONS="national"

# Expose API Gateway port
EXPOSE 8000

CMD ["uvicorn", "src.api_server:app", "--host", "0.0.0.0", "--port", "8000"]

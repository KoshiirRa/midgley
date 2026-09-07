# Production Dockerfile for Midgley Self-Hosted Container
FROM python:3.12-slim

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy official static uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create virtual environment and add to PATH
ENV VIRTUAL_ENV=/opt/venv
RUN uv venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy dependencies manifest & install into virtual environment
COPY requirements.txt .
RUN uv pip install --no-cache -r requirements.txt

# Copy application source
COPY . .

# Default environment configuration: Blank-slate National Wholesale RBOB
ENV MIDGLEY_ENABLED_REGIONS="national"

# Expose API Gateway port
EXPOSE 8000

CMD ["uvicorn", "src.api_server:app", "--host", "0.0.0.0", "--port", "8000"]

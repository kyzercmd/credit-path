# Multi-stage Dockerfile for CreditPath FastAPI Backend
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:0.5.26 /uv /uvx /bin/

# Copy dependencies definitions
COPY pyproject.toml uv.lock* ./

# Install python dependencies into a virtual environment
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache -r pyproject.toml fastparquet sqlalchemy psycopg2-binary "scikit-learn==1.6.1"

# Production runtime stage
FROM python:3.12-slim AS runner

WORKDIR /app

# Install libpq and libgomp runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv and app files
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app"
COPY . /app

# Ensure trained models exist for the application lifespan startup
RUN python -m app.ml.train

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

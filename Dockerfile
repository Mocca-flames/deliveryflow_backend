# DeliveryFlow Backend — Simplified Dockerfile

FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual env
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e "." || pip install --no-cache-dir .

# Copy application code
COPY app/ ./app/
COPY alembic.ini .

# Create non-root user
RUN groupadd -r dfuser && useradd -r -g dfuser dfuser && \
    chown -R dfuser:dfuser /app
USER dfuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

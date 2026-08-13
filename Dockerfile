# DeliveryFlow Backend — Dockerfile with WeasyPrint support

FROM python:3.12-slim

WORKDIR /app

# Install system deps (including WeasyPrint dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libcairo2 \
    libglib2.0-0 \
    libpangoft2-1.0-0 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create virtual env
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e "." || pip install --no-cache-dir .

# Copy application code
COPY app/ ./app/
COPY tests/ ./tests/
COPY alembic.ini .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Create non-root user
RUN groupadd -r dfuser && useradd -r -g dfuser dfuser && \
    chown -R dfuser:dfuser /app
USER dfuser

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]

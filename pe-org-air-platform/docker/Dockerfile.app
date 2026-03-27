
# ----------------------------------------------------------------------
# DOCKERFILE FOR API + MCP-SERVER SERVICES
# ----------------------------------------------------------------------
# Uses the same Airflow base image for user/permission parity,
# but installs requirements-app.txt which includes mem0ai (sqlalchemy>=2.0).
# Airflow's own CLI will be broken here — that is expected and fine,
# since these containers run uvicorn / python, never the airflow command.
FROM apache/airflow:2.8.1-python3.11

USER root

# System Dependencies (same as main Dockerfile)
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libxshmfence1 \
    fonts-liberation \
    fonts-unifont \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

USER root

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/bin/uv

# Install app-specific Python dependencies (sqlalchemy>=2.0 + mem0ai)
COPY requirements-app.txt /requirements.txt
RUN uv pip install --no-cache --system -r /requirements.txt && \
    rm -rf /home/airflow/.local && \
    mkdir -p /home/airflow/.local && \
    chown -R airflow:root /home/airflow/.local

# Install Playwright browsers
ENV PLAYWRIGHT_BROWSERS_PATH=/home/airflow/.cache/ms-playwright
RUN playwright install chromium && \
    chown -R airflow:root /home/airflow/.cache/ms-playwright

USER airflow

# Copy Application Code
COPY --chown=airflow:root app /opt/airflow/app
COPY --chown=airflow:root app /app
COPY --chown=airflow:root dags /opt/airflow/dags

ENV PYTHONPATH="${PYTHONPATH}:/opt/airflow:/app"
# Use pure-Python protobuf to avoid C-extension descriptor errors with chromadb
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

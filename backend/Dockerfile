FROM python:3.11-slim

# Arguments to match host user
ARG UID=1000
ARG GID=1000

# Install system deps (Git is needed for some repo operations)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -g "${GID}" appuser && \
    useradd -m -u "${UID}" -g "${GID}" -s /bin/bash appuser

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change ownership
RUN chown -R appuser:appuser /app

USER appuser

# Expose FastAPI port
EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
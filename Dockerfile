# Dockerfile for AI DevOps Incident Intelligence
# Uses a small Python base image, non-root user, and gunicorn for production.

FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

# Create a non-root user.
RUN groupadd --system appuser && \
    useradd --system --gid appuser --create-home --home-dir /home/appuser appuser

# Set working directory.
WORKDIR /app

# Copy only requirements first for better layer caching.
COPY requirements.txt .

# Install dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY app.py ollama_client.py retrieval.py ./
COPY templates/ ./templates/
COPY static/ ./static/
COPY runbooks/ ./runbooks/

# Switch to non-root user.
USER appuser

# Expose the configurable port.
EXPOSE 5000

# Use gunicorn for production serving.
# Use a single worker because the app stores incidents in process-local memory.
# Multiple workers would each have their own independent copy of the incidents
# list, causing "incident not found" errors when a request lands on a different
# worker than the one that created the incident.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 1 --timeout 60 app:app"]

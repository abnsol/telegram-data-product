FROM python:3.9-slim-buster

# Create a non-root user and set permissions
ARG UID=1000
RUN adduser --disabled-password --gecos '' --uid ${UID} appuser \
    && chown -R appuser:appuser /app /home/appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Change ownership of the copied files to appuser
COPY . .
RUN chown -R appuser:appuser /app

# Set the default user for subsequent commands
USER appuser

# ... rest of your Dockerfile (no changes needed below) ...
FROM python:3.9-slim-buster

# Create a non-root user and set permissions
ARG UID=1000
RUN adduser --disabled-password --gecos '' --uid ${UID} appuser \
    && chown -R appuser:appuser /app /home/appuser

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
RUN mkdir -p data/raw_telegram_data data/preprocessed_data
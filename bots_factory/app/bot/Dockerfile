FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app

COPY app/bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
#!/bin/sh

# Останавливаем выполнение при любой ошибке
set -e

# Применяем миграции Alembic
echo "Applying database migrations..."
alembic upgrade head

# Запускаем основной процесс (команду, переданную в docker-compose, то есть uvicorn)
echo "Starting Uvicorn server..."
exec uvicorn app.web.main:app --host 0.0.0.0 --port 8000
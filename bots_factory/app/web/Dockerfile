# Dockerfile.api (поместите этот файл в корень BOTS_FACTORY, то есть в C:\bots_factory\Dockerfile.api)

FROM python:3.11-slim

# Устанавливаем рабочую директорию в корне контейнера
WORKDIR /app

# Копируем всю папку 'app' из корневого контекста в '/app/app' внутри контейнера
# Это скопирует C:\bots_factory\app в /app/app
# Таким образом, C:\bots_factory\app\web будет доступна по /app/app/web
# и C:\bots_factory\app\bot будет доступна по /app/app/bot
COPY app /app/app

# Копируем всю папку 'frontend' из корневого контекста в '/app/frontend' внутри контейнера
# Это скопирует C:\bots_factory\frontend в /app/frontend
COPY frontend /app/frontend

# Копируем файл entrypoint.sh (если он есть и используется для API)
# Путь внутри контейнера: /app/entrypoint.sh
# Путь на хосте: C:\bots_factory\app\web\entrypoint.sh
COPY app/web/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Копируем requirements.txt для API-сервиса непосредственно в /app/app/web
# Это устраняет необходимость менять WORKDIR туда-сюда для этого шага.
COPY app/web/requirements.txt /app/app/web/requirements.txt

# Переходим в директорию API-сервиса, чтобы pip мог найти requirements.txt
WORKDIR /app/app/web 

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Возвращаемся в корень '/app' для запуска приложения Uvicorn
WORKDIR /app

# Команда для запуска Uvicorn сервера
CMD ["uvicorn", "app.web.main:app", "--host", "0.0.0.0", "--port", "8000"]
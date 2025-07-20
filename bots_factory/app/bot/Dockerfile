# bots_factory/app/bot/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY app/bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire 'app' directory into the container
COPY app /app/app

# Set the command to run the main script as a module
CMD ["python", "-m", "app.bot.main"]
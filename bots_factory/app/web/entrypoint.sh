#!/bin/bash

# Wait for the database to be ready
# (you might need a more robust solution for production)
sleep 5

# Apply database migrations
echo "Applying database migrations... (SKIPPED FOR DIRECT SYNC)"
# alembic upgrade head # <-- ИЗМЕНЕНО (закомментировано)

# Start Uvicorn server
echo "Starting Uvicorn server..."
uvicorn app.web.main:app --host 0.0.0.0 --port 8000 --reload
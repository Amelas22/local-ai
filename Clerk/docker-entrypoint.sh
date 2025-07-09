#!/bin/bash
set -e

echo "Waiting for database to be ready..."
while ! nc -z ${DATABASE_HOST:-localai-postgres-1} ${DATABASE_PORT:-5432}; do
  echo "Waiting for database at ${DATABASE_HOST:-localai-postgres-1}:${DATABASE_PORT:-5432}..."
  sleep 1
done
echo "Database is ready!"

# Run database initialization
echo "Initializing database..."
python init_db.py

# Start the application
echo "Starting Clerk application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
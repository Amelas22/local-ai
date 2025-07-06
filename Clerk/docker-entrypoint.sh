#!/bin/bash
set -e

echo "Waiting for database to be ready..."
while ! nc -z ${DATABASE_HOST:-postgres} ${DATABASE_PORT:-5432}; do
  sleep 1
done
echo "Database is ready!"

# Run database initialization
echo "Initializing database..."
python init_db.py

# Fix dev data if in development mode
if [ "$AUTH_ENABLED" = "false" ]; then
  echo "Ensuring development data exists..."
  python scripts/fix_dev_database.py
fi

# Start the application
echo "Starting Clerk application..."
exec python main.py
#!/bin/bash
# Check database configuration inside Docker container

echo "=== Checking Database Inside Docker ==="
echo ""

# Check environment inside clerk container
echo "1. Environment variables in Clerk container:"
docker exec clerk sh -c 'echo "DATABASE_URL: $DATABASE_URL"'

echo ""
echo "2. Testing connection from Clerk to Postgres:"
docker exec clerk sh -c 'nc -zv postgres 5432 2>&1'

echo ""
echo "3. Checking /app/.env file in Clerk:"
docker exec clerk sh -c 'grep DATABASE_URL /app/.env 2>/dev/null || echo "No .env file found"'

echo ""
echo "4. Python settings check:"
docker exec clerk python -c "
from config.settings import settings
print(f'Database URL from settings: {settings.database.url}')
print(f'Host: {settings.database.url.split(\"@\")[1].split(\":\")[0]}')
print(f'Port: {settings.database.url.split(\":\")[-1].split(\"/\")[0]}')
" 2>&1

echo ""
echo "5. Direct PostgreSQL connection test:"
docker exec clerk python -c "
import psycopg2
from urllib.parse import urlparse
import os

url = os.getenv('DATABASE_URL', '')
if not url:
    from config.settings import settings
    url = settings.database.url

print(f'Using URL: {url}')
parsed = urlparse(url)

try:
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port,
        database=parsed.path.lstrip('/'),
        user=parsed.username,
        password=parsed.password
    )
    print('✓ Successfully connected to PostgreSQL!')
    conn.close()
except Exception as e:
    print(f'✗ Connection failed: {e}')
" 2>&1

echo ""
echo "=== Recommendations ==="
echo "If connection fails with 'localhost' or '127.0.0.1', the .env file needs updating."
echo "Run: python fix_database_url.py"
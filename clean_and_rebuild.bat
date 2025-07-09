@echo off
echo Cleaning Docker build cache and rebuilding...

echo Stopping containers...
docker compose -p localai --profile cpu -f docker-compose.yml -f docker-compose.clerk.yml down

echo Cleaning Docker build cache...
docker builder prune -af

echo Removing dangling images...
docker image prune -f

echo Rebuilding services...
docker compose -p localai --profile cpu -f docker-compose.yml -f docker-compose.clerk.yml -f docker-compose.override.private.yml build --no-cache

echo Starting services...
docker compose -p localai --profile cpu -f docker-compose.yml -f docker-compose.clerk.yml -f docker-compose.override.private.yml up -d

echo Done! Check 'docker ps' to see running containers.
pause
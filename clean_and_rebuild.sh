#!/bin/bash

echo "Cleaning Docker build cache and rebuilding..."

# Stop all containers
echo "Stopping containers..."
docker compose -p localai --profile cpu -f docker-compose.yml -f docker-compose.clerk.yml down || true

# Clean Docker build cache
echo "Cleaning Docker build cache..."
docker builder prune -af

# Remove any dangling images
echo "Removing dangling images..."
docker image prune -f

# Clean up volumes if needed (optional - uncomment if you want to clean volumes too)
# docker volume prune -f

# Rebuild with no cache
echo "Rebuilding services..."
docker compose -p localai --profile cpu -f docker-compose.yml -f docker-compose.clerk.yml -f docker-compose.override.private.yml build --no-cache

# Start services
echo "Starting services..."
docker compose -p localai --profile cpu -f docker-compose.yml -f docker-compose.clerk.yml -f docker-compose.override.private.yml up -d

echo "Done! Check 'docker ps' to see running containers."
#!/bin/bash

# Run tests inside Docker containers to verify internal connectivity

echo "Starting test environment..."

# Ensure we're in the Clerk directory
cd "$(dirname "$0")"

# Build the test container
echo "Building test container..."
docker-compose -f docker-compose.test.yml build clerk-test

# Start required services
echo "Starting Qdrant and PostgreSQL..."
docker-compose -f docker-compose.test.yml up -d qdrant postgres

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Run container connectivity tests
echo "Running container connectivity tests..."
docker-compose -f docker-compose.test.yml run --rm clerk-test

# Run all tests if requested
if [ "$1" == "--all" ]; then
    echo "Running all tests in container..."
    docker-compose -f docker-compose.test.yml run --rm clerk-test python -m pytest -v
fi

# Cleanup if requested
if [ "$1" == "--cleanup" ] || [ "$2" == "--cleanup" ]; then
    echo "Cleaning up test environment..."
    docker-compose -f docker-compose.test.yml down -v
fi

echo "Tests completed!"
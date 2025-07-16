FROM qdrant/qdrant:latest

# Install curl for healthchecks
RUN apt-get update && \
    apt-get install -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
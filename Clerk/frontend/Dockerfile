# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Force cache invalidation
ARG CACHE_BUST=1

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Ensure PDF.js worker is available (the Vite plugin will copy it during build)
# As a fallback, download it if node_modules doesn't have it
RUN if [ ! -f "node_modules/pdfjs-dist/build/pdf.worker.min.js" ]; then \
      wget -O public/pdf.worker.min.js https://unpkg.com/pdfjs-dist@3.4.120/build/pdf.worker.min.js || \
      echo "console.warn('Failed to download PDF.js worker')" > public/pdf.worker.min.js; \
    fi

# Accept build arguments for environment variables
ARG VITE_API_URL
ARG VITE_WS_URL
ARG VITE_AUTH_ENABLED=false
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY

# Set environment variables for the build
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL
ENV VITE_AUTH_ENABLED=$VITE_AUTH_ENABLED
ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL
ENV VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY

# Build the application
RUN npm run build

# The builder stage is used directly by docker-compose
# The built files will be in /app/dist
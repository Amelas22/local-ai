#!/usr/bin/env python3
"""
Development startup script for Local AI Package
Starts services with hot reloading and development configurations
"""

import subprocess
import time
import sys
import os
from pathlib import Path

def run_command(command, check=True):
    """Run a shell command and print output."""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=False, text=True, check=check)
    return result

def check_docker():
    """Check if Docker is running."""
    result = run_command("docker info", check=False)
    if result.returncode != 0:
        print("Error: Docker is not running. Please start Docker Desktop.")
        sys.exit(1)

def main():
    print("Starting Local AI Package services in DEVELOPMENT mode...")
    print("=" * 60)
    
    # Check Docker
    check_docker()
    
    # Set project name
    project_name = "localai"
    
    # Phase 1: Start Supabase services
    print("\nPhase 1: Starting Supabase services...")
    print("-" * 40)
    
    supabase_compose = Path("supabase/docker/docker-compose.yml")
    if not supabase_compose.exists():
        print(f"Error: {supabase_compose} not found!")
        sys.exit(1)
    
    # Start Supabase
    run_command(f"docker-compose -p {project_name} -f {supabase_compose} up -d")
    
    print("\nWaiting for Supabase to initialize (15 seconds)...")
    time.sleep(15)
    
    # Phase 2: Start local AI services with development overrides
    print("\nPhase 2: Starting AI services with hot reloading...")
    print("-" * 40)
    
    # Build command with all compose files
    compose_files = [
        "docker-compose.yml",
        "docker-compose.clerk.yml",
        "docker-compose.dev.yml"
    ]
    
    # Check if files exist
    for file in compose_files:
        if not Path(file).exists():
            print(f"Error: {file} not found!")
            sys.exit(1)
    
    # Build docker-compose command
    compose_cmd = f"docker-compose -p {project_name}"
    for file in compose_files:
        compose_cmd += f" -f {file}"
    
    # Start services
    run_command(f"{compose_cmd} up -d")
    
    print("\n" + "=" * 60)
    print("All services started in DEVELOPMENT mode!")
    print("\nService URLs:")
    print("  - Frontend (Vite):     http://localhost:3000")
    print("  - Frontend (Caddy):    http://localhost:8010")
    print("  - Clerk API:           http://localhost:8010/api")
    print("  - Supabase Studio:     http://localhost:54323")
    print("  - n8n:                 http://localhost:5678")
    print("  - Qdrant Dashboard:    http://localhost:6333/dashboard")
    
    print("\nDevelopment features enabled:")
    print("  ✓ Hot reloading for Clerk backend")
    print("  ✓ Vite HMR for frontend")
    print("  ✓ Source code mounted as volumes")
    print("  ✓ Debug logging enabled")
    
    print("\nUseful commands:")
    print(f"  - View logs:     docker-compose -p {project_name} logs -f clerk clerk-frontend")
    print(f"  - Stop services: docker-compose -p {project_name} down")
    print(f"  - Restart clerk: docker-compose -p {project_name} restart clerk")
    
    print("\nOptional debug tools (start with --profile debug):")
    print("  - pgAdmin:         http://localhost:5050")
    print("  - Redis Commander: http://localhost:8081")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Fix PostgreSQL port conflicts and restart services properly.
"""

import subprocess
import sys
import time

def run_command(cmd, check=True):
    """Run a shell command and return result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    return True

def stop_all_services():
    """Stop all localai services."""
    print("Stopping all localai services...")
    commands = [
        ["docker", "compose", "-p", "localai", "down"],
        ["docker", "stop", "localai-postgres-1"],
        ["docker", "rm", "localai-postgres-1"],
    ]
    
    for cmd in commands:
        run_command(cmd, check=False)

def check_port_free():
    """Check if port 5432 is free."""
    try:
        result = subprocess.run(
            ["netstat", "-ano", "|", "findstr", ":5432"],
            shell=True,
            capture_output=True,
            text=True
        )
        return len(result.stdout.strip()) == 0
    except:
        return True

def use_alternative_port():
    """Configure to use alternative port 5433."""
    print("\nConfiguring PostgreSQL to use port 5433 instead of 5432...")
    
    # Update docker-compose.override.yml
    override_content = """# Docker Compose override for local development
# Using port 5433 to avoid conflicts

version: '3.8'

services:
  postgres:
    ports:
      - "5433:5432"  # Use port 5433 on host to avoid conflicts
"""
    
    with open("docker-compose.override.yml", "w") as f:
        f.write(override_content)
    
    print("Updated docker-compose.override.yml to use port 5433")
    print("\nIMPORTANT: Update your .env file:")
    print("DATABASE_URL=$redacted")
    print("\nNote the port change from 5432 to 5433 in the DATABASE_URL")

def main():
    print("Fixing PostgreSQL port conflicts...")
    
    # Step 1: Stop everything
    stop_all_services()
    time.sleep(2)
    
    # Step 2: Check if port is free
    if check_port_free():
        print("\nPort 5432 is now free. You can start services normally:")
        print("python start_services_with_postgres.py --profile cpu")
    else:
        print("\nPort 5432 is still in use (probably by local PostgreSQL).")
        response = input("Would you like to use port 5433 instead? (y/n): ")
        
        if response.lower() == 'y':
            use_alternative_port()
            print("\nNow you can start services with:")
            print("python start_services_with_postgres.py --profile cpu")
            print("\nThen initialize the database:")
            print("python init_clerk_db.py")
        else:
            print("\nTo manually fix:")
            print("1. Stop local PostgreSQL service")
            print("2. Or edit docker-compose files to use a different port")

if __name__ == "__main__":
    main()
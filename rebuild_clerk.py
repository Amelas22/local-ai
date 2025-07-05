#!/usr/bin/env python3
"""
Rebuild Clerk service to pick up new environment variables.
"""

import subprocess
import sys

def run_command(cmd):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout

def main():
    print("Rebuilding Clerk service with new environment variables...")
    
    # Stop Clerk service
    print("\n1. Stopping Clerk service...")
    run_command([
        "docker", "compose", "-p", "localai",
        "-f", "docker-compose.yml",
        "-f", "docker-compose.clerk.yml",
        "-f", "docker-compose.clerk-jwt.yml",
        "stop", "clerk"
    ])
    
    # Remove Clerk container to force recreation with new env
    print("\n2. Removing Clerk container...")
    run_command([
        "docker", "compose", "-p", "localai",
        "-f", "docker-compose.yml",
        "-f", "docker-compose.clerk.yml",
        "-f", "docker-compose.clerk-jwt.yml",
        "rm", "-f", "clerk"
    ])
    
    # Rebuild and start Clerk service
    print("\n3. Rebuilding and starting Clerk service...")
    run_command([
        "docker", "compose", "-p", "localai",
        "-f", "docker-compose.yml",
        "-f", "docker-compose.clerk.yml",
        "-f", "docker-compose.clerk-jwt.yml",
        "up", "-d", "--build", "clerk"
    ])
    
    print("\nClerk service rebuilt successfully!")
    print("The service will pick up the new environment variables from .env")
    print("\nYou can now run: python init_clerk_db.py")

if __name__ == "__main__":
    main()
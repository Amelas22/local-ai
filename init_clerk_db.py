#!/usr/bin/env python3
"""
Initialize Clerk database after services are started.

This script waits for PostgreSQL to be ready and then initializes
the Clerk database with JWT authentication tables.
"""

import subprocess
import time
import sys
import os

def check_postgres_ready():
    """Check if PostgreSQL is ready to accept connections."""
    try:
        # Try using docker exec to check PostgreSQL
        result = subprocess.run(
            ["docker", "exec", "localai-postgres-1", "pg_isready", "-U", "postgres"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except:
        # If docker exec fails, try direct connection
        try:
            import psycopg2
            conn_string = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/postgres")
            conn = psycopg2.connect(conn_string)
            conn.close()
            return True
        except:
            return False

def main():
    print("Checking PostgreSQL availability...")
    
    # Wait for PostgreSQL to be ready
    max_attempts = 30
    for i in range(max_attempts):
        if check_postgres_ready():
            print("PostgreSQL is ready!")
            break
        print(f"Waiting for PostgreSQL... ({i+1}/{max_attempts})")
        time.sleep(2)
    else:
        print("ERROR: PostgreSQL is not available after waiting.")
        print("\nPlease ensure:")
        print("1. Services are started with: python start_services.py")
        print("2. PostgreSQL is exposed on port 5432")
        print("3. DATABASE_URL in .env is correct")
        sys.exit(1)
    
    # Change to Clerk directory and run init_db.py
    print("\nInitializing Clerk database...")
    os.chdir("Clerk")
    
    try:
        subprocess.run([sys.executable, "init_db.py"], check=True)
        print("\nClerk database initialized successfully!")
        print("\nYou can now access Clerk at: http://localhost:3001")
        print("Default admin credentials are shown above.")
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
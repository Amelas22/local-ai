#!/usr/bin/env python3
"""
Check what's using port 5432 and help resolve conflicts.
"""

import subprocess
import sys
import platform

def check_port_windows():
    """Check port 5432 on Windows."""
    print("Checking what's using port 5432 on Windows...")
    try:
        # Use netstat to find what's using port 5432
        result = subprocess.run(
            ["netstat", "-ano", "|", "findstr", ":5432"],
            shell=True,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print("Port 5432 is in use:")
            print(result.stdout)
            
            # Try to get process names
            lines = result.stdout.strip().split('\n')
            pids = set()
            for line in lines:
                parts = line.split()
                if len(parts) > 4:
                    pid = parts[-1]
                    if pid.isdigit():
                        pids.add(pid)
            
            print("\nProcesses using port 5432:")
            for pid in pids:
                try:
                    proc_result = subprocess.run(
                        ["tasklist", "/FI", f"PID eq {pid}"],
                        capture_output=True,
                        text=True
                    )
                    print(proc_result.stdout)
                except:
                    pass
        else:
            print("Port 5432 appears to be free")
    except Exception as e:
        print(f"Error checking port: {e}")

def check_docker_postgres():
    """Check if PostgreSQL is running in Docker."""
    print("\nChecking Docker containers...")
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "publish=5432"],
            capture_output=True,
            text=True
        )
        if result.stdout:
            print("Docker containers exposing port 5432:")
            print(result.stdout)
            
            # Also check localai-postgres-1 specifically
            result2 = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=postgres"],
                capture_output=True,
                text=True
            )
            if result2.stdout:
                print("\nAll PostgreSQL containers:")
                print(result2.stdout)
    except Exception as e:
        print(f"Error checking Docker: {e}")

def suggest_solutions():
    """Suggest solutions based on findings."""
    print("\n" + "="*50)
    print("SOLUTIONS:")
    print("="*50)
    print("\n1. If PostgreSQL is running in Docker from a previous session:")
    print("   docker stop localai-postgres-1")
    print("   docker rm localai-postgres-1")
    print("\n2. If you have PostgreSQL installed locally on Windows:")
    print("   - Stop the PostgreSQL service: net stop postgresql-x64-15")
    print("   - Or change the port mapping in docker-compose.override.yml:")
    print('     Change: "5432:5432" to "5433:5432"')
    print('     Then update DATABASE_URL to use port 5433')
    print("\n3. Use a different port for Docker PostgreSQL:")
    print("   Edit docker-compose.override.yml and docker-compose.postgres-expose.yml:")
    print('   Change: "${POSTGRES_PORT:-5432}:5432"')
    print('   To:     "${POSTGRES_PORT:-5433}:5432"')
    print("\n4. Or set POSTGRES_PORT in your .env file:")
    print("   POSTGRES_PORT=5433")
    print('   DATABASE_URL=postgresql://postgres:your_password@localhost:5433/postgres')

def main():
    if platform.system() == "Windows":
        check_port_windows()
    check_docker_postgres()
    suggest_solutions()

if __name__ == "__main__":
    main()
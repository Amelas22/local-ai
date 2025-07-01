#!/usr/bin/env python3
"""
stop_services.py

This script stops all services in the local AI stack including Supabase and Clerk.
"""

import subprocess
import argparse

def run_command(cmd, cwd=None):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def stop_all_services(profile=None):
    """Stop all services in the unified localai project."""
    print("Stopping all services in the localai stack...")
    
    # Stop local AI services (including Clerk)
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml", "-f", "docker-compose.clerk.yml", "down"])
    
    try:
        run_command(cmd)
    except subprocess.CalledProcessError:
        print("Error stopping local AI services, continuing...")
    
    # Stop Supabase services
    print("Stopping Supabase services...")
    supabase_cmd = ["docker", "compose", "-p", "localai", "-f", "supabase/docker/docker-compose.yml", "down"]
    
    try:
        run_command(supabase_cmd)
    except subprocess.CalledProcessError:
        print("Error stopping Supabase services, continuing...")
    
    print("\n✅ All services stopped!")

def main():
    parser = argparse.ArgumentParser(description='Stop all local AI services.')
    parser.add_argument('--profile', choices=['cpu', 'gpu-nvidia', 'gpu-amd', 'none'], default='cpu',
                      help='Profile that was used for Docker Compose (default: cpu)')
    args = parser.parse_args()
    
    stop_all_services(args.profile)

if __name__ == "__main__":
    main()
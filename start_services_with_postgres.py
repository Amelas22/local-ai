#!/usr/bin/env python3
"""
start_services_with_postgres.py

Modified version of start_services.py that exposes PostgreSQL for Clerk's JWT authentication.
This script starts the Supabase stack first, waits for it to initialize, and then starts
the local AI stack with PostgreSQL exposed on the host.
"""

import os
import subprocess
import shutil
import time
import argparse
import platform
import sys

def run_command(cmd, cwd=None):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def clone_supabase_repo():
    """Clone the Supabase repository using sparse checkout if not already present."""
    if not os.path.exists("supabase"):
        print("Cloning the Supabase repository...")
        run_command([
            "git", "clone", "--filter=blob:none", "--no-checkout",
            "https://github.com/supabase/supabase.git"
        ])
        os.chdir("supabase")
        run_command(["git", "sparse-checkout", "init", "--cone"])
        run_command(["git", "sparse-checkout", "set", "docker"])
        run_command(["git", "checkout", "master"])
        os.chdir("..")
    else:
        print("Supabase repository already exists, updating...")
        os.chdir("supabase")
        run_command(["git", "pull"])
        os.chdir("..")

def prepare_supabase_env():
    """Copy .env to .env in supabase/docker."""
    env_path = os.path.join("supabase", "docker", ".env")
    env_example_path = os.path.join(".env")
    print("Copying .env in root to .env in supabase/docker...")
    shutil.copyfile(env_example_path, env_path)

def stop_existing_containers(profile=None):
    print("Stopping and removing existing containers for the unified project 'localai'...")
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml", "-f", "docker-compose.clerk.yml", "down"])
    run_command(cmd)

def start_supabase(environment=None, rebuild=False):
    """Start the Supabase services (using its compose file)."""
    print("Starting Supabase services...")
    cmd = ["docker", "compose", "-p", "localai", "-f", "supabase/docker/docker-compose.yml"]
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.supabase.yml"])
    cmd.extend(["up"])
    if rebuild:
        cmd.extend(["--build", "--force-recreate"])
    cmd.append("-d")
    run_command(cmd)

def start_local_ai(profile=None, environment=None, rebuild=False, expose_postgres=True):
    """Start the local AI services (using its compose file)."""
    print("Starting local AI services (including Clerk frontend)...")
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml"])
    
    # Include Clerk frontend compose file
    cmd.extend(["-f", "docker-compose.clerk.yml"])
    
    # Include Clerk JWT configuration
    cmd.extend(["-f", "docker-compose.clerk-jwt.yml"])
    
    # Include PostgreSQL exposure for development
    if expose_postgres:
        print("Including PostgreSQL exposure for Clerk JWT authentication...")
        cmd.extend(["-f", "docker-compose.postgres-expose.yml"])
    
    if environment and environment == "private":
        cmd.extend(["-f", "docker-compose.override.private.yml"])
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.yml"])
    cmd.extend(["up"])
    if rebuild:
        cmd.extend(["--build", "--force-recreate"])
    cmd.append("-d")
    run_command(cmd)

def wait_for_postgres():
    """Wait for PostgreSQL to be ready."""
    print("Waiting for PostgreSQL to be ready...")
    max_attempts = 30
    for i in range(max_attempts):
        try:
            # Try to connect to PostgreSQL
            result = subprocess.run(
                ["docker", "exec", "localai-postgres-1", "pg_isready", "-U", "postgres"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("PostgreSQL is ready!")
                return True
        except subprocess.CalledProcessError:
            pass
        
        print(f"Waiting for PostgreSQL... ({i+1}/{max_attempts})")
        time.sleep(2)
    
    print("Warning: PostgreSQL may not be ready after waiting")
    return False

def init_clerk_database():
    """Initialize the Clerk database if needed."""
    print("\nChecking if Clerk database needs initialization...")
    init_db_path = os.path.join("Clerk", "init_db.py")
    
    if os.path.exists(init_db_path):
        print("Found Clerk database initialization script.")
        response = input("Would you like to initialize the Clerk database now? (y/N): ")
        if response.lower() == 'y':
            print("Initializing Clerk database...")
            os.chdir("Clerk")
            run_command([sys.executable, "init_db.py"])
            os.chdir("..")
            print("Clerk database initialized successfully!")
        else:
            print("Skipping database initialization. You can run it later with:")
            print("  cd Clerk && python init_db.py")
    else:
        print("Clerk database initialization script not found.")

def generate_searxng_secret_key():
    """Generate a secret key for SearXNG based on the current platform."""
    print("Checking SearXNG settings...")
    
    # Define paths for SearXNG settings files
    settings_path = os.path.join("searxng", "settings.yml")
    settings_base_path = os.path.join("searxng", "settings-base.yml")
    
    # Check if settings-base.yml exists
    if not os.path.exists(settings_base_path):
        print(f"Warning: SearXNG base settings file not found at {settings_base_path}")
        return
    
    # Check if settings.yml already exists
    if os.path.exists(settings_path):
        print("SearXNG settings.yml already exists.")
        # Read the existing settings.yml and check if it has a secret_key
        with open(settings_path, 'r') as f:
            content = f.read()
            if 'secret_key:' in content and 'secret_key: ""' not in content:
                print("SearXNG secret key already set.")
                return
    
    # If we're here, we need to generate the settings.yml
    print("Generating SearXNG settings...")
    
    # Generate a secret key
    secret_key_cmd = ["openssl", "rand", "-hex", "32"]
    
    # Check if we're on Windows and openssl is not available
    if platform.system() == "Windows":
        try:
            subprocess.run(["openssl", "version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Generate using Python instead
            import secrets
            secret_key = secrets.token_hex(32)
            print("Generated secret key using Python (OpenSSL not available on Windows)")
            # Copy settings-base.yml to settings.yml
            shutil.copy(settings_base_path, settings_path)
            
            # Replace the secret_key placeholder
            with open(settings_path, 'r') as f:
                content = f.read()
            
            content = content.replace('secret_key: ""', f'secret_key: "{secret_key}"')
            
            with open(settings_path, 'w') as f:
                f.write(content)
            
            print(f"Created SearXNG settings.yml with generated secret key")
            return
    
    # Use openssl if available
    try:
        result = subprocess.run(secret_key_cmd, capture_output=True, text=True, check=True)
        secret_key = result.stdout.strip()
        
        # Copy settings-base.yml to settings.yml
        shutil.copy(settings_base_path, settings_path)
        
        # Replace the secret_key placeholder
        with open(settings_path, 'r') as f:
            content = f.read()
        
        content = content.replace('secret_key: ""', f'secret_key: "{secret_key}"')
        
        with open(settings_path, 'w') as f:
            f.write(content)
        
        print(f"Created SearXNG settings.yml with generated secret key")
    except subprocess.CalledProcessError as e:
        print(f"Error generating secret key: {e}")

def wait_for_services():
    """Wait for services to be ready with improved feedback."""
    print("Waiting for services to initialize (this may take a few minutes on first run)...")
    
    # Wait for critical services
    services_to_check = {
        "qdrant": ("http://localhost:6333/", "Qdrant"),
        "n8n": ("http://localhost:5678/", "n8n"),
        "open-webui": ("http://localhost:3000/", "Open WebUI"),
        "searxng": ("http://localhost:4000/", "SearXNG"),
        "clerk": ("http://localhost:3001/", "Clerk Frontend")
    }
    
    print("\nChecking service availability:")
    max_wait = 180  # 3 minutes total
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        all_ready = True
        for service, (url, name) in services_to_check.items():
            try:
                import urllib.request
                urllib.request.urlopen(url, timeout=2)
                print(f"✓ {name} is ready at {url}")
            except:
                print(f"⏳ Waiting for {name}...")
                all_ready = False
        
        if all_ready:
            print("\nAll services are ready!")
            break
        else:
            time.sleep(5)
    else:
        print("\nWarning: Some services may still be initializing.")
    
    print("\nYou can now access:")
    print("- Open WebUI (Chat Interface): http://localhost:3000")
    print("- Clerk Legal AI Frontend: http://localhost:3001") 
    print("- n8n Workflow Automation: http://localhost:5678")
    print("- SearXNG Search: http://localhost:4000")
    print("- Qdrant Vector Database: http://localhost:6333/dashboard")
    print("- PostgreSQL Database: localhost:5432 (user: postgres)")
    print("\nTo stop all services, run: python stop_services.py")

def main():
    parser = argparse.ArgumentParser(description="Start local AI services with optional GPU support")
    parser.add_argument("--profile", choices=["none", "gpu", "cpu"], default="cpu",
                      help="Docker Compose profile to use (default: cpu)")
    parser.add_argument("--environment", choices=["none", "private", "public"], default="none",
                      help="Environment override file to use (default: none)")
    parser.add_argument("--skip-supabase", action="store_true",
                      help="Skip starting Supabase services")
    parser.add_argument("--rebuild", action="store_true",
                      help="Force rebuild of all containers")
    parser.add_argument("--no-postgres-expose", action="store_true",
                      help="Don't expose PostgreSQL on host (disables Clerk JWT auth)")
    args = parser.parse_args()

    # Check if .env file exists
    if not os.path.exists(".env"):
        print("Error: .env file not found. Please copy .env.example to .env and configure it.")
        sys.exit(1)

    # If GPU profile, check for nvidia-smi
    if args.profile == "gpu":
        try:
            subprocess.run(["nvidia-smi"], capture_output=True, check=True)
            print("NVIDIA GPU detected. Using GPU-enabled services.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Warning: NVIDIA GPU not detected or nvidia-smi not available.")
            print("Falling back to CPU profile.")
            args.profile = "cpu"

    # Stop existing containers first
    stop_existing_containers(args.profile)

    # Clone Supabase repo
    if not args.skip_supabase:
        clone_supabase_repo()
        prepare_supabase_env()
        
        # Start Supabase
        start_supabase(args.environment, args.rebuild)
        
        # Give Supabase time to initialize (it needs to be ready before local AI services)
        print("Waiting 20 seconds for Supabase to initialize...")
        time.sleep(20)
    
    # Generate SearXNG secret key if needed
    generate_searxng_secret_key()

    # Start local AI services with PostgreSQL exposed by default
    start_local_ai(args.profile, args.environment, args.rebuild, 
                   expose_postgres=not args.no_postgres_expose)
    
    # Wait for PostgreSQL if exposed
    if not args.no_postgres_expose:
        if wait_for_postgres():
            # Ask about database initialization
            init_clerk_database()
    
    # Wait for all services with improved UI
    wait_for_services()

if __name__ == "__main__":
    main()
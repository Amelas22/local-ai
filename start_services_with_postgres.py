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
import psycopg2
from psycopg2.extras import RealDictCursor

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

def rebuild_container(container_name, profile=None):
    """Rebuild a specific container without cache."""
    print(f"Rebuilding container: {container_name}")
    
    # Map container names to their compose files
    compose_files_map = {
        "clerk": ["docker-compose.clerk.yml"],
        "supabase": ["supabase/docker/docker-compose.yml"],
        "all": None  # Special case for all containers
    }
    
    if container_name == "all":
        # Rebuild all containers
        print("Rebuilding all containers...")
        # Rebuild Supabase
        cmd = ["docker", "compose", "-p", "localai", "-f", "supabase/docker/docker-compose.yml", "build", "--no-cache"]
        run_command(cmd)
        
        # Rebuild local AI services
        cmd = ["docker", "compose", "-p", "localai"]
        if profile and profile != "none":
            cmd.extend(["--profile", profile])
        cmd.extend(["-f", "docker-compose.yml", "-f", "docker-compose.clerk.yml", "-f", "docker-compose.clerk-jwt.yml", "build", "--no-cache"])
        run_command(cmd)
    else:
        # Rebuild specific container
        if container_name in compose_files_map:
            compose_files = compose_files_map[container_name]
            cmd = ["docker", "compose", "-p", "localai"]
            if profile and profile != "none" and container_name != "supabase":
                cmd.extend(["--profile", profile])
            for cf in compose_files:
                cmd.extend(["-f", cf])
            cmd.extend(["build", "--no-cache"])
            run_command(cmd)
        else:
            # Try to rebuild any service by name
            cmd = ["docker", "compose", "-p", "localai"]
            if profile and profile != "none":
                cmd.extend(["--profile", profile])
            cmd.extend(["-f", "docker-compose.yml", "-f", "docker-compose.clerk.yml", "build", "--no-cache", container_name])
            run_command(cmd)

def start_supabase(environment=None):
    """Start the Supabase services (using its compose file)."""
    print("Starting Supabase services...")
    cmd = ["docker", "compose", "-p", "localai", "-f", "supabase/docker/docker-compose.yml"]
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.supabase.yml"])
    cmd.extend(["up", "-d"])
    run_command(cmd)

def start_local_ai(profile=None, environment=None, expose_postgres=True):
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
    cmd.extend(["up", "-d"])
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

def get_db_connection():
    """Get a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="postgres",
            user="postgres",
            password="postgres"
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def check_database_schema(conn):
    """Check if the database schema is properly initialized."""
    required_tables = ['law_firms', 'users', 'cases', 'case_permissions']
    missing_tables = []
    incomplete_tables = {}
    
    with conn.cursor() as cur:
        # Check which tables exist
        for table in required_tables:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, (table,))
            exists = cur.fetchone()[0]
            if not exists:
                missing_tables.append(table)
        
        # Check table structures for existing tables
        if 'cases' in required_tables and 'cases' not in missing_tables:
            # Check if cases table has all required columns
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'cases' 
                AND table_schema = 'public';
            """)
            columns = [row[0] for row in cur.fetchall()]
            required_columns = ['id', 'name', 'law_firm_id', 'collection_name', 
                              'description', 'status', 'created_by', 'created_at', 
                              'updated_at', 'metadata']
            missing_columns = [col for col in required_columns if col not in columns]
            if missing_columns:
                incomplete_tables['cases'] = missing_columns
    
    return missing_tables, incomplete_tables

def init_database(conn):
    """Initialize the database with the SQL script."""
    print("Initializing database with dev data...")
    sql_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "init_clerk_db.sql")
    
    if not os.path.exists(sql_file):
        print(f"Error: SQL initialization file not found at {sql_file}")
        return False
    
    try:
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        with conn.cursor() as cur:
            cur.execute(sql_content)
            conn.commit()
        
        print("Database initialized successfully with dev data!")
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
        return False

def run_migration(conn, incomplete_tables):
    """Run migration to add missing columns to existing tables."""
    print("Running database migration to add missing columns...")
    
    try:
        with conn.cursor() as cur:
            for table, missing_columns in incomplete_tables.items():
                print(f"Updating table '{table}' with missing columns: {missing_columns}")
                
                if table == 'cases':
                    # Add missing columns to cases table
                    if 'metadata' in missing_columns:
                        cur.execute("ALTER TABLE cases ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;")
                    if 'collection_name' in missing_columns:
                        cur.execute("ALTER TABLE cases ADD COLUMN IF NOT EXISTS collection_name VARCHAR(255) UNIQUE;")
                    if 'status' in missing_columns:
                        cur.execute("ALTER TABLE cases ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'active';")
                    if 'description' in missing_columns:
                        cur.execute("ALTER TABLE cases ADD COLUMN IF NOT EXISTS description TEXT;")
                    if 'updated_at' in missing_columns:
                        cur.execute("ALTER TABLE cases ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();")
                        # Also add the trigger for updated_at
                        cur.execute("""
                            CREATE OR REPLACE FUNCTION update_updated_at_column()
                            RETURNS TRIGGER AS $$
                            BEGIN
                                NEW.updated_at = NOW();
                                RETURN NEW;
                            END;
                            $$ language 'plpgsql';
                        """)
                        cur.execute("""
                            CREATE TRIGGER update_cases_updated_at BEFORE UPDATE ON cases
                            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                        """)
            
            conn.commit()
            print("Migration completed successfully!")
            return True
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        return False

def check_and_init_database():
    """Check database status and initialize/migrate as needed."""
    print("\nChecking PostgreSQL database status...")
    
    conn = get_db_connection()
    if not conn:
        print("Could not connect to database. Skipping initialization.")
        return
    
    try:
        missing_tables, incomplete_tables = check_database_schema(conn)
        
        if not missing_tables and not incomplete_tables:
            print("Database is properly initialized!")
            # Check if dev data exists
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT COUNT(*) as count FROM law_firms WHERE id = 'dev-firm-123';")
                result = cur.fetchone()
                if result['count'] == 0:
                    print("Dev data not found. Adding dev law firm and user...")
                    init_database(conn)
        elif missing_tables == ['law_firms', 'users', 'cases', 'case_permissions']:
            # All tables missing - fresh database
            print("Database is empty. Initializing with schema and dev data...")
            init_database(conn)
        elif missing_tables:
            # Some tables missing - partial setup
            print(f"Missing tables: {missing_tables}")
            print("Running full initialization...")
            init_database(conn)
        elif incomplete_tables:
            # Tables exist but missing columns
            print(f"Incomplete tables found: {list(incomplete_tables.keys())}")
            run_migration(conn, incomplete_tables)
            # After migration, ensure dev data exists
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT COUNT(*) as count FROM law_firms WHERE id = 'dev-firm-123';")
                result = cur.fetchone()
                if result['count'] == 0:
                    print("Adding dev data after migration...")
                    init_database(conn)
    finally:
        conn.close()

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
        "clerk": ("http://localhost:8010/", "Clerk Frontend (via Caddy)")
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
    print("- Clerk Legal AI Frontend: http://localhost:8010") 
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
    parser.add_argument("--rebuild", type=str, metavar="CONTAINER",
                      help="Rebuild specific container without cache (e.g., 'clerk', 'all')")
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

    # Handle rebuild flag if provided
    if args.rebuild:
        rebuild_container(args.rebuild, args.profile)

    # Stop existing containers first
    stop_existing_containers(args.profile)

    # Clone Supabase repo
    if not args.skip_supabase:
        clone_supabase_repo()
        prepare_supabase_env()
        
        # Start Supabase (step 1: start services in order)
        start_supabase(args.environment)
        
        # Give Supabase time to initialize (it needs to be ready before local AI services)
        print("Waiting 20 seconds for Supabase to initialize...")
        time.sleep(20)
    
    # Generate SearXNG secret key if needed
    generate_searxng_secret_key()

    # Start local AI services with PostgreSQL exposed by default (step 2)
    start_local_ai(args.profile, args.environment, expose_postgres=not args.no_postgres_expose)
    
    # Wait for PostgreSQL if exposed
    if not args.no_postgres_expose:
        if wait_for_postgres():
            # Check and initialize database (steps 3-6)
            check_and_init_database()
    
    # Wait for all services with improved UI
    wait_for_services()

if __name__ == "__main__":
    # Check if psycopg2 is installed
    try:
        import psycopg2
    except ImportError:
        print("Error: psycopg2 is required for database operations.")
        print("Please install it with: pip install psycopg2-binary")
        sys.exit(1)
    
    main()
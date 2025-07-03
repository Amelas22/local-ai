#!/bin/bash
# Script to fix PostgreSQL version mismatch

echo "PostgreSQL Version Fix Script"
echo "============================"

# Check which option to use
echo "Choose an option:"
echo "1. Upgrade to PostgreSQL 17 (recommended if no critical data)"
echo "2. Downgrade to PostgreSQL 15 (requires data backup/restore)"
echo "3. Clean restart (DELETE ALL DATA - use only if data is not important)"

read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo "Upgrading to PostgreSQL 17..."
        # Already done in the .env file edit above
        echo "✅ .env file already updated to use PostgreSQL 17"
        echo ""
        echo "Now run:"
        echo "docker-compose down"
        echo "docker-compose up -d postgres"
        echo ""
        echo "Note: This will work only if the container can access PG17 data"
        ;;
    
    2)
        echo "This requires manual backup and restore process:"
        echo ""
        echo "1. First, start a PostgreSQL 17 container to backup data:"
        echo "   docker run -d --name pg17-backup -v your_data_volume:/var/lib/postgresql/data postgres:17"
        echo ""
        echo "2. Backup the database:"
        echo "   docker exec pg17-backup pg_dumpall -U postgres > backup.sql"
        echo ""
        echo "3. Stop and remove the container:"
        echo "   docker stop pg17-backup && docker rm pg17-backup"
        echo ""
        echo "4. Remove the old data directory:"
        echo "   docker volume rm your_data_volume"
        echo ""
        echo "5. Start PostgreSQL 15 and restore:"
        echo "   docker-compose up -d postgres"
        echo "   docker exec -i postgres psql -U postgres < backup.sql"
        ;;
    
    3)
        echo "⚠️  WARNING: This will DELETE ALL PostgreSQL data!"
        read -p "Are you sure? (yes/no): " confirm
        
        if [ "$confirm" = "yes" ]; then
            echo "Stopping containers..."
            docker-compose down
            
            echo "Finding PostgreSQL volumes..."
            # List volumes that might contain postgres data
            docker volume ls | grep postgres
            
            echo ""
            echo "To remove a volume, run:"
            echo "docker volume rm <volume_name>"
            echo ""
            echo "Common volume names:"
            echo "- local-ai-package_postgres_data"
            echo "- local-ai-package_db-data"
            echo ""
            echo "After removing volumes, run:"
            echo "docker-compose up -d postgres"
        else
            echo "Cancelled."
        fi
        ;;
    
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
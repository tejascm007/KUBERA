"""
Database Initialization Script
Creates database, runs migrations, and seeds initial data
"""

import asyncio
import asyncpg
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from datetime import datetime

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def check_database_exists(conn, db_name: str) -> bool:
    """Check if database exists"""
    query = "SELECT 1 FROM pg_database WHERE datname = $1"
    result = await conn.fetchval(query, db_name)
    return result is not None


async def create_database():
    """Create database if it doesn't exist"""
    # Connect to default postgres database
    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database='postgres'
    )
    
    try:
        # Check if database exists
        db_exists = await check_database_exists(conn, settings.POSTGRES_DB)
        
        if db_exists:
            logger.info(f"Database '{settings.POSTGRES_DB}' already exists")
        else:
            logger.info(f"Creating database '{settings.POSTGRES_DB}'...")
            await conn.execute(f'CREATE DATABASE {settings.POSTGRES_DB}')
            logger.info(f"Database '{settings.POSTGRES_DB}' created successfully")
    
    finally:
        await conn.close()


async def run_migration_file(conn, filepath: str):
    """Run a single migration SQL file"""
    logger.info(f"Running migration: {os.path.basename(filepath)}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    try:
        await conn.execute(sql)
        logger.info(f"Migration completed: {os.path.basename(filepath)}")
    except Exception as e:
        logger.error(f"Migration failed: {os.path.basename(filepath)}")
        logger.error(f"Error: {e}")
        raise


async def run_migrations():
    """Run all migration files in order"""
    # Connect to application database
    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB
    )
    
    try:
        logger.info("=" * 80)
        logger.info("RUNNING DATABASE MIGRATIONS")
        logger.info("=" * 80)
        
        # Get migrations directory
        migrations_dir = Path(__file__).parent.parent / "app" / "db" / "migrations"
        
        # Migration files in order
        migration_files = [
            "v1_initial_schema.sql",
            "v2_indexes.sql",
            "v3_constraints.sql"
        ]
        
        # Run each migration
        for migration_file in migration_files:
            filepath = migrations_dir / migration_file
            
            if not filepath.exists():
                logger.warning(f"Migration file not found: {migration_file}")
                continue
            
            await run_migration_file(conn, str(filepath))
        
        logger.info("=" * 80)
        logger.info("ALL MIGRATIONS COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
    
    finally:
        await conn.close()


async def verify_setup():
    """Verify database setup"""
    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB
    )
    
    try:
        logger.info("=" * 80)
        logger.info("VERIFYING DATABASE SETUP")
        logger.info("=" * 80)
        
        # Check tables
        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        tables = await conn.fetch(tables_query)
        
        logger.info(f"Total tables: {len(tables)}")
        for table in tables:
            logger.info(f"  {table['table_name']}")
        
        # Check schema version
        version_query = "SELECT * FROM schema_version ORDER BY applied_at DESC LIMIT 3"
        versions = await conn.fetch(version_query)
        
        logger.info(f"\nSchema versions:")
        for version in versions:
            logger.info(f"  {version['version']}: {version['description']}")
            logger.info(f"     Applied at: {version['applied_at']}")
        
        # Check default data
        system_status = await conn.fetchrow("SELECT * FROM system_status LIMIT 1")
        rate_limit_config = await conn.fetchrow("SELECT * FROM rate_limit_config LIMIT 1")
        
        logger.info(f"\nDefault data:")
        logger.info(f"  System status: {system_status['current_status'] if system_status else 'NOT FOUND'}")
        logger.info(f"  Rate limit config: {rate_limit_config['burst_limit_per_minute'] if rate_limit_config else 'NOT FOUND'}/min burst")
        
        logger.info("=" * 80)
        logger.info("DATABASE SETUP VERIFICATION COMPLETE")
        logger.info("=" * 80)
    
    finally:
        await conn.close()


async def main():
    """Main initialization function"""
    try:
        logger.info("=" * 80)
        logger.info("KUBERA DATABASE INITIALIZATION")
        logger.info("=" * 80)
        logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
        logger.info(f"Host: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
        logger.info(f"Database: {settings.POSTGRES_DB}")
        logger.info(f"User: {settings.POSTGRES_USER}")
        logger.info("=" * 80)
        
        # Step 1: Create database
        logger.info("\nSTEP 1: CREATE DATABASE")
        await create_database()
        
        # Step 2: Run migrations
        logger.info("\nSTEP 2: RUN MIGRATIONS")
        await run_migrations()
        
        # Step 3: Verify setup
        logger.info("\nSTEP 3: VERIFY SETUP")
        await verify_setup()
        
        logger.info("\n" + "=" * 80)
        logger.info("DATABASE INITIALIZATION COMPLETE!")
        logger.info("=" * 80)
        logger.info("\nNEXT STEPS:")
        logger.info("1. Run 'python scripts/seed_admin.py' to create admin user")
        logger.info("2. Run 'python scripts/seed_rate_limits.py' to configure rate limits")
        logger.info("3. Start the application with 'python run.py'")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"\nDATABASE INITIALIZATION FAILED")
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

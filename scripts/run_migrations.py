"""
Migration Runner Script
Runs database migrations
"""

import asyncio
import asyncpg
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from datetime import datetime

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def get_applied_migrations(conn):
    """Get list of applied migrations"""
    try:
        query = "SELECT version FROM schema_version ORDER BY applied_at"
        rows = await conn.fetch(query)
        return [row['version'] for row in rows]
    except:
        return []


async def apply_migration(conn, filepath: str, version: str):
    """Apply a single migration"""
    logger.info(f"Applying migration: {os.path.basename(filepath)}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    try:
        await conn.execute(sql)
        logger.info(f"Migration applied: {version}")
    except Exception as e:
        logger.error(f"Migration failed: {version}")
        logger.error(f"Error: {e}")
        raise


async def rollback_migration(conn, version: str):
    """Rollback a migration (if rollback script exists)"""
    migrations_dir = Path(__file__).parent.parent / "app" / "db" / "migrations"
    rollback_file = migrations_dir / f"{version}_rollback.sql"
    
    if not rollback_file.exists():
        logger.error(f"No rollback script found for {version}")
        return False
    
    logger.info(f"Rolling back migration: {version}")
    
    with open(rollback_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    try:
        await conn.execute(sql)
        
        # Remove from schema_version
        await conn.execute(
            "DELETE FROM schema_version WHERE version = $1",
            version
        )
        
        logger.info(f"Migration rolled back: {version}")
        return True
        
    except Exception as e:
        logger.error(f"Rollback failed: {version}")
        logger.error(f"Error: {e}")
        return False


async def run_migrations():
    """Run all pending migrations"""
    import os
    
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
        
        # Get applied migrations
        applied = await get_applied_migrations(conn)
        logger.info(f"Applied migrations: {', '.join(applied) if applied else 'None'}")
        
        # Available migrations
        migrations = {
            "v1.0": "v1_initial_schema.sql",
            "v2.0": "v2_indexes.sql",
            "v3.0": "v3_constraints.sql"
        }
        
        pending = []
        for version, filename in migrations.items():
            if version not in applied:
                pending.append((version, filename))
        
        if not pending:
            logger.info("No pending migrations")
            return
        
        logger.info(f"Pending migrations: {len(pending)}")
        
        # Run pending migrations
        for version, filename in pending:
            filepath = migrations_dir / filename
            
            if not filepath.exists():
                logger.warning(f"Migration file not found: {filename}")
                continue
            
            await apply_migration(conn, str(filepath), version)
        
        logger.info("=" * 80)
        logger.info("ALL MIGRATIONS COMPLETED")
        logger.info("=" * 80)
    
    finally:
        await conn.close()


async def show_migration_status():
    """Show migration status"""
    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB
    )
    
    try:
        logger.info("=" * 80)
        logger.info("MIGRATION STATUS")
        logger.info("=" * 80)
        
        query = "SELECT * FROM schema_version ORDER BY applied_at"
        rows = await conn.fetch(query)
        
        if not rows:
            logger.info("No migrations applied yet")
            return
        
        for row in rows:
            logger.info(f"\n{row['version']}: {row['description']}")
            logger.info(f"Applied at: {row['applied_at']}")
        
        logger.info("=" * 80)
    
    finally:
        await conn.close()


async def main():
    """Main function"""
    try:
        logger.info("=" * 80)
        logger.info("KUBERA MIGRATION RUNNER")
        logger.info("=" * 80)
        logger.info(f"Database: {settings.POSTGRES_DB}")
        logger.info(f"Host: {settings.POSTGRES_HOST}")
        logger.info("=" * 80)
        
        # Check command line arguments
        if len(sys.argv) > 1:
            command = sys.argv[1]
            
            if command == "status":
                await show_migration_status()
                return
            
            elif command == "migrate":
                await run_migrations()
                return
            
            else:
                logger.error(f"Unknown command: {command}")
                logger.info("\nUsage:")
                logger.info("  python scripts/run_migrations.py status   - Show migration status")
                logger.info("  python scripts/run_migrations.py migrate  - Run pending migrations")
                sys.exit(1)
        
        # Default: run migrations
        await run_migrations()
        
    except Exception as e:
        logger.error(f"\nMIGRATION RUNNER FAILED")
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

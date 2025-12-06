"""
Database Connection Module - Supabase Compatible
Async PostgreSQL connection using asyncpg with Supabase Transaction Pooler
"""

import asyncpg
import logging
from typing import Optional
from contextlib import asynccontextmanager

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global connection pool
_pool: Optional[asyncpg.Pool] = None


async def init_db() -> asyncpg.Pool:
    """
    Initialize database connection pool for Supabase
    
    IMPORTANT: Uses statement_cache_size=0 for Supabase/PgBouncer compatibility
    """
    global _pool
    
    if _pool is not None:
        return _pool
    
    try:
        logger.info("=" * 60)
        logger.info("CONNECTING TO SUPABASE DATABASE")
        logger.info("=" * 60)
        logger.info(f"Host: {settings.POSTGRES_HOST}")
        logger.info(f"Port: {settings.POSTGRES_PORT}")
        logger.info(f"Database: {settings.POSTGRES_DB}")
        logger.info(f"User: {settings.POSTGRES_USER}")
        
        # Create connection pool with Supabase-compatible settings
        _pool = await asyncpg.create_pool(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
            min_size=settings.POSTGRES_MIN_POOL_SIZE,
            max_size=settings.POSTGRES_MAX_POOL_SIZE,
            # CRITICAL: Disable prepared statements for Supabase/PgBouncer
            statement_cache_size=0,
            # SSL required for Supabase
            ssl='require',
            # Connection timeout
            command_timeout=60,
            # Server settings
            server_settings={
                'timezone': 'Asia/Kolkata'
            }
        )
        
        # Test connection
        async with _pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            logger.info(f"Connected to PostgreSQL")
            logger.info(f"Version: {version[:50]}...")
            
            # Test timezone
            tz = await conn.fetchval("SHOW timezone")
            logger.info(f"Timezone: {tz}")
        
        logger.info("=" * 60)
        logger.info("DATABASE CONNECTION POOL INITIALIZED")
        logger.info(f"Pool size: {settings.POSTGRES_MIN_POOL_SIZE}-{settings.POSTGRES_MAX_POOL_SIZE}")
        logger.info("=" * 60)
        
        return _pool
        
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def close_db():
    """Close database connection pool"""
    global _pool
    
    if _pool is not None:
        logger.info("Closing database connection pool...")
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


def get_db_pool() -> asyncpg.Pool:
    """Get the database connection pool"""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db() first.")
    return _pool


@asynccontextmanager
async def get_db_connection():
    """
    Get a database connection from the pool
    
    Usage:
        async with get_db_connection() as conn:
            result = await conn.fetch("SELECT * FROM users")
    """
    pool = get_db_pool()
    async with pool.acquire() as connection:
        yield connection


async def execute_query(query: str, *args):
    """Execute a query and return result"""
    async with get_db_connection() as conn:
        return await conn.execute(query, *args)


async def fetch_one(query: str, *args):
    """Fetch a single row"""
    async with get_db_connection() as conn:
        return await conn.fetchrow(query, *args)


async def fetch_all(query: str, *args):
    """Fetch all rows"""
    async with get_db_connection() as conn:
        return await conn.fetch(query, *args)


async def fetch_val(query: str, *args):
    """Fetch a single value"""
    async with get_db_connection() as conn:
        return await conn.fetchval(query, *args)

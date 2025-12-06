"""
Cleanup Jobs
Cleans up expired OTPs, revoked tokens, and other temporary data
"""

import logging
from datetime import datetime, timedelta
import asyncpg

from app.db.repositories.otp_repository import OTPRepository
from app.db.repositories.token_repository import TokenRepository

logger = logging.getLogger(__name__)


async def cleanup_expired_otps(db_pool: asyncpg.Pool):
    """
    Clean up expired OTPs (runs every hour)
    
    Deletes OTPs that are:
    - Expired (created_at > OTP_EXPIRE_MINUTES)
    - Already verified
    - Failed attempts exceeded
    
    Args:
        db_pool: Database connection pool
    """
    start_time = datetime.now()
    
    try:
        logger.info("=" * 70)
        logger.info(" STARTING OTP CLEANUP JOB")
        logger.info(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S IST')}")
        logger.info("=" * 70)
        
        otp_repo = OTPRepository(db_pool)
        
        # Delete expired OTPs (older than 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        query = """
            DELETE FROM otps
            WHERE created_at < $1
            RETURNING otp_id
        """
        
        async with db_pool.acquire() as conn:
            deleted_rows = await conn.fetch(query, cutoff_time)
            deleted_count = len(deleted_rows)
        
        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 70)
        logger.info(" OTP CLEANUP COMPLETED")
        logger.info(f"Deleted: {deleted_count} OTPs")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f" OTP cleanup job failed: {e}", exc_info=True)


async def cleanup_revoked_tokens(db_pool: asyncpg.Pool):
    """
    Clean up old revoked tokens (runs every 6 hours)
    
    Deletes tokens that are:
    - Revoked
    - Expired (expires_at < now)
    - Older than 30 days
    
    Args:
        db_pool: Database connection pool
    """
    start_time = datetime.now()
    
    try:
        logger.info("=" * 70)
        logger.info(" STARTING TOKEN CLEANUP JOB")
        logger.info(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S IST')}")
        logger.info("=" * 70)
        
        # Delete expired and old revoked tokens
        current_time = datetime.now()
        old_token_cutoff = current_time - timedelta(days=30)
        
        query = """
            DELETE FROM refresh_tokens
            WHERE (
                (revoked_at IS NOT NULL AND revoked_at < $1)
                OR (expires_at < $2)
            )
            RETURNING token_id
        """
        
        async with db_pool.acquire() as conn:
            deleted_rows = await conn.fetch(query, old_token_cutoff, current_time)
            deleted_count = len(deleted_rows)
        
        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 70)
        logger.info(" TOKEN CLEANUP COMPLETED")
        logger.info(f"Deleted: {deleted_count} tokens")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f" Token cleanup job failed: {e}", exc_info=True)


async def cleanup_old_rate_limit_violations(db_pool: asyncpg.Pool):
    """
    Clean up old rate limit violation logs (optional)
    
    Deletes violations older than 90 days
    
    Args:
        db_pool: Database connection pool
    """
    start_time = datetime.now()
    
    try:
        logger.info("=" * 70)
        logger.info("STARTING RATE LIMIT VIOLATIONS CLEANUP")
        logger.info(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S IST')}")
        logger.info("=" * 70)
        
        cutoff_time = datetime.now() - timedelta(days=90)
        
        query = """
            DELETE FROM rate_limit_violations
            WHERE violated_at < $1
            RETURNING violation_id
        """
        
        async with db_pool.acquire() as conn:
            deleted_rows = await conn.fetch(query, cutoff_time)
            deleted_count = len(deleted_rows)
        
        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 70)
        logger.info(" RATE LIMIT VIOLATIONS CLEANUP COMPLETED")
        logger.info(f"Deleted: {deleted_count} violations")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f" Rate limit violations cleanup failed: {e}", exc_info=True)


async def cleanup_old_email_logs(db_pool: asyncpg.Pool):
    """
    Clean up old email logs (optional)
    
    Deletes email logs older than 180 days
    
    Args:
        db_pool: Database connection pool
    """
    start_time = datetime.now()
    
    try:
        logger.info("=" * 70)
        logger.info("STARTING EMAIL LOGS CLEANUP")
        logger.info(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S IST')}")
        logger.info("=" * 70)
        
        cutoff_time = datetime.now() - timedelta(days=180)
        
        query = """
            DELETE FROM email_logs
            WHERE sent_at < $1
            RETURNING log_id
        """
        
        async with db_pool.acquire() as conn:
            deleted_rows = await conn.fetch(query, cutoff_time)
            deleted_count = len(deleted_rows)
        
        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 70)
        logger.info("EMAIL LOGS CLEANUP COMPLETED")
        logger.info(f"Deleted: {deleted_count} logs")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f" Email logs cleanup failed: {e}", exc_info=True)

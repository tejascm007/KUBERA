"""
OTP Repository
Database operations for otps table
"""

import asyncpg
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.core.security import get_current_ist_time, hash_otp

logger = logging.getLogger(__name__)


class OTPRepository:
    """Repository for OTP database operations"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    # ========================================================================
    # CREATE
    # ========================================================================
    
    async def create_otp(
        self,
        email: str,
        otp: str,
        otp_type: str,
        expire_minutes: int = 10
    ) -> Dict[str, Any]:
        """Create a new OTP entry"""
        otp_hash = hash_otp(otp)
        expires_at = get_current_ist_time() + timedelta(minutes=expire_minutes)
        
        query = """
            INSERT INTO otps (email, otp_type, otp_hash, expires_at)
            VALUES ($1, $2, $3, $4)
            RETURNING otp_id, email, otp_type, otp_hash, created_at, expires_at, is_verified, attempt_count, verified_at
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, email.lower(), otp_type, otp_hash, expires_at)
            return dict(row) if row else None
    
    # ========================================================================
    # READ
    # ========================================================================
    
    async def get_latest_otp(
        self,
        email: str,
        otp_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get latest unverified OTP for email and type"""
        query = """
            SELECT * FROM otps
            WHERE email = $1 AND otp_type = $2 AND is_verified = FALSE
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, email.lower(), otp_type)
            return dict(row) if row else None
    
    # ========================================================================
    # UPDATE
    # ========================================================================
    
    async def increment_attempt_count(self, otp_id: str) -> int:
        """Increment OTP attempt count and return new count"""
        query = """
            UPDATE otps
            SET attempt_count = attempt_count + 1
            WHERE otp_id = $1
            RETURNING attempt_count
        """
        
        async with self.db.acquire() as conn:
            return await conn.fetchval(query, otp_id)
    
    async def mark_verified(self, otp_id: str) -> None:
        """Mark OTP as verified"""
        query = """
            UPDATE otps
            SET is_verified = TRUE, verified_at = $1
            WHERE otp_id = $2
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(query, get_current_ist_time(), otp_id)
    
    # ========================================================================
    # DELETE
    # ========================================================================
    
    async def delete_expired_otps(self) -> int:
        """Delete expired OTPs (cleanup job)"""
        query = """
            DELETE FROM otps
            WHERE expires_at < $1 OR (is_verified = TRUE AND verified_at < $2)
        """
        
        current_time = get_current_ist_time()
        cleanup_threshold = current_time - timedelta(hours=24)
        
        async with self.db.acquire() as conn:
            result = await conn.execute(query, current_time, cleanup_threshold)
            # Extract count from result string like "DELETE 5"
            return int(result.split()[-1]) if result else 0
    
    async def delete_user_otps(self, email: str) -> None:
        """Delete all OTPs for an email"""
        query = "DELETE FROM otps WHERE email = $1"
        
        async with self.db.acquire() as conn:
            await conn.execute(query, email.lower())

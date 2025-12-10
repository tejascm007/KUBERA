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
        otp_type: str,
        verified: Optional[bool] = None  # ← NEW: Can filter by verified status
    ) -> Optional[Dict[str, Any]]:
        """
            Get latest OTP for email and type
            
            Args:
                email: User email
                otp_type: Type of OTP (registration, password_reset, etc.)
                verified: If True, get verified OTP. If False, get unverified. If None, get any.
            """
        if verified is None:
            # Get latest OTP regardless of verification status
            query = """
                SELECT * FROM otps
                WHERE email = $1 AND otp_type = $2
                ORDER BY created_at DESC
                LIMIT 1
            """
        else:
            # Filter by verification status
            query = """
                SELECT * FROM otps
                WHERE email = $1 AND otp_type = $2 AND is_verified = $3
                ORDER BY created_at DESC
                LIMIT 1
            """
        
        async with self.db.acquire() as conn:
            if verified is None:
                row = await conn.fetchrow(query, email.lower(), otp_type)
            else:
                row = await conn.fetchrow(query, email.lower(), otp_type, verified)
            return dict(row) if row else None


    async def get_latest_unverified_otp(
        self,
        email: str,
        otp_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get latest unverified OTP for email and type (used in Step 2)"""
        return await self.get_latest_otp(email, otp_type, verified=False)


    async def get_latest_verified_otp(
        self,
        email: str,
        otp_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get latest verified OTP for email and type (used in Step 3)"""
        return await self.get_latest_otp(email, otp_type, verified=True)

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


# ==========================================
# FORGOT PASSWORD REPOSITORY FUNCTIONS
# ==========================================

async def create_forgot_password_otp(
    self,
    email: str,
    otp_hash: str
) -> dict:
    """Create or update OTP for forgot password"""
    
    query = """
    INSERT INTO otps (email, otp_hash, otp_type, is_verified, attempt_count, created_at, verified_at)
    VALUES (:email, :otp_hash, :otp_type, FALSE, 0, NOW(), NULL)
    ON CONFLICT (email) DO UPDATE SET
        otp_hash = :otp_hash,
        otp_type = :otp_type,
        is_verified = FALSE,
        attempt_count = 0,
        created_at = NOW(),
        verified_at = NULL
    WHERE otps.otp_type = :otp_type
    RETURNING otp_id, email, created_at;
    """
    
    result = await self.db.fetch_one(
        query,
        {
            "email": email.lower(),
            "otp_hash": otp_hash,
            "otp_type": "forgot_password"
        }
    )
    
    return result


async def verify_forgot_password_otp(
    self,
    email: str,
    otp_hash: str
) -> dict:
    """Verify OTP for forgot password"""
    
    query = """
    SELECT otp_id, email, is_verified, attempt_count, created_at
    FROM otps
    WHERE email = :email
    AND otp_type = 'forgot_password'
    AND otp_hash = :otp_hash
    ORDER BY created_at DESC
    LIMIT 1;
    """
    
    result = await self.db.fetch_one(
        query,
        {
            "email": email.lower(),
            "otp_hash": otp_hash
        }
    )
    
    return result


async def mark_forgot_password_otp_verified(self, email: str) -> bool:
    """Mark forgot password OTP as verified"""
    
    query = """
    UPDATE otps
    SET is_verified = TRUE, verified_at = NOW()
    WHERE email = :email
    AND otp_type = 'forgot_password'
    AND is_verified = FALSE;
    """
    
    result = await self.db.execute(
        query,
        {"email": email.lower()}
    )
    
    return result > 0


async def delete_forgot_password_otp(self, email: str) -> bool:
    """Delete forgot password OTP after successful reset"""
    
    query = """
    DELETE FROM otps
    WHERE email = :email
    AND otp_type = 'forgot_password';
    """
    
    result = await self.db.execute(
        query,
        {"email": email.lower()}
    )
    
    return result > 0

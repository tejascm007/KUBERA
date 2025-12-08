"""
Refresh Token Repository
Database operations for refresh_tokens table
"""

import asyncpg
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

from app.core.security import get_current_ist_time

logger = logging.getLogger(__name__)


class TokenRepository:
    """Repository for refresh token database operations"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    # ========================================================================
    # CREATE
    # ========================================================================
    
    async def create_refresh_token(
        self,
        user_id: str,
        jti: str,
        expires_at: datetime
    ) -> Dict[str, Any]:
        """Create a new refresh token entry"""
        query = """
            INSERT INTO refresh_tokens (user_id, jti, expires_at)
            VALUES ($1, $2, $3)
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, user_id, jti, expires_at)
            return dict(row) if row else None
    
    # ========================================================================
    # READ
    # ========================================================================
    
    async def get_token_by_jti(self, jti: str) -> Optional[Dict[str, Any]]:
        """Get token by JTI"""
        query = "SELECT * FROM refresh_tokens WHERE jti = $1"
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, jti)
            return dict(row) if row else None
    
    async def is_token_revoked(self, jti: str) -> bool:
        """Check if token is revoked"""
        query = "SELECT revoked FROM refresh_tokens WHERE jti = $1"
        
        async with self.db.acquire() as conn:
            result = await conn.fetchval(query, jti)
            return result if result is not None else True
    
    async def get_user_tokens(
        self,
        user_id: str,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all tokens for a user"""
        
        if active_only:
            query = """
                SELECT * FROM refresh_tokens
                WHERE user_id = $1 AND revoked = FALSE AND expires_at > $2
                ORDER BY issued_at DESC
            """
            params = [user_id, get_current_ist_time()]
        else:
            query = """
                SELECT * FROM refresh_tokens
                WHERE user_id = $1
                ORDER BY issued_at DESC
            """
            params = [user_id]
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    # ========================================================================
    # UPDATE
    # ========================================================================
    
    async def revoke_token(
        self,
        jti: str,
        reason: str = "user_logout"
    ) -> None:
        """Revoke a refresh token"""
        query = """
            UPDATE refresh_tokens
            SET 
                revoked = TRUE,
                revoked_reason = $1,
                revoked_at = $2
            WHERE jti = $3
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(query, reason, get_current_ist_time(), jti)
    
    async def revoke_all_user_tokens(
        self,
        user_id: str,
        reason: str = "password_change"
    ) -> int:
        """Revoke all tokens for a user"""
        query = """
            UPDATE refresh_tokens
            SET 
                revoked = TRUE,
                revoked_reason = $1,
                revoked_at = $2
            WHERE user_id = $3 AND revoked = FALSE
        """
        
        async with self.db.acquire() as conn:
            result = await conn.execute(query, reason, get_current_ist_time(), user_id)
            return int(result.split()[-1]) if result else 0
    
    async def update_last_used(self, jti: str) -> None:
        """Update last used timestamp"""
        query = """
            UPDATE refresh_tokens
            SET last_used_at = $1
            WHERE jti = $2
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(query, get_current_ist_time(), jti)
    
    # ========================================================================
    # DELETE
    # ========================================================================
    
    async def delete_expired_tokens(self) -> int:
        """Delete expired tokens (cleanup job)"""
        query = """
            DELETE FROM refresh_tokens
            WHERE expires_at < $1 OR (revoked = TRUE AND revoked_at < $2)
        """
        
        current_time = get_current_ist_time()
        cleanup_threshold = current_time - timedelta(days=30)
        
        async with self.db.acquire() as conn:
            result = await conn.execute(query, current_time, cleanup_threshold)
            return int(result.split()[-1]) if result else 0

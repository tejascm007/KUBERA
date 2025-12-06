"""
User Repository
Database operations for users table
"""

import asyncpg
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.core.security import get_current_ist_time

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user database operations"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    # ========================================================================
    # CREATE
    # ========================================================================
    
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user
        
        Args:
            user_data: Dictionary with user fields
        
        Returns:
            Created user dict
        """
        query = """
            INSERT INTO users (
                email, username, password_hash, full_name,
                phone, date_of_birth, investment_style,
                risk_tolerance, interested_sectors
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                query,
                user_data.get('email'),
                user_data.get('username'),
                user_data.get('password_hash'),
                user_data.get('full_name'),
                user_data.get('phone'),
                user_data.get('date_of_birth'),
                user_data.get('investment_style'),
                user_data.get('risk_tolerance'),
                user_data.get('interested_sectors', [])
            )
            
            return dict(row) if row else None
    
    # ========================================================================
    # READ
    # ========================================================================
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        query = "SELECT * FROM users WHERE user_id = $1"
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            return dict(row) if row else None
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        query = "SELECT * FROM users WHERE email = $1"
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, email.lower())
            return dict(row) if row else None
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        query = "SELECT * FROM users WHERE username = $1"
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, username.lower())
            return dict(row) if row else None
    
    async def check_email_exists(self, email: str) -> bool:
        """Check if email already exists"""
        query = "SELECT EXISTS(SELECT 1 FROM users WHERE email = $1)"
        
        async with self.db.acquire() as conn:
            return await conn.fetchval(query, email.lower())
    
    async def check_username_exists(self, username: str) -> bool:
        """Check if username already exists"""
        query = "SELECT EXISTS(SELECT 1 FROM users WHERE username = $1)"
        
        async with self.db.acquire() as conn:
            return await conn.fetchval(query, username.lower())
    
    async def get_all_users(
        self,
        limit: int = 100,
        offset: int = 0,
        account_status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all users with pagination and optional filtering"""
        
        if account_status:
            query = """
                SELECT * FROM users
                WHERE account_status = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """
            params = [account_status, limit, offset]
        else:
            query = """
                SELECT * FROM users
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
            """
            params = [limit, offset]
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def count_users(self, account_status: Optional[str] = None) -> int:
        """Count total users"""
        
        if account_status:
            query = "SELECT COUNT(*) FROM users WHERE account_status = $1"
            params = [account_status]
        else:
            query = "SELECT COUNT(*) FROM users"
            params = []
        
        async with self.db.acquire() as conn:
            return await conn.fetchval(query, *params)
    
    # ========================================================================
    # UPDATE
    # ========================================================================
    
    async def update_user(
        self,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update user fields
        
        Args:
            user_id: User UUID
            updates: Dictionary with fields to update
        
        Returns:
            Updated user dict
        """
        # Build dynamic update query
        set_clauses = []
        values = []
        param_count = 1
        
        for key, value in updates.items():
            if key not in ['user_id', 'created_at', 'updated_at']:
                set_clauses.append(f"{key} = ${param_count}")
                values.append(value)
                param_count += 1
        
        if not set_clauses:
            return await self.get_user_by_id(user_id)
        
        # Add updated_at
        set_clauses.append(f"updated_at = ${param_count}")
        values.append(get_current_ist_time())
        param_count += 1
        
        # Add user_id for WHERE clause
        values.append(user_id)
        
        query = f"""
            UPDATE users
            SET {', '.join(set_clauses)}
            WHERE user_id = ${param_count}
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            return dict(row) if row else None
    
    async def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp"""
        query = """
            UPDATE users
            SET last_login_at = $1
            WHERE user_id = $2
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(query, get_current_ist_time(), user_id)
    
    async def update_username(self, user_id: str, new_username: str) -> Optional[Dict[str, Any]]:
        """Update username"""
        query = """
            UPDATE users
            SET username = $1, updated_at = $2
            WHERE user_id = $3
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                query,
                new_username.lower(),
                get_current_ist_time(),
                user_id
            )
            return dict(row) if row else None
    
    async def update_password(self, user_id: str, new_password_hash: str) -> None:
        """Update user password"""
        query = """
            UPDATE users
            SET password_hash = $1, updated_at = $2
            WHERE user_id = $3
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(
                query,
                new_password_hash,
                get_current_ist_time(),
                user_id
            )
    
    async def update_account_status(
        self,
        user_id: str,
        status: str
    ) -> Optional[Dict[str, Any]]:
        """Update account status (active, deactivated, suspended)"""
        query = """
            UPDATE users
            SET account_status = $1, updated_at = $2
            WHERE user_id = $3
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                query,
                status,
                get_current_ist_time(),
                user_id
            )
            return dict(row) if row else None
    
    async def verify_email(self, user_id: str) -> None:
        """Mark email as verified"""
        query = """
            UPDATE users
            SET email_verified = TRUE, updated_at = $1
            WHERE user_id = $2
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(query, get_current_ist_time(), user_id)
    
    # ========================================================================
    # DELETE
    # ========================================================================
    
    async def delete_user(self, user_id: str) -> bool:
        """
        Delete user (hard delete)
        Note: Use deactivate instead in production
        """
        query = "DELETE FROM users WHERE user_id = $1"
        
        async with self.db.acquire() as conn:
            result = await conn.execute(query, user_id)
            return result == "DELETE 1"
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    async def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics (chats, messages, portfolio count)"""
        query = """
            SELECT
                (SELECT COUNT(*) FROM chats WHERE user_id = $1) as total_chats,
                (SELECT COUNT(*) FROM messages WHERE user_id = $1) as total_messages,
                (SELECT COUNT(*) FROM portfolios WHERE user_id = $1) as total_portfolio_entries,
                (SELECT SUM(prompt_count) FROM chats WHERE user_id = $1) as total_prompts
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            return dict(row) if row else {}

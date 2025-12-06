"""
Rate Limit Repository
Database operations for rate limiting tables
"""

import asyncpg
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

from app.core.security import get_current_ist_time

logger = logging.getLogger(__name__)


class RateLimitRepository:
    """Repository for rate limit database operations"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    # ========================================================================
    # RATE LIMIT CONFIG
    # ========================================================================
    
    async def get_rate_limit_config(self) -> Dict[str, Any]:
        """Get current rate limit configuration"""
        query = "SELECT * FROM rate_limit_config ORDER BY created_at DESC LIMIT 1"
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query)
            return dict(row) if row else None
    
    async def update_global_rate_limits(
        self,
        updates: Dict[str, Any],
        updated_by: str
    ) -> Dict[str, Any]:
        """Update global rate limits"""
        set_clauses = []
        values = []
        param_count = 1
        
        for key, value in updates.items():
            if key in ['burst_limit_per_minute', 'per_chat_limit', 'per_hour_limit', 'per_day_limit']:
                set_clauses.append(f"{key} = ${param_count}")
                values.append(value)
                param_count += 1
        
        if not set_clauses:
            return await self.get_rate_limit_config()
        
        # Add updated_at and updated_by
        set_clauses.append(f"updated_at = ${param_count}")
        values.append(get_current_ist_time())
        param_count += 1
        
        set_clauses.append(f"updated_by = ${param_count}")
        values.append(updated_by)
        
        query = f"""
            UPDATE rate_limit_config
            SET {', '.join(set_clauses)}
            WHERE config_id = (SELECT config_id FROM rate_limit_config ORDER BY created_at DESC LIMIT 1)
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            return dict(row) if row else None
    
    async def get_user_specific_limits(self, user_id: str) -> Optional[Dict[str, int]]:
        """Get user-specific rate limit overrides"""
        query = """
            SELECT user_specific_overrides->>$1 as limits
            FROM rate_limit_config
            ORDER BY created_at DESC LIMIT 1
        """
        
        async with self.db.acquire() as conn:
            result = await conn.fetchval(query, user_id)
            return result if result else None
    
    async def set_user_specific_limits(
        self,
        user_id: str,
        limits: Dict[str, int],
        updated_by: str
    ) -> None:
        """Set user-specific rate limit overrides"""
        query = """
            UPDATE rate_limit_config
            SET 
                user_specific_overrides = jsonb_set(
                    user_specific_overrides,
                    ARRAY[$1],
                    $2::jsonb
                ),
                updated_at = $3,
                updated_by = $4
            WHERE config_id = (SELECT config_id FROM rate_limit_config ORDER BY created_at DESC LIMIT 1)
        """
        
        import json
        
        async with self.db.acquire() as conn:
            await conn.execute(
                query,
                user_id,
                json.dumps(limits),
                get_current_ist_time(),
                updated_by
            )
    
    async def add_user_to_whitelist(self, user_id: str, updated_by: str) -> None:
        """Add user to whitelist (no rate limits)"""
        query = """
            UPDATE rate_limit_config
            SET 
                whitelisted_users = array_append(whitelisted_users, $1::uuid),
                updated_at = $2,
                updated_by = $3
            WHERE config_id = (SELECT config_id FROM rate_limit_config ORDER BY created_at DESC LIMIT 1)
            AND NOT ($1::uuid = ANY(whitelisted_users))
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(
                query,
                user_id,
                get_current_ist_time(),
                updated_by
            )
    
    async def remove_user_from_whitelist(self, user_id: str, updated_by: str) -> None:
        """Remove user from whitelist"""
        query = """
            UPDATE rate_limit_config
            SET 
                whitelisted_users = array_remove(whitelisted_users, $1::uuid),
                updated_at = $2,
                updated_by = $3
            WHERE config_id = (SELECT config_id FROM rate_limit_config ORDER BY created_at DESC LIMIT 1)
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(
                query,
                user_id,
                get_current_ist_time(),
                updated_by
            )
    
    async def is_user_whitelisted(self, user_id: str) -> bool:
        """Check if user is whitelisted"""
        query = """
            SELECT $1::uuid = ANY(whitelisted_users)
            FROM rate_limit_config
            ORDER BY created_at DESC LIMIT 1
        """
        
        async with self.db.acquire() as conn:
            return await conn.fetchval(query, user_id) or False
    
    # ========================================================================
    # RATE LIMIT TRACKING
    # ========================================================================
    
    async def get_or_create_tracking(self, user_id: str) -> Dict[str, Any]:
        """Get or create rate limit tracking for user"""
        query = "SELECT * FROM rate_limit_tracking WHERE user_id = $1"
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            
            if row:
                return dict(row)
            
            # Create if doesn't exist
            insert_query = """
                INSERT INTO rate_limit_tracking (user_id)
                VALUES ($1)
                RETURNING *
            """
            row = await conn.fetchrow(insert_query, user_id)
            return dict(row) if row else None
    
    async def increment_counters(
        self,
        user_id: str,
        current_time: datetime
    ) -> Dict[str, Any]:
        """
        Increment rate limit counters with window reset logic
        """
        query = """
            UPDATE rate_limit_tracking
            SET
                -- Minute window (reset if window expired)
                prompts_current_minute = CASE
                    WHEN $2 - minute_window_start >= INTERVAL '1 minute' THEN 1
                    ELSE prompts_current_minute + 1
                END,
                minute_window_start = CASE
                    WHEN $2 - minute_window_start >= INTERVAL '1 minute' THEN $2
                    ELSE minute_window_start
                END,
                
                -- Hour window (reset if window expired)
                prompts_current_hour = CASE
                    WHEN $2 - hour_window_start >= INTERVAL '1 hour' THEN 1
                    ELSE prompts_current_hour + 1
                END,
                hour_window_start = CASE
                    WHEN $2 - hour_window_start >= INTERVAL '1 hour' THEN $2
                    ELSE hour_window_start
                END,
                
                -- 24-hour window (reset if window expired)
                prompts_current_24h = CASE
                    WHEN $2 - window_24h_start >= INTERVAL '24 hours' THEN 1
                    ELSE prompts_current_24h + 1
                END,
                window_24h_start = CASE
                    WHEN $2 - window_24h_start >= INTERVAL '24 hours' THEN $2
                    ELSE window_24h_start
                END,
                
                last_prompt_at = $2,
                updated_at = $2
            WHERE user_id = $1
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, user_id, current_time)
            return dict(row) if row else None
    
    async def get_current_counts(self, user_id: str) -> Dict[str, int]:
        """Get current prompt counts with window checks"""
        current_time = get_current_ist_time()
        
        query = """
            SELECT
                CASE
                    WHEN $2 - minute_window_start >= INTERVAL '1 minute' THEN 0
                    ELSE prompts_current_minute
                END as minute_count,
                CASE
                    WHEN $2 - hour_window_start >= INTERVAL '1 hour' THEN 0
                    ELSE prompts_current_hour
                END as hour_count,
                CASE
                    WHEN $2 - window_24h_start >= INTERVAL '24 hours' THEN 0
                    ELSE prompts_current_24h
                END as day_count
            FROM rate_limit_tracking
            WHERE user_id = $1
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, user_id, current_time)
            
            if row:
                return {
                    'minute': row['minute_count'],
                    'hour': row['hour_count'],
                    'day': row['day_count']
                }
            
            return {'minute': 0, 'hour': 0, 'day': 0}
    
    async def reset_user_counters(self, user_id: str) -> None:
        """Reset all counters for a user (admin action)"""
        current_time = get_current_ist_time()
        
        query = """
            UPDATE rate_limit_tracking
            SET
                prompts_current_minute = 0,
                minute_window_start = $2,
                prompts_current_hour = 0,
                hour_window_start = $2,
                prompts_current_24h = 0,
                window_24h_start = $2,
                updated_at = $2
            WHERE user_id = $1
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(query, user_id, current_time)
    
    # ========================================================================
    # RATE LIMIT VIOLATIONS
    # ========================================================================
    
    async def log_violation(
        self,
        violation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Log a rate limit violation"""
        query = """
            INSERT INTO rate_limit_violations (
                user_id, chat_id, violation_type, limit_value,
                prompts_used, action_taken, user_message,
                ip_address, user_agent
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                query,
                violation_data.get('user_id'),
                violation_data.get('chat_id'),
                violation_data.get('violation_type'),
                violation_data.get('limit_value'),
                violation_data.get('prompts_used'),
                violation_data.get('action_taken', 'blocked'),
                violation_data.get('user_message'),
                violation_data.get('ip_address'),
                violation_data.get('user_agent')
            )
            return dict(row) if row else None
    
    async def get_user_violations(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get violations for a user"""
        query = """
            SELECT * FROM rate_limit_violations
            WHERE user_id = $1
            ORDER BY violated_at DESC
            LIMIT $2
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, user_id, limit)
            return [dict(row) for row in rows]
    
    async def get_all_violations(
        self,
        limit: int = 100,
        offset: int = 0,
        violation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all violations with pagination"""
        
        if violation_type:
            query = """
                SELECT v.*, u.email, u.username
                FROM rate_limit_violations v
                JOIN users u ON v.user_id = u.user_id
                WHERE v.violation_type = $1
                ORDER BY v.violated_at DESC
                LIMIT $2 OFFSET $3
            """
            params = [violation_type, limit, offset]
        else:
            query = """
                SELECT v.*, u.email, u.username
                FROM rate_limit_violations v
                JOIN users u ON v.user_id = u.user_id
                ORDER BY v.violated_at DESC
                LIMIT $1 OFFSET $2
            """
            params = [limit, offset]
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def count_violations(
        self,
        user_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> int:
        """Count violations"""
        
        conditions = []
        params = []
        param_count = 1
        
        if user_id:
            conditions.append(f"user_id = ${param_count}")
            params.append(user_id)
            param_count += 1
        
        if since:
            conditions.append(f"violated_at >= ${param_count}")
            params.append(since)
            param_count += 1
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        query = f"SELECT COUNT(*) FROM rate_limit_violations {where_clause}"
        
        async with self.db.acquire() as conn:
            return await conn.fetchval(query, *params)

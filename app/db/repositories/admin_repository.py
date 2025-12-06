"""
Admin Repository
Database operations for admin table
"""

import asyncpg
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.core.security import get_current_ist_time

logger = logging.getLogger(__name__)


class AdminRepository:
    """Repository for admin database operations"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    # ========================================================================
    # READ
    # ========================================================================
    
    async def get_admin_by_id(self, admin_id: str) -> Optional[Dict[str, Any]]:
        """Get admin by ID"""
        query = "SELECT * FROM admin WHERE admin_id = $1"
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, admin_id)
            return dict(row) if row else None
    
    async def get_admin_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get admin by email"""
        query = "SELECT * FROM admin WHERE email = $1"
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, email.lower())
            return dict(row) if row else None
    
    async def get_admin_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get admin by phone"""
        query = "SELECT * FROM admin WHERE phone = $1"
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, phone)
            return dict(row) if row else None
    
    async def get_all_admins(self) -> List[Dict[str, Any]]:
        """Get all admins"""
        query = "SELECT * FROM admin ORDER BY created_at ASC"
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]
    
    # ========================================================================
    # UPDATE
    # ========================================================================
    
    async def update_last_login(self, admin_id: str) -> None:
        """Update admin's last login timestamp"""
        query = """
            UPDATE admin
            SET last_login_at = $1
            WHERE admin_id = $2
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(query, get_current_ist_time(), admin_id)
    
    async def update_admin_status(
        self,
        admin_id: str,
        is_active: bool
    ) -> Optional[Dict[str, Any]]:
        """Activate or deactivate admin"""
        query = """
            UPDATE admin
            SET is_active = $1
            WHERE admin_id = $2
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, is_active, admin_id)
            return dict(row) if row else None
    
    # ========================================================================
    # ACTIVITY LOG
    # ========================================================================
    
    async def log_activity(
        self,
        activity_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Log admin activity"""
        query = """
            INSERT INTO admin_activity_log (
                admin_id, action, target_type, target_id,
                old_value, new_value, ip_address, user_agent
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                query,
                activity_data.get('admin_id'),
                activity_data.get('action'),
                activity_data.get('target_type'),
                activity_data.get('target_id'),
                activity_data.get('old_value'),
                activity_data.get('new_value'),
                activity_data.get('ip_address'),
                activity_data.get('user_agent')
            )
            return dict(row) if row else None
    
    async def get_activity_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        admin_id: Optional[str] = None,
        action: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get activity logs with filters"""
        
        conditions = []
        params = []
        param_count = 1
        
        if admin_id:
            conditions.append(f"admin_id = ${param_count}")
            params.append(admin_id)
            param_count += 1
        
        if action:
            conditions.append(f"action = ${param_count}")
            params.append(action)
            param_count += 1
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        params.append(limit)
        params.append(offset)
        
        query = f"""
            SELECT l.*, a.email as admin_email, a.full_name as admin_name
            FROM admin_activity_log l
            JOIN admin a ON l.admin_id = a.admin_id
            {where_clause}
            ORDER BY l.performed_at DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def count_activity_logs(
        self,
        admin_id: Optional[str] = None
    ) -> int:
        """Count activity logs"""
        
        if admin_id:
            query = "SELECT COUNT(*) FROM admin_activity_log WHERE admin_id = $1"
            params = [admin_id]
        else:
            query = "SELECT COUNT(*) FROM admin_activity_log"
            params = []
        
        async with self.db.acquire() as conn:
            return await conn.fetchval(query, *params)

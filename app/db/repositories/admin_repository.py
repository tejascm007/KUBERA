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
        query = "SELECT * FROM admins WHERE admin_id = $1"
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, admin_id)
            return dict(row) if row else None
    
    async def get_admin_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get admin by email"""
        query = "SELECT * FROM admins WHERE email = $1"
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, email.lower())
            return dict(row) if row else None
    
    async def get_admin_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get admin by phone"""
        query = "SELECT * FROM admins WHERE phone = $1"
        
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
            UPDATE admins
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
            UPDATE admins
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
            INSERT INTO admin_activity_logs (
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
        import json
        
        conditions = []
        params = []
        param_count = 1
        
        if admin_id:
            conditions.append(f"l.admin_id = ${param_count}")
            params.append(admin_id)
            param_count += 1
        
        if action:
            conditions.append(f"l.action = ${param_count}")
            params.append(action)
            param_count += 1
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        params.append(limit)
        params.append(offset)
        
        query = f"""
            SELECT l.*, 
                   COALESCE(a.email, 'unknown') as admin_email, 
                   COALESCE(a.full_name, 'Unknown Admin') as admin_name
            FROM admin_activity_logs l
            LEFT JOIN admins a ON l.admin_id = a.admin_id
            {where_clause}
            ORDER BY l.performed_at DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
            # Convert results to proper format
            results = []
            for row in rows:
                log_dict = dict(row)
                
                # Convert UUID fields to strings
                if log_dict.get('log_id'):
                    log_dict['log_id'] = str(log_dict['log_id'])
                if log_dict.get('admin_id'):
                    log_dict['admin_id'] = str(log_dict['admin_id'])
                if log_dict.get('target_id'):
                    log_dict['target_id'] = str(log_dict['target_id'])
                
                # Parse JSON strings to dicts
                if log_dict.get('old_value') and isinstance(log_dict['old_value'], str):
                    try:
                        log_dict['old_value'] = json.loads(log_dict['old_value'])
                    except (json.JSONDecodeError, TypeError):
                        log_dict['old_value'] = None
                
                if log_dict.get('new_value') and isinstance(log_dict['new_value'], str):
                    try:
                        log_dict['new_value'] = json.loads(log_dict['new_value'])
                    except (json.JSONDecodeError, TypeError):
                        log_dict['new_value'] = None
                
                results.append(log_dict)
            
            return results
    
    async def count_activity_logs(
        self,
        admin_id: Optional[str] = None
    ) -> int:
        """Count activity logs"""
        
        if admin_id:
            query = "SELECT COUNT(*) FROM admin_activity_logs WHERE admin_id = $1"
            params = [admin_id]
        else:
            query = "SELECT COUNT(*) FROM admin_activity_logs"
            params = []
        
        async with self.db.acquire() as conn:
            return await conn.fetchval(query, *params)
    
    async def log_admin_action(
        self,
        admin_id: str,
        action: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log an admin action"""
        import json
        
        # Convert dicts to JSON strings for storage
        old_value_json = json.dumps(old_value) if old_value else None
        new_value_json = json.dumps(new_value) if new_value else None
        
        query = """
            INSERT INTO admin_activity_logs (
                admin_id, action, target_type, target_id,
                old_value, new_value, ip_address, user_agent
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                query,
                admin_id,
                action,
                target_type,
                target_id,
                old_value_json,
                new_value_json,
                ip_address,
                user_agent
            )
            return dict(row) if row else None

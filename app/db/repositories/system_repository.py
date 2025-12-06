"""
System Repository
Database operations for system_status table
"""

import asyncpg
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from app.core.security import get_current_ist_time

logger = logging.getLogger(__name__)


class SystemRepository:
    """Repository for system status database operations"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    # ========================================================================
    # READ
    # ========================================================================
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        query = "SELECT * FROM system_status ORDER BY created_at DESC LIMIT 1"
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query)
            return dict(row) if row else None
    
    # ========================================================================
    # UPDATE
    # ========================================================================
    
    async def update_system_status(self, status: str) -> Dict[str, Any]:
        """Update system status (running, stopped, maintenance)"""
        query = """
            UPDATE system_status
            SET current_status = $1, updated_at = $2
            WHERE status_id = (SELECT status_id FROM system_status ORDER BY created_at DESC LIMIT 1)
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, status, get_current_ist_time())
            return dict(row) if row else None
    
    async def update_portfolio_report_settings(
        self,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update portfolio report settings"""
        set_clauses = []
        values = []
        param_count = 1
        
        valid_fields = [
            'portfolio_report_frequency',
            'portfolio_report_send_time',
            'portfolio_report_send_day_weekly',
            'portfolio_report_send_day_monthly',
            'portfolio_report_job_id',
            'portfolio_report_next_scheduled'
        ]
        
        for key, value in settings.items():
            if key in valid_fields:
                set_clauses.append(f"{key} = ${param_count}")
                values.append(value)
                param_count += 1
        
        if not set_clauses:
            return await self.get_system_status()
        
        # Add updated_at
        set_clauses.append(f"updated_at = ${param_count}")
        values.append(get_current_ist_time())
        
        query = f"""
            UPDATE system_status
            SET {', '.join(set_clauses)}
            WHERE status_id = (SELECT status_id FROM system_status ORDER BY created_at DESC LIMIT 1)
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            return dict(row) if row else None
    
    async def update_portfolio_report_last_sent(self) -> None:
        """Update portfolio report last sent timestamp"""
        query = """
            UPDATE system_status
            SET 
                portfolio_report_last_sent = $1,
                updated_at = $1
            WHERE status_id = (SELECT status_id FROM system_status ORDER BY created_at DESC LIMIT 1)
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(query, get_current_ist_time())

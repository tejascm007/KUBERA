"""
Email Repository
Database operations for email_log and email_preferences tables
"""

import asyncpg
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.core.security import get_current_ist_time

logger = logging.getLogger(__name__)


class EmailRepository:
    """Repository for email database operations"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    # ========================================================================
    # EMAIL PREFERENCES
    # ========================================================================
    
    async def get_email_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get email preferences for user"""
        query = "SELECT * FROM email_preferences WHERE user_id = $1"
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            
            # If no preferences exist, create default ones
            if not row:
                default_prefs = {
                    'user_id': user_id,
                    'portfolio_reports': True,
                    'security_alerts': True,
                    'rate_limit_notifications': True,
                    'system_notifications': True,
                    'promotional_emails': False
                }
                row = await self.create_email_preferences(default_prefs)
            
            # ========================================================================
            # FIX: Convert UUIDs to strings
            # ========================================================================
            result = dict(row) if row else None
            if result:
                if result.get('preference_id'):
                    result['preference_id'] = str(result['preference_id'])
                if result.get('user_id'):
                    result['user_id'] = str(result['user_id'])
            
            return result



    async def create_email_preferences(
        self,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create default email preferences"""
        query = """
            INSERT INTO email_preferences (
                user_id, portfolio_reports, security_alerts,
                rate_limit_notifications, system_notifications, promotional_emails
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (user_id) DO UPDATE SET
                portfolio_reports = EXCLUDED.portfolio_reports,
                security_alerts = EXCLUDED.security_alerts,
                rate_limit_notifications = EXCLUDED.rate_limit_notifications,
                system_notifications = EXCLUDED.system_notifications,
                promotional_emails = EXCLUDED.promotional_emails
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                query,
                preferences['user_id'],
                preferences.get('portfolio_reports', True),
                preferences.get('security_alerts', True),
                preferences.get('rate_limit_notifications', True),
                preferences.get('system_notifications', True),
                preferences.get('promotional_emails', False)
            )
            
            # ========================================================================
            # FIX: Convert UUIDs to strings
            # ========================================================================
            result = dict(row) if row else None
            if result:
                if result.get('preference_id'):
                    result['preference_id'] = str(result['preference_id'])
                if result.get('user_id'):
                    result['user_id'] = str(result['user_id'])
            
            return result


    
    async def update_email_preferences(
        self,
        user_id: str,
        preferences: Dict[str, bool]
    ) -> Optional[Dict[str, Any]]:
        """Update email preferences"""
        set_clauses = []
        values = []
        param_count = 1
        
        valid_fields = [
            'portfolio_reports',
            'security_alerts',
            'rate_limit_notifications',
            'system_notifications',
            'promotional_emails'
        ]
        
        for key, value in preferences.items():
            if key in valid_fields:
                set_clauses.append(f"{key} = ${param_count}")
                values.append(value)
                param_count += 1
        
        if not set_clauses:
            return await self.get_email_preferences(user_id)
        
        # Add updated_at
        set_clauses.append(f"updated_at = ${param_count}")
        values.append(get_current_ist_time())
        param_count += 1
        
        # Add user_id for WHERE
        values.append(user_id)
        
        query = f"""
            UPDATE email_preferences
            SET {', '.join(set_clauses)}
            WHERE user_id = ${param_count}
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            
            # ========================================================================
            # FIX: Convert UUIDs to strings
            # ========================================================================
            result = dict(row) if row else None
            if result:
                if result.get('preference_id'):
                    result['preference_id'] = str(result['preference_id'])
                if result.get('user_id'):
                    result['user_id'] = str(result['user_id'])
            
            return result

    async def get_users_with_preference(
        self,
        preference_name: str,
        enabled: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all users with specific email preference enabled/disabled"""
        query = f"""
            SELECT u.user_id, u.email, u.full_name
            FROM users u
            JOIN email_preferences ep ON u.user_id = ep.user_id
            WHERE u.account_status = 'active'
            AND ep.{preference_name} = $1
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, enabled)
            return [dict(row) for row in rows]
    
    # ========================================================================
    # EMAIL LOG
    # ========================================================================
    
    async def log_email(
        self,
        recipient_email: str,
        email_type: str,
        subject: str
    ) -> Dict[str, Any]:
        """Log an email that needs to be sent"""
        query = """
            INSERT INTO email_log (recipient_email, email_type, subject, send_status)
            VALUES ($1, $2, $3, 'pending')
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, recipient_email, email_type, subject)
            return dict(row) if row else None
    
    async def mark_email_sent(self, log_id: str) -> None:
        """Mark email as successfully sent"""
        query = """
            UPDATE email_log
            SET send_status = 'sent', sent_at = $1
            WHERE log_id = $2
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(query, get_current_ist_time(), log_id)
    
    async def mark_email_failed(
        self,
        log_id: str,
        error_message: str
    ) -> None:
        """Mark email as failed"""
        query = """
            UPDATE email_log
            SET 
                send_status = 'failed',
                retry_count = retry_count + 1,
                last_error = $1
            WHERE log_id = $2
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(query, error_message, log_id)
    
    async def get_pending_emails(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pending emails to retry"""
        query = """
            SELECT * FROM email_log
            WHERE send_status = 'pending' AND retry_count < 3
            ORDER BY created_at ASC
            LIMIT $1
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, limit)
            return [dict(row) for row in rows]
    
    async def get_email_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        email_type: Optional[str] = None,
        send_status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get email logs with filters"""
        
        conditions = []
        params = []
        param_count = 1
        
        if email_type:
            conditions.append(f"email_type = ${param_count}")
            params.append(email_type)
            param_count += 1
        
        if send_status:
            conditions.append(f"send_status = ${param_count}")
            params.append(send_status)
            param_count += 1
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        params.append(limit)
        params.append(offset)
        
        query = f"""
            SELECT * FROM email_log
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

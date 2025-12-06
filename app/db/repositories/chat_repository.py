"""
Chat Repository
Database operations for chats and messages tables
"""

import asyncpg
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.core.security import get_current_ist_time

logger = logging.getLogger(__name__)


class ChatRepository:
    """Repository for chat and message database operations"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    # ========================================================================
    # CHAT OPERATIONS
    # ========================================================================
    
    async def create_chat(
        self,
        user_id: str,
        chat_name: str = "New Chat"
    ) -> Dict[str, Any]:
        """Create a new chat"""
        query = """
            INSERT INTO chats (user_id, chat_name)
            VALUES ($1, $2)
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, user_id, chat_name)
            return dict(row) if row else None
    
    async def get_chat_by_id(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """Get chat by ID"""
        query = "SELECT * FROM chats WHERE chat_id = $1"
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, chat_id)
            return dict(row) if row else None
    
    async def get_user_chats(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all chats for a user"""
        query = """
            SELECT * FROM chats
            WHERE user_id = $1
            ORDER BY last_message_at DESC NULLS LAST, created_at DESC
            LIMIT $2 OFFSET $3
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, user_id, limit, offset)
            return [dict(row) for row in rows]
    
    async def count_user_chats(self, user_id: str) -> int:
        """Count total chats for user"""
        query = "SELECT COUNT(*) FROM chats WHERE user_id = $1"
        
        async with self.db.acquire() as conn:
            return await conn.fetchval(query, user_id)
    
    async def rename_chat(
        self,
        chat_id: str,
        new_name: str
    ) -> Optional[Dict[str, Any]]:
        """Rename a chat"""
        query = """
            UPDATE chats
            SET chat_name = $1, updated_at = $2
            WHERE chat_id = $3
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                query,
                new_name,
                get_current_ist_time(),
                chat_id
            )
            return dict(row) if row else None
    
    async def increment_prompt_count(self, chat_id: str) -> None:
        """Increment prompt count for a chat"""
        query = """
            UPDATE chats
            SET 
                prompt_count = prompt_count + 1,
                last_message_at = $1,
                updated_at = $1
            WHERE chat_id = $2
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(query, get_current_ist_time(), chat_id)
    
    async def get_chat_prompt_count(self, chat_id: str) -> int:
        """Get current prompt count for a chat"""
        query = "SELECT prompt_count FROM chats WHERE chat_id = $1"
        
        async with self.db.acquire() as conn:
            return await conn.fetchval(query, chat_id) or 0
    
    async def delete_chat(self, chat_id: str) -> bool:
        """Delete a chat (cascades to messages)"""
        query = "DELETE FROM chats WHERE chat_id = $1"
        
        async with self.db.acquire() as conn:
            result = await conn.execute(query, chat_id)
            return result == "DELETE 1"
    
    # ========================================================================
    # MESSAGE OPERATIONS
    # ========================================================================
    
    async def create_message(
        self,
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new message"""
        query = """
            INSERT INTO messages (
                chat_id, user_id, user_message, assistant_response,
                tokens_used, mcp_servers_called, mcp_tools_used,
                charts_generated, processing_time_ms, llm_model
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                query,
                message_data.get('chat_id'),
                message_data.get('user_id'),
                message_data.get('user_message'),
                message_data.get('assistant_response'),
                message_data.get('tokens_used'),
                message_data.get('mcp_servers_called', []),
                message_data.get('mcp_tools_used', []),
                message_data.get('charts_generated', 0),
                message_data.get('processing_time_ms'),
                message_data.get('llm_model')
            )
            return dict(row) if row else None
    
    async def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get message by ID"""
        query = "SELECT * FROM messages WHERE message_id = $1"
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, message_id)
            return dict(row) if row else None
    
    async def get_chat_messages(
        self,
        chat_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all messages for a chat"""
        query = """
            SELECT * FROM messages
            WHERE chat_id = $1
            ORDER BY created_at ASC
            LIMIT $2 OFFSET $3
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, chat_id, limit, offset)
            return [dict(row) for row in rows]
    
    async def count_chat_messages(self, chat_id: str) -> int:
        """Count total messages in a chat"""
        query = "SELECT COUNT(*) FROM messages WHERE chat_id = $1"
        
        async with self.db.acquire() as conn:
            return await conn.fetchval(query, chat_id)
    
    async def update_message_response(
        self,
        message_id: str,
        assistant_response: str,
        tokens_used: Optional[int] = None,
        processing_time_ms: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Update message with assistant response"""
        query = """
            UPDATE messages
            SET 
                assistant_response = $1,
                tokens_used = $2,
                processing_time_ms = $3
            WHERE message_id = $4
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                query,
                assistant_response,
                tokens_used,
                processing_time_ms,
                message_id
            )
            return dict(row) if row else None
    
    async def delete_message(self, message_id: str) -> bool:
        """Delete a message"""
        query = "DELETE FROM messages WHERE message_id = $1"
        
        async with self.db.acquire() as conn:
            result = await conn.execute(query, message_id)
            return result == "DELETE 1"
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    async def get_total_messages_count(self) -> int:
        """Get total messages across all users"""
        query = "SELECT COUNT(*) FROM messages"
        
        async with self.db.acquire() as conn:
            return await conn.fetchval(query)
    
    async def get_user_message_count(self, user_id: str) -> int:
        """Get total messages for a user"""
        query = "SELECT COUNT(*) FROM messages WHERE user_id = $1"
        
        async with self.db.acquire() as conn:
            return await conn.fetchval(query, user_id)
    
    async def get_user_prompt_count(
        self,
        user_id: str,
        since: Optional[datetime] = None
    ) -> int:
        """Get total prompts for a user (optionally since a date)"""
        
        if since:
            query = """
                SELECT COUNT(*) FROM messages
                WHERE user_id = $1 AND created_at >= $2
            """
            params = [user_id, since]
        else:
            query = "SELECT COUNT(*) FROM messages WHERE user_id = $1"
            params = [user_id]
        
        async with self.db.acquire() as conn:
            return await conn.fetchval(query, *params)

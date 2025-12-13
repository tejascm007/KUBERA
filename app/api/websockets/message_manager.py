"""
MessageManager
Handles database operations for chat messages
"""

import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MessageManager:
    """Manages message persistence"""
    
    def __init__(self, db_pool, user_id: str, chat_id: str):
        self.db_pool = db_pool
        self.user_id = user_id
        self.chat_id = chat_id
    
    async def save_user_message(self, message_id: str, content: str):
        """Save user message to database"""
        query = """
            INSERT INTO messages 
            (message_id, chat_id, user_id, user_message, created_at)
            VALUES ($1, $2, $3, $4, NOW())
        """
        await self.db_pool.execute(query, message_id, self.chat_id, self.user_id, content)
        logger.info(f"Saved user message {message_id}")
    
    async def save_assistant_response(self, message_id: str, response: str,
                                     tokens_used: int, processing_time_ms: int,
                                     tools_used: list, chart_url: str = None):
        """Save assistant response to database"""
        query = """
            UPDATE messages
            SET 
                assistant_response = $1,
                tokens_used = $2,
                processing_time_ms = $3,
                mcp_tools_used = $4,
                chart_url = $5,
                response_completed_at = NOW()
            WHERE message_id = $6
        """
        logger.info(f"Saving chart_url to DB: {chart_url[:50] if chart_url else 'None'}")
        await self.db_pool.execute(
            query,
            response,
            tokens_used,
            processing_time_ms,
            tools_used,
            chart_url,
            message_id
        )
        logger.info(f"Saved assistant response for message {message_id}")
    
    async def get_chat_history(self, limit: int = 50):
        """Get chat history for context"""
        query = """
            SELECT user_message, assistant_response
            FROM messages
            WHERE chat_id = $1
            ORDER BY created_at ASC
            LIMIT $2
        """
        messages = await self.db_pool.fetch(query, self.chat_id, limit)
        return messages

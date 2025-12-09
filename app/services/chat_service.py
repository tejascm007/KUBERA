"""
Chat Service
Business logic for chat and message management
"""

from typing import Dict, Any, List
import logging

from app.db.repositories.chat_repository import ChatRepository
from app.exceptions.custom_exceptions import ChatNotFoundException

logger = logging.getLogger(__name__)


class ChatService:
    """Chat management service"""
    
    def __init__(self, db_pool):
        self.db = db_pool
        self.chat_repo = ChatRepository(db_pool)
    
    # ========================================================================
    # CHAT OPERATIONS
    # ========================================================================
    
    async def create_chat(
        self,
        user_id: str,
        chat_name: str = "New Chat"
    ) -> Dict[str, Any]:
        """
        Create a new chat
        
        Args:
            user_id: User UUID
            chat_name: Chat name
        
        Returns:
            Created chat
        """
        chat = await self.chat_repo.create_chat(user_id, chat_name)

        # ========================================================================
        # FIX: Convert UUIDs to strings
        # ========================================================================
        if chat:
            if chat.get('chat_id'):
                chat['chat_id'] = str(chat['chat_id'])
            if chat.get('user_id'):
                chat['user_id'] = str(chat['user_id'])
        
        
        
        logger.info(f"Chat created for user {user_id}: {chat['chat_id']}")
        
        return chat
    
    async def get_user_chats(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get all chats for a user
        
        Args:
            user_id: User UUID
            limit: Number of chats
            offset: Offset for pagination
        
        Returns:
            List of chats with count
        """
        chats = await self.chat_repo.get_user_chats(user_id, limit, offset)
        
        # ========================================================================
        # FIX: Convert UUIDs to strings for all chats
        # ========================================================================
        for chat in chats:
            if chat.get('chat_id'):
                chat['chat_id'] = str(chat['chat_id'])
            if chat.get('user_id'):
                chat['user_id'] = str(chat['user_id'])
        
        total = await self.chat_repo.count_user_chats(user_id)
        
        return {
            "success": True,
            "total_chats": total,
            "chats": chats
        }

    
    async def get_chat_with_messages(
        self,
        chat_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get chat with all messages
        
        Args:
            chat_id: Chat UUID
            limit: Number of messages
            offset: Offset for pagination
        
        Returns:
            Chat with messages
        
        Raises:
            ChatNotFoundException: Chat not found
        """
        chat = await self.chat_repo.get_chat_by_id(chat_id)
        
        if not chat:
            raise ChatNotFoundException(chat_id)
        
        # ========================================================================
        # FIX: Convert UUIDs to strings for chat
        # ========================================================================
        if chat.get('chat_id'):
            chat['chat_id'] = str(chat['chat_id'])
        if chat.get('user_id'):
            chat['user_id'] = str(chat['user_id'])
        
        messages = await self.chat_repo.get_chat_messages(chat_id, limit, offset)
        
        # ========================================================================
        # FIX: Convert UUIDs to strings for messages
        # ========================================================================
        for message in messages:
            if message.get('message_id'):
                message['message_id'] = str(message['message_id'])
            if message.get('chat_id'):
                message['chat_id'] = str(message['chat_id'])
            if message.get('user_id'):
                message['user_id'] = str(message['user_id'])
        
        total_messages = await self.chat_repo.count_chat_messages(chat_id)
        
        return {
            "success": True,
            "chat": chat,
            "messages": messages,
            "total_messages": total_messages
        }

    
    async def rename_chat(
        self,
        chat_id: str,
        new_name: str
    ) -> Dict[str, Any]:
        """
        Rename a chat
        
        Args:
            chat_id: Chat UUID
            new_name: New chat name
        
        Returns:
            Updated chat
        """
        chat = await self.chat_repo.rename_chat(chat_id, new_name)
        
        # ========================================================================
        # FIX: Convert UUIDs to strings
        # ========================================================================
        if chat:
            if chat.get('chat_id'):
                chat['chat_id'] = str(chat['chat_id'])
            if chat.get('user_id'):
                chat['user_id'] = str(chat['user_id'])
        
        logger.info(f"Chat renamed: {chat_id}")
        
        return chat

    
    async def delete_chat(self, chat_id: str) -> bool:
        """
        Delete a chat (cascades to messages)
        
        Args:
            chat_id: Chat UUID
        
        Returns:
            True if deleted
        """
        deleted = await self.chat_repo.delete_chat(chat_id)
        
        if deleted:
            logger.info(f"Chat deleted: {chat_id}")
        
        return deleted
    
    # ========================================================================
    # MESSAGE OPERATIONS
    # ========================================================================
    
    async def create_message(
        self,
        chat_id: str,
        user_id: str,
        user_message: str
    ) -> Dict[str, Any]:
        """
        Create a new message (user prompt)
        
        Args:
            chat_id: Chat UUID
            user_id: User UUID
            user_message: User's message
        
        Returns:
            Created message
        """
        message_data = {
            'chat_id': chat_id,
            'user_id': user_id,
            'user_message': user_message
        }
        
        message = await self.chat_repo.create_message(message_data)
        
        # Increment chat prompt count
        await self.chat_repo.increment_prompt_count(chat_id)
        
        logger.info(f"Message created in chat {chat_id}")
        
        return message
    
    async def update_message_response(
        self,
        message_id: str,
        assistant_response: str,
        tokens_used: int = None,
        processing_time_ms: int = None,
        mcp_servers_called: List[str] = None,
        mcp_tools_used: List[str] = None,
        charts_generated: int = 0,
        llm_model: str = None
    ) -> Dict[str, Any]:
        """
        Update message with assistant response and metadata
        
        Args:
            message_id: Message UUID
            assistant_response: AI response
            tokens_used: Tokens consumed
            processing_time_ms: Processing time
            mcp_servers_called: List of MCP servers used
            mcp_tools_used: List of MCP tools called
            charts_generated: Number of charts generated
            llm_model: LLM model used
        
        Returns:
            Updated message
        """
        message = await self.chat_repo.update_message_response(
            message_id,
            assistant_response,
            tokens_used,
            processing_time_ms
        )
        
        logger.info(f"Message response updated: {message_id}")
        
        return message
    
    async def get_chat_prompt_count(self, chat_id: str) -> int:
        """Get current prompt count for a chat"""
        return await self.chat_repo.get_chat_prompt_count(chat_id)

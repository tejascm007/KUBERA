"""
ChatWebSocketHandler
Manages individual chat WebSocket connections
Handles message receiving, LLM processing, and response streaming
"""

import json
import logging
import uuid
from datetime import datetime
from fastapi import WebSocket
from app.api.websockets.message_manager import MessageManager
from app.api.websockets.llm_service import LLMService
from app.models.rate_limit import RateLimiter

logger = logging.getLogger(__name__)


class ChatWebSocketHandler:
    """
    Handles individual WebSocket chat connections
    
    Features:
    - Message receiving and parsing
    - LLM integration with streaming
    - Rate limit checking
    - Message persistence
    - Error handling
    """
    
    def __init__(self, websocket: WebSocket, user_id: str, email: str, 
                 chat_id: str, db_pool):
        """
        Initialize WebSocket handler
        
        Args:
            websocket: FastAPI WebSocket connection
            user_id: User's UUID
            email: User's email
            chat_id: Chat session UUID
            db_pool: Database connection pool
        """
        self.websocket = websocket
        self.user_id = user_id
        self.email = email
        self.chat_id = chat_id
        self.db_pool = db_pool
        
        # Initialize services
        self.message_manager = MessageManager(db_pool, user_id, chat_id)
        self.llm_service = LLMService()
        self.rate_limiter = RateLimiter(db_pool, user_id)
    
    async def connect(self):
        """Accept WebSocket connection and send welcome message"""
        try:
            logger.info(f"WebSocket accepted for user {self.user_id}, chat {self.chat_id}")
            
            # Send connection confirmation
            await self.websocket.send_json({
                "type": "connected",
                "chat_id": self.chat_id,
                "user_id": self.user_id,
                "message": "Connected to chat successfully",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Send current rate limit info
            rate_info = await self.rate_limiter.get_current_usage()
            await self.websocket.send_json({
                "type": "rate_limit_info",
                "current": rate_info["current"],
                "limits": rate_info["limits"]
            })
            
        except Exception as e:
            logger.error(f"Error accepting WebSocket: {str(e)}")
            raise
    
    async def listen(self):
        """
        Listen for incoming messages and process them
        Continuously receives messages until connection closes
        """
        try:
            while True:
                #   RECEIVE MESSAGE FROM CLIENT
                data = await self.websocket.receive_text()
                
                try:
                    message_data = json.loads(data)
                except json.JSONDecodeError:
                    await self.send_error("Invalid JSON format")
                    continue
                
                #   PROCESS MESSAGE
                await self.process_message(message_data)
                
        except Exception as e:
            logger.error(f"Error in listen loop: {str(e)}")
            await self.send_error(f"Error: {str(e)}")
    
    async def process_message(self, message_data: dict):
        """
        Process incoming message
        - Check format
        - Validate rate limits
        - Save to database
        - Call LLM
        - Stream response
        """
        try:
            message_type = message_data.get("type", "message")
            
            if message_type == "message":
                await self.handle_chat_message(message_data)
            elif message_type == "typing":
                await self.handle_typing_notification(message_data)
            else:
                await self.send_error(f"Unknown message type: {message_type}")
        
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            await self.send_error(f"Processing error: {str(e)}")
    
    async def handle_chat_message(self, message_data: dict):
        """Handle actual chat message"""
        
        user_message = message_data.get("content", "").strip()
        
        if not user_message:
            await self.send_error("Message cannot be empty")
            return
        
        logger.info(f"Chat message from {self.user_id}: {user_message[:100]}")
        
        #   CHECK RATE LIMITS
        rate_check = await self.rate_limiter.check_limits()
        
        if not rate_check["allowed"]:
            await self.websocket.send_json({
                "type": "rate_limit_exceeded",
                "error": rate_check["error"],
                "details": rate_check["details"]
            })
            logger.warning(f"Rate limit exceeded for user {self.user_id}")
            return
        
        #   SAVE MESSAGE TO DATABASE
        message_id = str(uuid.uuid4())
        try:
            await self.message_manager.save_user_message(
                message_id=message_id,
                content=user_message
            )
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            await self.send_error("Failed to save message")
            return
        
        #  CALL LLM AND STREAM RESPONSE
        await self.stream_llm_response(message_id, user_message)
    
    async def stream_llm_response(self, message_id: str, user_message: str):
        """Stream LLM response in real-time"""
        
        try:
            # Send typing indicator
            await self.websocket.send_json({
                "type": "typing",
                "user_id": "assistant"
            })
            
            #   USE THE NEW LLMSERVICE
            response_text = ""
            tools_used = []
            tokens_used = 0
            processing_start = datetime.utcnow()
            
            async for chunk in self.llm_service.stream_response(
                user_message=user_message,
                chat_id=self.chat_id,
                user_id=self.user_id,
                chat_history=await self.message_manager.get_chat_history()
            ):
                # Handle different chunk types
                if chunk["type"] == "text_chunk":
                    response_text += chunk["content"]
                    
                    # Stream text chunk to client
                    await self.websocket.send_json({
                        "type": "text_chunk",
                        "content": chunk["content"],
                        "message_id": message_id
                    })
                
                elif chunk["type"] == "tool_executing":
                    # Notify client of tool execution
                    await self.websocket.send_json({
                        "type": "tool_executing",
                        "tool_name": chunk["tool_name"],
                        "tool_id": chunk["tool_id"],
                        "message_id": message_id
                    })
                
                elif chunk["type"] == "tool_result":
                    # Tool completed
                    await self.websocket.send_json({
                        "type": "tool_complete",
                        "tool_name": chunk["tool_name"],
                        "message_id": message_id
                    })
                
                elif chunk["type"] == "message_complete":
                    tokens_used = chunk["metadata"].get("tokens_used", 0)
                    tools_used = chunk["metadata"].get("tools_used", [])
            
            #   SAVE ASSISTANT RESPONSE
            processing_time = (datetime.utcnow() - processing_start).total_seconds() * 1000
            
            try:
                await self.message_manager.save_assistant_response(
                    message_id=message_id,
                    response=response_text,
                    tokens_used=tokens_used,
                    processing_time_ms=int(processing_time),
                    tools_used=tools_used
                )
            except Exception as e:
                logger.error(f"Error saving response: {str(e)}")
            
            #   SEND COMPLETION MESSAGE
            await self.websocket.send_json({
                "type": "message_complete",
                "message_id": message_id,
                "metadata": {
                    "tokens_used": tokens_used,
                    "tools_used": tools_used,
                    "processing_time_ms": int(processing_time)
                }
            })
            
            logger.info(f"Message {message_id} completed. Tokens: {tokens_used}, Tools: {len(tools_used)}")
        
        except Exception as e:
            logger.error(f"Error streaming response: {str(e)}")
            await self.send_error(f"LLM error: {str(e)}")

    
    async def handle_typing_notification(self, message_data: dict):
        """Handle typing notification (optional feature)"""
        # Broadcast typing status to other users in same chat
        typing_data = {
            "type": "typing",
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        logger.debug(f"User {self.user_id} typing in chat {self.chat_id}")
    
    async def send_error(self, error_message: str):
        """Send error message to client"""
        try:
            await self.websocket.send_json({
                "type": "error",
                "error": error_message,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Error sending error message: {str(e)}")
    
    async def disconnect(self):
        """Cleanup when connection closes"""
        try:
            logger.info(f"Disconnecting user {self.user_id} from chat {self.chat_id}")
            
            # Update chat last activity
            query = """
                UPDATE chats 
                SET last_message_at = NOW(), updated_at = NOW()
                WHERE chat_id = $1
            """
            await self.db_pool.execute(query, self.chat_id)
            
            logger.info(f"Chat {self.chat_id} cleanup completed")
        
        except Exception as e:
            logger.error(f"Error during disconnect cleanup: {str(e)}")

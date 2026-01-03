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
from app.websocket.response_streamer import ResponseStreamer

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
        self.llm_service = LLMService(db_pool)  # Pass db_pool for portfolio access
        self.rate_limiter = RateLimiter(db_pool, user_id)
        
        # Initialize response streamer for cleaner streaming
        self.streamer = ResponseStreamer(websocket)
    
    def _generate_chat_title(self, message: str, max_length: int = 35) -> str:
        """
        Generate chat title from first message
        Truncates at word boundary and adds ellipsis if needed
        """
        # Clean and normalize the message
        title = message.strip()
        
        # If message is short enough, use as-is
        if len(title) <= max_length:
            return title
        
        # Truncate at word boundary
        truncated = title[:max_length].rsplit(' ', 1)[0]
        
        # If we couldn't find a space, just hard truncate
        if not truncated:
            truncated = title[:max_length]
        
        return truncated + "..."
    
    async def _send_rate_limit_email(self, violation_type: str, limit: int):
        """
        Send rate limit exceeded email notification in background
        This runs in a separate task to not block the WebSocket response
        """
        try:
            from app.services.email_service import EmailService
            
            email_service = EmailService(self.db_pool)
            await email_service.send_rate_limit_violation_email(
                user_id=self.user_id,
                violation_type=violation_type,
                limit=limit
            )
            logger.info(f"Rate limit email sent to user {self.user_id}")
        except Exception as e:
            # Don't raise - this is a background task, just log
            logger.error(f"Failed to send rate limit email: {str(e)}")
    
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
            
            # Send current rate limit info using streamer
            rate_info = await self.rate_limiter.get_current_usage()
            await self.streamer.stream_rate_limit_info(
                current_usage=rate_info["current"],
                limits=rate_info["limits"]
            )
            
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
            elif message_type == "ping":
                # Respond to heartbeat ping with pong
                await self.websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                await self.send_error(f"Unknown message type: {message_type}")
        
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            await self.send_error(f"Processing error: {str(e)}")
    
    async def handle_chat_message(self, message_data: dict):
        """Handle actual chat message"""
        
        # ========================================================================
        # CHECK SYSTEM STATUS - Block prompts when system is stopped
        # ========================================================================
        try:
            from app.db.repositories.system_repository import SystemRepository
            system_repo = SystemRepository(self.db_pool)
            system_status = await system_repo.get_system_status()
            
            if system_status and system_status.get('current_status') != 'running':
                await self.websocket.send_json({
                    "type": "system_maintenance",
                    "error": "System is currently under maintenance. Chat prompts are temporarily disabled.",
                    "status": system_status.get('current_status', 'stopped')
                })
                logger.warning(f"Chat blocked for user {self.user_id} - system status: {system_status.get('current_status')}")
                return
        except Exception as e:
            logger.error(f"Error checking system status: {e}")
            # Don't block on error - allow prompts if status check fails
        
        # Accept message from either 'content' or 'message' field (frontend uses 'message')
        user_message = (message_data.get("content") or message_data.get("message") or "").strip()
        
        if not user_message:
            await self.send_error("Message cannot be empty")
            return
        
        logger.info(f"Chat message from {self.user_id}: {user_message[:100]}")
        
        #   CHECK RATE LIMITS
        rate_check = await self.rate_limiter.check_limits()
        
        if not rate_check["allowed"]:
            await self.streamer.stream_rate_limit_exceeded(
                error=rate_check["error"],
                details=rate_check["details"]
            )
            logger.warning(f"Rate limit exceeded for user {self.user_id}")
            
            # Send email notification in background (non-blocking)
            import asyncio
            asyncio.create_task(self._send_rate_limit_email(
                violation_type=rate_check["details"].get("violation_type", "unknown"),
                limit=rate_check["details"].get("limit", 0)
            ))
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
            # Send thinking indicator
            await self.streamer.stream_thinking("Generating response...")
            
            #   USE THE NEW LLMSERVICE
            response_text = ""
            tools_used = []
            tokens_used = 0
            chart_url = None  # Track chart URL from visualization tools
            chart_html = None  # Track chart HTML for direct rendering
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
                    
                    # Stream text chunk to client using streamer
                    await self.streamer.stream_text_chunk(chunk["content"])
                
                elif chunk["type"] == "tool_executing":
                    # Notify client of tool execution
                    await self.streamer.stream_tool_executing(
                        tool_name=chunk["tool_name"],
                        tool_id=chunk["tool_id"]
                    )
                
                elif chunk["type"] == "tool_result":
                    # Tool completed
                    await self.streamer.stream_tool_complete(
                        tool_name=chunk["tool_name"],
                        tool_id=chunk["tool_id"]
                    )
                
                elif chunk["type"] == "message_complete":
                    tokens_used = chunk["metadata"].get("tokens_used", 0)
                    tools_used = chunk["metadata"].get("tools_used", [])
                    chart_url = chunk["metadata"].get("chart_url")
                    chart_html = chunk["metadata"].get("chart_html")  # Chart HTML for direct rendering
                    # Debug: Log chart data received
                    logger.info(f"Message complete - chart_url: {chart_url[:50] if chart_url else 'None'}...")
                    logger.info(f"Message complete - chart_html size: {len(chart_html) if chart_html else 0} bytes")
            
            #   SAVE ASSISTANT RESPONSE
            processing_time = (datetime.utcnow() - processing_start).total_seconds() * 1000
            
            try:
                logger.info(f"Saving response - chart_url to save: {chart_url[:50] if chart_url else 'None'}")
                await self.message_manager.save_assistant_response(
                    message_id=message_id,
                    response=response_text,
                    tokens_used=tokens_used,
                    processing_time_ms=int(processing_time),
                    tools_used=tools_used,
                    chart_url=chart_url  # Save chart URL for reload
                )
            except Exception as e:
                logger.error(f"Error saving response: {str(e)}")
            
            #   SEND COMPLETION MESSAGE using streamer
            await self.streamer.stream_complete(
                message_id=message_id,
                metadata={
                    "tokens_used": tokens_used,
                    "tools_used": tools_used,
                    "processing_time_ms": int(processing_time),
                    "chart_url": chart_url,  # Include chart URL for frontend
                    "chart_html": chart_html  # Include chart HTML for direct rendering
                }
            )
            
            # Clear streamer buffer for next message
            self.streamer.clear_buffer()
            
            logger.info(f"Message {message_id} completed. Tokens: {tokens_used}, Tools: {len(tools_used)}")
            
            # ========================================================================
            # AUTO-NAME CHAT FROM FIRST MESSAGE
            # ========================================================================
            try:
                from app.db.repositories.chat_repository import ChatRepository
                chat_repo = ChatRepository(self.db_pool)
                
                # Check if this is the first message in the chat
                message_count = await chat_repo.count_chat_messages(self.chat_id)
                
                if message_count == 1:
                    # Generate title from first message (truncate to 35 chars at word boundary)
                    title = self._generate_chat_title(user_message)
                    
                    # Update chat name in database
                    await chat_repo.rename_chat(self.chat_id, title)
                    
                    # Notify frontend of the new name
                    await self.websocket.send_json({
                        "type": "chat_renamed",
                        "chat_id": self.chat_id,
                        "new_name": title
                    })
                    
                    logger.info(f"Chat {self.chat_id} auto-named to: {title}")
            except Exception as e:
                logger.error(f"Error auto-naming chat: {str(e)}")
        
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

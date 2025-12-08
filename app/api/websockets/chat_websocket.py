"""
WebSocket Handler for Real-Time Chat Streaming
Handles bidirectional communication for chat with streaming responses
"""

import json
import logging
from typing import Dict, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from app.mcp.config import MCPServerConfig
from app.mcp.llm_integration import llm_mcp_orchestrator
from app.services.chat_service import ChatService
from app.services.rate_limit_service import RateLimitService
from app.exceptions.custom_exceptions import RateLimitException

logger = logging.getLogger(__name__)


class ChatWebSocketHandler:
    """WebSocket handler for real-time chat"""
    
    def __init__(self, websocket: WebSocket, user_id: str, db_pool):
        self.websocket = websocket
        self.user_id = user_id
        self.db_pool = db_pool
        self.chat_service = ChatService(db_pool)
        self.rate_limit_service = RateLimitService(db_pool)
        self.is_connected = False
    
    async def connect(self):
        """Accept WebSocket connection"""
        await self.websocket.accept()
        self.is_connected = True
        
        await self.send_message({
            "type": "connection",
            "status": "connected",
            "user_id": self.user_id,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f" WebSocket connected: user {self.user_id}")
    
    async def disconnect(self):
        """Close WebSocket connection"""
        if self.is_connected and self.websocket.client_state == WebSocketState.CONNECTED:
            await self.websocket.close()
        self.is_connected = False
        logger.info(f" WebSocket disconnected: user {self.user_id}")
    
    async def send_message(self, message: Dict[str, Any]):
        """Send message to client"""
        if self.is_connected and self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                self.is_connected = False
    
    async def handle_chat_message(self, data: Dict[str, Any]):
        """
        Handle incoming chat message and stream response
        
        Expected data:
        {
            "type": "message",
            "chat_id": "uuid",
            "message": "Analyze INFY stock"
        }
        """
        try:
            chat_id = data.get("chat_id")
            user_message = data.get("message")
            
            if not chat_id or not user_message:
                await self.send_message({
                    "type": "error",
                    "error": "Missing chat_id or message"
                })
                return
            
            # ================================================================
            # STEP 1: CHECK RATE LIMITS (4-LEVEL FAIL-FAST)
            # ================================================================
            try:
                rate_limit_result = await self.rate_limit_service.check_rate_limits(
                    user_id=self.user_id,
                    chat_id=chat_id,
                    user_message=user_message
                )
                
                # Send rate limit info
                await self.send_message({
                    "type": "rate_limit_info",
                    "current_usage": rate_limit_result["current_usage"],
                    "limits": rate_limit_result["limits"]
                })
                
            except RateLimitException as e:
                await self.send_message({
                    "type": "rate_limit_exceeded",
                    "error": e.message,
                    "details": e.details
                })
                return
            
            # ================================================================
            # STEP 2: CREATE MESSAGE IN DATABASE
            # ================================================================
            message_record = await self.chat_service.create_message(
                chat_id=chat_id,
                user_id=self.user_id,
                user_message=user_message
            )
            
            message_id = message_record['message_id']
            
            # Send acknowledgment
            await self.send_message({
                "type": "message_received",
                "message_id": message_id,
                "chat_id": chat_id,
                "timestamp": datetime.now().isoformat()
            })
            
            # ================================================================
            # STEP 3: GET CONVERSATION HISTORY
            # ================================================================
            chat_data = await self.chat_service.get_chat_with_messages(chat_id, limit=10)
            conversation_history = []
            
            # Build conversation history (exclude current message)
            for msg in reversed(chat_data['messages'][:-1]):
                if msg['user_message']:
                    conversation_history.append({
                        "role": "user",
                        "content": msg['user_message']
                    })
                if msg['assistant_response']:
                    conversation_history.append({
                        "role": "assistant",
                        "content": msg['assistant_response']
                    })
            
            # ================================================================
            # STEP 4: STREAM RESPONSE FROM LLM + MCP
            # ================================================================
            full_response = ""
            tools_used = []
            start_time = datetime.now()
            
            async for chunk in llm_mcp_orchestrator.process_with_streaming(
                user_message=user_message,
                conversation_history=conversation_history
            ):
                # Forward all chunks to client
                await self.send_message(chunk)
                
                # Track data for database
                if chunk["type"] == "text_chunk":
                    full_response += chunk["content"]
                
                elif chunk["type"] == "tool_complete":
                    if chunk["tool_name"] not in tools_used:
                        tools_used.append(chunk["tool_name"])
                
                elif chunk["type"] == "complete":
                    # Calculate processing time
                    end_time = datetime.now()
                    processing_time = int((end_time - start_time).total_seconds() * 1000)
                    
                    # ========================================================
                    # STEP 5: UPDATE MESSAGE IN DATABASE
                    # ========================================================
                    await self.chat_service.update_message_response(
                        message_id=message_id,
                        assistant_response=full_response,
                        tokens_used=chunk.get("tokens_used"),
                        processing_time_ms=processing_time,
                        mcp_servers_called=self._get_servers_from_tools(tools_used),
                        mcp_tools_used=tools_used,
                        llm_model=chunk.get("model", "claude-3-5-sonnet")
                    )
                    
                    # Send final metadata
                    await self.send_message({
                        "type": "message_complete",
                        "message_id": message_id,
                        "metadata": {
                            "tokens_used": chunk.get("tokens_used"),
                            "tools_used": tools_used,
                            "servers_called": self._get_servers_from_tools(tools_used),
                            "processing_time_ms": processing_time,
                            "iterations": chunk.get("iterations", 1)
                        }
                    })
                
                elif chunk["type"] == "error":
                    await self.send_message({
                        "type": "error",
                        "error": chunk["error"],
                        "message_id": message_id
                    })
                    break
        
        except Exception as e:
            logger.error(f"Error handling chat message: {e}", exc_info=True)
            await self.send_message({
                "type": "error",
                "error": str(e)
            })
    
    def _get_servers_from_tools(self, tools_used: list) -> list:
        """Map tools to their respective servers"""
        
        servers = set()
        
        for tool_name in tools_used:
            for server_name, config in MCPServerConfig.SERVERS.items():
                if tool_name in config.get("tools", []):
                    servers.add(server_name)
                    break
        
        return list(servers)
    
    async def handle_ping(self):
        """Handle ping message"""
        await self.send_message({
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        })
    
    async def listen(self):
        """Listen for incoming messages"""
        try:
            while self.is_connected:
                # Receive message
                data = await self.websocket.receive_json()
                
                # Handle different message types
                message_type = data.get("type")
                
                if message_type == "message":
                    await self.handle_chat_message(data)
                
                elif message_type == "ping":
                    await self.handle_ping()
                
                else:
                    await self.send_message({
                        "type": "error",
                        "error": f"Unknown message type: {message_type}"
                    })
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected normally: user {self.user_id}")
        
        except Exception as e:
            logger.error(f"WebSocket error: {e}", exc_info=True)
        
        finally:
            await self.disconnect()

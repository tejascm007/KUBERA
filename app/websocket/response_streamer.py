"""
WebSocket Response Streamer
Handles streaming of LLM responses and tool executions to WebSocket clients
"""

import logging
from typing import Dict, Any, AsyncGenerator
from datetime import datetime
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ResponseStreamer:
    """
    Streams LLM responses and tool executions to WebSocket clients
    Handles chunking, formatting, and error handling
    """
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.message_buffer = []
        self.chunk_count = 0
    
    # ========================================================================
    # STREAMING METHODS
    # ========================================================================
    
    async def stream_text_chunk(self, content: str):
        """
        Stream a text chunk to client
        
        Args:
            content: Text content to stream
        """
        try:
            await self.websocket.send_json({
                "type": "text_chunk",
                "content": content,
                "chunk_id": self.chunk_count,
                "timestamp": datetime.now().isoformat()
            })
            
            self.chunk_count += 1
            self.message_buffer.append(content)
            
        except Exception as e:
            logger.error(f"Error streaming text chunk: {e}")
            raise
    
    async def stream_tool_call_start(self, tool_name: str, tool_id: str):
        """
        Notify client that a tool call is starting
        
        Args:
            tool_name: Name of the tool
            tool_id: Tool call ID
        """
        try:
            await self.websocket.send_json({
                "type": "tool_call_start",
                "tool_name": tool_name,
                "tool_id": tool_id,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error streaming tool call start: {e}")
            raise
    
    async def stream_tool_executing(self, tool_name: str, tool_id: str):
        """
        Notify client that a tool is executing
        
        Args:
            tool_name: Name of the tool
            tool_id: Tool call ID
        """
        try:
            await self.websocket.send_json({
                "type": "tool_executing",
                "tool_name": tool_name,
                "tool_id": tool_id,
                "status": "executing",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error streaming tool executing: {e}")
            raise
    
    async def stream_tool_complete(
        self,
        tool_name: str,
        tool_id: str,
        result: Any = None,
        include_result: bool = False
    ):
        """
        Notify client that a tool execution completed
        
        Args:
            tool_name: Name of the tool
            tool_id: Tool call ID
            result: Tool execution result (optional)
            include_result: Whether to include result in message
        """
        try:
            message = {
                "type": "tool_complete",
                "tool_name": tool_name,
                "tool_id": tool_id,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            
            if include_result and result:
                message["result"] = result
            
            await self.websocket.send_json(message)
            
        except Exception as e:
            logger.error(f"Error streaming tool complete: {e}")
            raise
    
    async def stream_tool_error(self, tool_name: str, tool_id: str, error: str):
        """
        Notify client of tool execution error
        
        Args:
            tool_name: Name of the tool
            tool_id: Tool call ID
            error: Error message
        """
        try:
            await self.websocket.send_json({
                "type": "tool_error",
                "tool_name": tool_name,
                "tool_id": tool_id,
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error streaming tool error: {e}")
            raise
    
    async def stream_complete(
        self,
        message_id: str,
        metadata: Dict[str, Any]
    ):
        """
        Send completion message with metadata
        
        Args:
            message_id: Message UUID
            metadata: Completion metadata (tokens, tools used, etc.)
        """
        try:
            await self.websocket.send_json({
                "type": "message_complete",
                "message_id": message_id,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error streaming complete: {e}")
            raise
    
    async def stream_error(self, error: str, error_code: str = None):
        """
        Stream error message to client
        
        Args:
            error: Error message
            error_code: Optional error code
        """
        try:
            message = {
                "type": "error",
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
            
            if error_code:
                message["error_code"] = error_code
            
            await self.websocket.send_json(message)
            
        except Exception as e:
            logger.error(f"Error streaming error message: {e}")
            raise
    
    # ========================================================================
    # PROGRESS INDICATORS
    # ========================================================================
    
    async def stream_thinking(self, message: str = "Thinking..."):
        """
        Send thinking indicator
        
        Args:
            message: Thinking message
        """
        try:
            await self.websocket.send_json({
                "type": "thinking",
                "message": message,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error streaming thinking: {e}")
            raise
    
    async def stream_processing(self, step: str, progress: float = None):
        """
        Send processing indicator
        
        Args:
            step: Current processing step
            progress: Progress percentage (0-100)
        """
        try:
            message = {
                "type": "processing",
                "step": step,
                "timestamp": datetime.now().isoformat()
            }
            
            if progress is not None:
                message["progress"] = progress
            
            await self.websocket.send_json(message)
            
        except Exception as e:
            logger.error(f"Error streaming processing: {e}")
            raise
    
    # ========================================================================
    # BUFFER MANAGEMENT
    # ========================================================================
    
    def get_full_message(self) -> str:
        """Get the complete message from buffer"""
        return "".join(self.message_buffer)
    
    def clear_buffer(self):
        """Clear the message buffer"""
        self.message_buffer = []
        self.chunk_count = 0
    
    def get_chunk_count(self) -> int:
        """Get total number of chunks sent"""
        return self.chunk_count
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    async def stream_rate_limit_info(self, current_usage: Dict, limits: Dict):
        """
        Stream rate limit information
        
        Args:
            current_usage: Current usage counts
            limits: Rate limit thresholds
        """
        try:
            await self.websocket.send_json({
                "type": "rate_limit_info",
                "current_usage": current_usage,
                "limits": limits,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error streaming rate limit info: {e}")
            raise
    
    async def stream_rate_limit_exceeded(self, error: str, details: Dict):
        """
        Stream rate limit exceeded notification
        
        Args:
            error: Error message
            details: Rate limit violation details
        """
        try:
            await self.websocket.send_json({
                "type": "rate_limit_exceeded",
                "error": error,
                "details": details,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error streaming rate limit exceeded: {e}")
            raise

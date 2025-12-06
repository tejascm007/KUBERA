"""
WebSocket Message Protocols
Defines message formats and protocol specifications
"""

from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# CLIENT -> SERVER MESSAGES
# ============================================================================

class WSChatMessage(BaseModel):
    """Chat message from client"""
    type: Literal["message"] = "message"
    chat_id: str = Field(..., description="Chat UUID")
    message: str = Field(..., description="User's message")


class WSPingMessage(BaseModel):
    """Ping message from client"""
    type: Literal["ping"] = "ping"


class WSTypingIndicator(BaseModel):
    """Typing indicator from client"""
    type: Literal["typing"] = "typing"
    chat_id: str = Field(..., description="Chat UUID")
    is_typing: bool = Field(..., description="Whether user is typing")


class WSMessageAck(BaseModel):
    """Message acknowledgment from client"""
    type: Literal["ack"] = "ack"
    message_id: str = Field(..., description="Message UUID")


# ============================================================================
# SERVER -> CLIENT MESSAGES
# ============================================================================

class WSConnectionMessage(BaseModel):
    """Connection confirmation"""
    type: Literal["connection"] = "connection"
    status: str = "connected"
    user_id: str
    timestamp: str


class WSTextChunk(BaseModel):
    """Streaming text chunk"""
    type: Literal["text_chunk"] = "text_chunk"
    content: str
    chunk_id: Optional[int] = None
    timestamp: str


class WSToolCallStart(BaseModel):
    """Tool call started"""
    type: Literal["tool_call_start"] = "tool_call_start"
    tool_name: str
    tool_id: str
    timestamp: str


class WSToolExecuting(BaseModel):
    """Tool is executing"""
    type: Literal["tool_executing"] = "tool_executing"
    tool_name: str
    tool_id: str
    status: str = "executing"
    timestamp: str


class WSToolComplete(BaseModel):
    """Tool execution completed"""
    type: Literal["tool_complete"] = "tool_complete"
    tool_name: str
    tool_id: str
    success: bool = True
    result: Optional[Any] = None
    timestamp: str


class WSToolError(BaseModel):
    """Tool execution error"""
    type: Literal["tool_error"] = "tool_error"
    tool_name: str
    tool_id: str
    error: str
    timestamp: str


class WSMessageComplete(BaseModel):
    """Message processing complete"""
    type: Literal["message_complete"] = "message_complete"
    message_id: str
    metadata: Dict[str, Any]
    timestamp: str


class WSError(BaseModel):
    """Error message"""
    type: Literal["error"] = "error"
    error: str
    error_code: Optional[str] = None
    timestamp: str


class WSPongMessage(BaseModel):
    """Pong response"""
    type: Literal["pong"] = "pong"
    timestamp: str


class WSRateLimitInfo(BaseModel):
    """Rate limit information"""
    type: Literal["rate_limit_info"] = "rate_limit_info"
    current_usage: Dict[str, int]
    limits: Dict[str, int]
    timestamp: str


class WSRateLimitExceeded(BaseModel):
    """Rate limit exceeded"""
    type: Literal["rate_limit_exceeded"] = "rate_limit_exceeded"
    error: str
    details: Dict[str, Any]
    timestamp: str


class WSThinking(BaseModel):
    """Thinking indicator"""
    type: Literal["thinking"] = "thinking"
    message: str = "Thinking..."
    timestamp: str


class WSProcessing(BaseModel):
    """Processing indicator"""
    type: Literal["processing"] = "processing"
    step: str
    progress: Optional[float] = None
    timestamp: str


# ============================================================================
# PROTOCOL DOCUMENTATION
# ============================================================================

PROTOCOL_DOCUMENTATION = {
    "version": "1.0",
    "description": "KUBERA WebSocket Protocol",
    
    "client_to_server": {
        "message": {
            "description": "Send a chat message",
            "schema": WSChatMessage.schema(),
            "example": {
                "type": "message",
                "chat_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Analyze INFY stock"
            }
        },
        "ping": {
            "description": "Ping to check connection",
            "schema": WSPingMessage.schema(),
            "example": {
                "type": "ping"
            }
        },
        "typing": {
            "description": "Typing indicator",
            "schema": WSTypingIndicator.schema(),
            "example": {
                "type": "typing",
                "chat_id": "550e8400-e29b-41d4-a716-446655440000",
                "is_typing": True
            }
        }
    },
    
    "server_to_client": {
        "connection": {
            "description": "Connection confirmation",
            "schema": WSConnectionMessage.schema()
        },
        "text_chunk": {
            "description": "Streaming text chunk from LLM",
            "schema": WSTextChunk.schema()
        },
        "tool_call_start": {
            "description": "Tool call initiated",
            "schema": WSToolCallStart.schema()
        },
        "tool_executing": {
            "description": "Tool is executing",
            "schema": WSToolExecuting.schema()
        },
        "tool_complete": {
            "description": "Tool execution completed",
            "schema": WSToolComplete.schema()
        },
        "tool_error": {
            "description": "Tool execution failed",
            "schema": WSToolError.schema()
        },
        "message_complete": {
            "description": "Message processing complete",
            "schema": WSMessageComplete.schema()
        },
        "error": {
            "description": "Error occurred",
            "schema": WSError.schema()
        },
        "rate_limit_info": {
            "description": "Rate limit information",
            "schema": WSRateLimitInfo.schema()
        },
        "rate_limit_exceeded": {
            "description": "Rate limit exceeded",
            "schema": WSRateLimitExceeded.schema()
        }
    }
}


def get_protocol_documentation() -> Dict:
    """Get protocol documentation"""
    return PROTOCOL_DOCUMENTATION

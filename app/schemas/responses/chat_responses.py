"""
Chat Response Schemas
Pydantic models for chat endpoint responses
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ChatResponse(BaseModel):
    """Response schema for single chat"""
    
    chat_id: str
    user_id: str
    chat_name: str
    total_prompts: int  # ← CHANGED from prompt_count
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True  # Allow ORM mode
        json_schema_extra = {
            "example": {
                "chat_id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "chat_name": "Stock Analysis Discussion",
                "total_prompts": 15,  # ← CHANGED
                "created_at": "2024-12-01T10:00:00+05:30",
                "updated_at": "2024-12-05T11:00:00+05:30",
                "last_message_at": "2024-12-05T11:00:00+05:30"
            }
        }


class ChatListResponse(BaseModel):
    """Response schema for list of chats"""
    
    success: bool = True
    total_chats: int
    chats: List[ChatResponse]


class CreateChatResponse(BaseModel):
    """Response schema for creating chat"""
    
    success: bool = True
    message: str
    chat: ChatResponse


class RenameChatResponse(BaseModel):
    """Response schema for renaming chat"""
    
    success: bool = True
    message: str
    chat: ChatResponse


class DeleteChatResponse(BaseModel):
    """Response schema for deleting chat"""
    
    success: bool = True
    message: str
    deleted_chat_id: str


class MessageResponse(BaseModel):
    """Response schema for single message"""
    
    message_id: str
    chat_id: str
    user_id: str
    user_message: str
    assistant_response: Optional[str] = None
    tokens_used: Optional[int] = None
    mcp_servers_called: Optional[List[str]] = None
    mcp_tools_used: Optional[List[str]] = None
    charts_generated: int = 0
    processing_time_ms: Optional[int] = None
    llm_model: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True  # Allow ORM mode


class ChatMessagesResponse(BaseModel):
    """Response schema for chat messages"""
    
    success: bool = True
    chat: ChatResponse
    messages: List[MessageResponse]
    total_messages: int


class WebSocketMessageResponse(BaseModel):
    """Response schema for WebSocket messages (streamed)"""
    
    type: str  # "chunk", "complete", "error", "rate_limit", "tool_call"
    chunk: Optional[str] = None  # Text chunk
    message_id: Optional[str] = None
    complete: bool = False
    error: Optional[str] = None
    metadata: Optional[dict] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "chunk",
                "chunk": "Based on the fundamentals...",
                "complete": False
            }
        }

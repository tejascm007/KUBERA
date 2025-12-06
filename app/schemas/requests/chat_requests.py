"""
Chat Request Schemas
Pydantic models for chat endpoints
"""

from pydantic import BaseModel, Field
from typing import Optional


class CreateChatRequest(BaseModel):
    """Request schema for creating a new chat"""
    
    chat_name: Optional[str] = Field(default="New Chat", max_length=255, description="Chat name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "chat_name": "Stock Analysis Discussion"
            }
        }


class RenameChatRequest(BaseModel):
    """Request schema for renaming a chat"""
    
    new_name: str = Field(..., min_length=1, max_length=255, description="New chat name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "new_name": "Portfolio Review Chat"
            }
        }


class SendMessageRequest(BaseModel):
    """Request schema for sending message (WebSocket)"""
    
    message: str = Field(..., min_length=1, max_length=5000, description="User message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Analyze INFY stock fundamentals"
            }
        }

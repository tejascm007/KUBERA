from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatBase(BaseModel):
    chat_name: str = Field(default="New Chat", max_length=255)


class ChatCreate(ChatBase):
    pass


class ChatInDBBase(ChatBase):
    chat_id: str
    user_id: str
    total_prompts: int = 0
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Chat(ChatInDBBase):
    pass


class MessageBase(BaseModel):
    user_message: str
    assistant_response: Optional[str] = None


class MessageCreate(BaseModel):
    chat_id: str
    user_message: str


class MessageInDBBase(MessageBase):
    message_id: str
    chat_id: str
    user_id: str

    tokens_used: Optional[int] = None
    processing_time_ms: Optional[int] = None
    mcp_servers_called: Optional[List[str]] = None
    mcp_tools_used: Optional[List[str]] = None
    charts_generated: int = 0
    llm_model: Optional[str] = None

    created_at: datetime
    response_completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Message(MessageInDBBase):
    pass


class ChatWithMessages(Chat):
    messages: List[Message] = []

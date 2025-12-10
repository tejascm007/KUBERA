"""
Chat Routes
Endpoints for chat and message management
"""

from fastapi import APIRouter, Depends, status, Path, Query
from typing import Dict, Any

from app.schemas.requests.chat_requests import (
    CreateChatRequest,
    RenameChatRequest
)
from app.schemas.responses.chat_responses import (
    ChatListResponse,
    CreateChatResponse,
    RenameChatResponse,
    DeleteChatResponse,
    ChatMessagesResponse
)
from app.services.chat_service import ChatService
from app.core.dependencies import get_current_user, verify_user_owns_chat
from app.core.database import get_db_pool

router = APIRouter(prefix="/chats", tags=["Chat"])


# ============================================================================
# CHAT OPERATIONS
# ============================================================================

@router.get(
    "/",
    response_model=ChatListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all chats",
    description="Get list of user's chats"
)
async def get_chats(
    limit: int = Query(50, ge=1, le=100, description="Number of chats"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: Dict = Depends(get_current_user)
):
    """
    **Get All Chats**
    
    - Returns list of chats sorted by last activity
    - Paginated results
    """
    db_pool = get_db_pool()
    chat_service = ChatService(db_pool)
    
    result = await chat_service.get_user_chats(
        current_user["user_id"],
        limit=limit,
        offset=offset
    )
    return result


@router.post(
    "/",
    response_model=CreateChatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new chat",
    description="Create a new chat conversation"
)
async def create_chat(
    request: CreateChatRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    **Create New Chat**
    
    - Creates empty chat
    - Use WebSocket to send messages
    """
    db_pool = get_db_pool()
    chat_service = ChatService(db_pool)
    
    chat = await chat_service.create_chat(
        current_user["user_id"],
        request.chat_name
    )
    
    return {
        "success": True,
        "message": "Chat created successfully",
        "chat": chat
    }


@router.get(
    "/{chat_id}",
    response_model=ChatMessagesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get chat with messages",
    description="Get chat details and message history"
)
async def get_chat_messages(
    chat_id: str = Path(..., description="Chat UUID"),
    limit: int = Query(100, ge=1, le=200, description="Number of messages"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: Dict = Depends(get_current_user)
):
    """
    **Get Chat Messages**
    
    - Returns chat info and message history
    - Messages ordered chronologically
    """
    db_pool = get_db_pool()
    
    # Verify user owns this chat
    await verify_user_owns_chat(chat_id, current_user, db_pool)
    
    chat_service = ChatService(db_pool)
    
    result = await chat_service.get_chat_with_messages(chat_id, limit, offset)
    return result


@router.put(
    "/{chat_id}/rename",
    response_model=RenameChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Rename chat",
    description="Update chat name"
)
async def rename_chat(
    chat_id: str = Path(..., description="Chat UUID"),
    request: RenameChatRequest = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    **Rename Chat**
    
    - Updates chat name
    """
    db_pool = get_db_pool()
    
    # Verify user owns this chat
    await verify_user_owns_chat(chat_id, current_user, db_pool)
    
    chat_service = ChatService(db_pool)
    
    chat = await chat_service.rename_chat(chat_id, request.new_name)
    
    return {
        "success": True,
        "message": "Chat renamed successfully",
        "chat": chat
    }


@router.delete(
    "/{chat_id}",
    response_model=DeleteChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete chat",
    description="Delete chat and all messages"
)
async def delete_chat(
    chat_id: str = Path(..., description="Chat UUID"),
    current_user: Dict = Depends(get_current_user)
):
    """
    **Delete Chat**
    
    - Deletes chat and all messages
    - Cannot be undone
    """
    db_pool = get_db_pool()
    
    # Verify user owns this chat
    await verify_user_owns_chat(chat_id, current_user, db_pool)
    
    chat_service = ChatService(db_pool)
    
    deleted = await chat_service.delete_chat(chat_id)
    
    if deleted:
        return {
            "success": True,
            "message": "Chat deleted successfully",
            "deleted_chat_id": chat_id
        }

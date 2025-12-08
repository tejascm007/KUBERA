"""
WebSocket Routes
WebSocket endpoints for real-time chat streaming
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import Optional
import logging
from app.api.websockets.chat_websocket import ChatWebSocketHandler
from app.core.dependencies import verify_token
from app.core.database import get_db_pool
from app.exceptions.custom_exceptions import UnauthorizedException

router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger(__name__)


async def get_current_user_ws(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT access token")
):
    """
    WebSocket authentication dependency
    
    Authenticates user via JWT token in query parameter
    """
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        raise UnauthorizedException("Token required")
    
    # Verify token
    payload = verify_token(token, token_type="access")
    
    if not payload:
        await websocket.close(code=1008, reason="Invalid token")
        raise UnauthorizedException("Invalid token")
    
    return {
        "user_id": payload.get("sub"),
        "email": payload.get("email")
    }


@router.websocket("/ws/chat")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT access token")
):
    """
    **WebSocket Chat Endpoint**
    
    Real-time bidirectional chat with streaming AI responses
    
    **Connection:**
    ```
    ws://localhost:8000/ws/chat?token=YOUR_JWT_TOKEN
    ```
    
    **Message Format (Client -> Server):**
    ```
    {
        "type": "message",
        "chat_id": "uuid",
        "message": "Analyze INFY stock"
    }
    ```
    
    **Response Format (Server -> Client):**
    
    1. **Rate Limit Info:**
    ```
    {
        "type": "rate_limit_info",
        "current_usage": {"burst": 1, "per_chat": 5, "hourly": 20, "daily": 50},
        "limits": {"burst": 10, "per_chat": 50, "hourly": 150, "daily": 1000}
    }
    ```
    
    2. **Text Chunks (Streaming):**
    ```
    {
        "type": "text_chunk",
        "content": "Based on the fundamentals..."
    }
    ```
    
    3. **Tool Execution:**
    ```
    {
        "type": "tool_executing",
        "tool_name": "get_stock_info",
        "tool_id": "tool_123"
    }
    ```
    
    4. **Completion:**
    ```
    {
        "type": "message_complete",
        "message_id": "uuid",
        "metadata": {
            "tokens_used": 1500,
            "tools_used": ["get_stock_info", "get_technical_indicators"],
            "processing_time_ms": 3500
        }
    }
    ```
    
    5. **Errors:**
    ```
    {
        "type": "error",
        "error": "Error message"
    }
    ```
    
    6. **Rate Limit Exceeded:**
    ```
    {
        "type": "rate_limit_exceeded",
        "error": "Daily rate limit exceeded",
        "details": {"violation_type": "daily", "limit": 1000, "used": 1000}
    }
    ```
    """
    try:
        # Authenticate user
        current_user = await get_current_user_ws(websocket, token)
        
        # Get database pool
        db_pool = await get_db_pool()
        
        # Create handler
        handler = ChatWebSocketHandler(
            websocket=websocket,
            user_id=current_user["user_id"],
            db_pool=db_pool
        )
        
        # Connect and listen
        await handler.connect()
        await handler.listen()
        
    except UnauthorizedException:
        # Already handled in get_current_user_ws
        pass
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass

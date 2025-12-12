"""
WebSocket Routes for Chat
Handles WebSocket connections and routing
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Query
from app.api.websockets.chat_websocket import ChatWebSocketHandler
from app.core.security import verify_token
from app.exceptions.custom_exceptions import AuthenticationException
from app.core.database import get_db_pool
from app.websocket.connection_manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


#========================================================================
# JWT TOKEN EXTRACTION FROM WEBSOCKET
# ========================================================================

async def get_token_from_query(websocket: WebSocket) -> str:
    """
    Extract JWT token from WebSocket query parameters
    
    Args:
        websocket: WebSocket connection
    
    Returns:
        JWT token string
    
    Raises:
        AuthenticationException: If token not found
    """
    
    # Get token from query parameter
    token = websocket.query_params.get("token")
    
    if token:
        logger.info("Token extracted from query parameter")
        return token
    
    # No token found
    logger.error("No JWT token found in query params")
    raise AuthenticationException("Missing authentication token")


# ========================================================================
# WEBSOCKET ENDPOINT
# ========================================================================

@router.websocket("/chat/{chat_id}")
async def websocket_chat(websocket: WebSocket, chat_id: str):
    """
    WebSocket endpoint for real-time chat
    
    URL: ws://localhost:8000/ws/chat/{chat_id}?token=<JWT_TOKEN>
    
    Args:
        websocket: WebSocket connection
        chat_id: Chat session ID (UUID)
    """
    
    # ========================================================================
    # STEP 1: ACCEPT CONNECTION IMMEDIATELY (BEFORE AUTH)
    # ========================================================================
    
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for chat {chat_id}")
    
    try:
        # ========================================================================
        # STEP 2: AUTHENTICATE (AFTER ACCEPTING)
        # ========================================================================
        
        try:
            # Extract JWT token from query params
            token = await get_token_from_query(websocket)
            
            # Verify token with explicit token_type
            payload = verify_token(token, token_type="access")
            
            if not payload:
                logger.error("JWT token verification failed")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid or expired token"
                })
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            
            user_id = payload.get("sub")
            email = payload.get("email")
            
            if not user_id:
                logger.error("JWT token missing user_id (sub)")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid token: missing user_id"
                })
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            
            logger.info(f"JWT verified for user {user_id}")
        
        except AuthenticationException as e:
            logger.warning(f"Authentication failed: {str(e)}")
            await websocket.send_json({
                "type": "error",
                "message": "Authentication failed"
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            await websocket.send_json({
                "type": "error",
                "message": "Invalid token"
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        # ========================================================================
        # STEP 3: GET DATABASE POOL
        # ========================================================================
        
        try:
            db_pool = get_db_pool()
            if not db_pool:
                logger.error("Database pool not available")
                await websocket.send_json({
                    "type": "error",
                    "message": "Database connection error"
                })
                await websocket.close(code=status.WS_1011_SERVER_ERROR)
                return
        except Exception as e:
            logger.error(f"Error getting database pool: {str(e)}")
            await websocket.send_json({
                "type": "error",
                "message": "Database error"
            })
            await websocket.close(code=status.WS_1011_SERVER_ERROR)
            return
        
        # ========================================================================
        # STEP 4: VERIFY USER OWNS THE CHAT
        # ========================================================================
        
        try:
            from app.db.repositories.chat_repository import ChatRepository
            chat_repo = ChatRepository(db_pool)
            chat = await chat_repo.get_chat_by_id(chat_id)
            
            if not chat:
                logger.warning(f"Chat {chat_id} not found")
                await websocket.send_json({
                    "type": "error",
                    "message": "Chat not found"
                })
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            
            if str(chat["user_id"]) != str(user_id):
                logger.warning(f"User {user_id} attempted to access chat {chat_id} owned by {chat['user_id']}")
                await websocket.send_json({
                    "type": "error",
                    "message": "You don't have permission to access this chat"
                })
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            
            logger.info(f"Chat ownership verified for user {user_id}, chat {chat_id}")
            
        except Exception as e:
            logger.error(f"Error verifying chat ownership: {str(e)}")
            await websocket.send_json({
                "type": "error",
                "message": "Failed to verify chat access"
            })
            await websocket.close(code=status.WS_1011_SERVER_ERROR)
            return
        
        # ========================================================================
        # STEP 5: SEND CONNECTION CONFIRMATION
        # ========================================================================
        
        await websocket.send_json({
            "type": "connected",
            "chat_id": chat_id,
            "user_id": user_id,
            "message": "Connected to chat successfully"
        })
        logger.info(f"Connection confirmed for user {user_id}, chat {chat_id}")
        
        # Register connection with connection manager
        await connection_manager.connect(websocket, user_id, {
            "chat_id": chat_id,
            "email": email
        })
        
        # ========================================================================
        # STEP 6: INITIALIZE HANDLER
        # ========================================================================
        
        handler = ChatWebSocketHandler(
            websocket=websocket,
            user_id=user_id,
            email=email,
            chat_id=chat_id,
            db_pool=db_pool
        )
        
        # ========================================================================
        # STEP 7: CONNECT AND LISTEN
        # ========================================================================
        
        try:
            await handler.connect()
            await handler.listen()
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user {user_id}, chat {chat_id}")
            await connection_manager.disconnect(websocket, user_id)
            await handler.disconnect()
        
        except Exception as e:
            logger.error(f"Error in WebSocket handler: {str(e)}", exc_info=True)
            await connection_manager.disconnect(websocket, user_id)
            await handler.disconnect()
    
    except Exception as e:
        logger.error(f"Unexpected error in websocket_chat: {str(e)}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Internal server error"
            })
            await websocket.close(code=status.WS_1011_SERVER_ERROR)
        except Exception:
            pass

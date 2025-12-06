"""
WebSocket Message Handler
Validates and routes incoming WebSocket messages
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


# ============================================================================
# MESSAGE SCHEMAS
# ============================================================================

class ChatMessageSchema(BaseModel):
    """Schema for chat message"""
    type: str = "message"
    chat_id: str
    message: str


class PingMessageSchema(BaseModel):
    """Schema for ping message"""
    type: str = "ping"


class TypingIndicatorSchema(BaseModel):
    """Schema for typing indicator"""
    type: str = "typing"
    chat_id: str
    is_typing: bool


class MessageAcknowledgmentSchema(BaseModel):
    """Schema for message acknowledgment"""
    type: str = "ack"
    message_id: str


# ============================================================================
# MESSAGE HANDLER
# ============================================================================

class WebSocketMessageHandler:
    """
    Handles incoming WebSocket messages
    Validates, parses, and routes messages to appropriate handlers
    """
    
    def __init__(self):
        self.message_types = {
            "message": ChatMessageSchema,
            "ping": PingMessageSchema,
            "typing": TypingIndicatorSchema,
            "ack": MessageAcknowledgmentSchema
        }
    
    # ========================================================================
    # MESSAGE VALIDATION
    # ========================================================================
    
    def validate_message(self, data: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[BaseModel]]:
        """
        Validate incoming message against schema
        
        Args:
            data: Raw message data
        
        Returns:
            (is_valid, error_message, parsed_message)
        """
        # Check if type field exists
        if "type" not in data:
            return False, "Missing 'type' field", None
        
        message_type = data.get("type")
        
        # Check if type is supported
        if message_type not in self.message_types:
            return False, f"Unknown message type: {message_type}", None
        
        # Get schema for message type
        schema = self.message_types[message_type]
        
        # Validate message
        try:
            parsed_message = schema(**data)
            return True, None, parsed_message
        
        except ValidationError as e:
            error_msg = f"Validation error: {str(e)}"
            return False, error_msg, None
    
    # ========================================================================
    # MESSAGE ROUTING
    # ========================================================================
    
    async def route_message(
        self,
        data: Dict[str, Any],
        websocket_handler
    ) -> Dict[str, Any]:
        """
        Route message to appropriate handler
        
        Args:
            data: Message data
            websocket_handler: WebSocket handler instance
        
        Returns:
            Response dict
        """
        # Validate message
        is_valid, error, parsed_message = self.validate_message(data)
        
        if not is_valid:
            return {
                "type": "error",
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
        
        message_type = parsed_message.type
        
        # Route to handler
        if message_type == "message":
            await websocket_handler.handle_chat_message(data)
            return {"type": "routing", "status": "handled"}
        
        elif message_type == "ping":
            await websocket_handler.handle_ping()
            return {"type": "routing", "status": "handled"}
        
        elif message_type == "typing":
            await websocket_handler.handle_typing_indicator(data)
            return {"type": "routing", "status": "handled"}
        
        elif message_type == "ack":
            await websocket_handler.handle_message_acknowledgment(data)
            return {"type": "routing", "status": "handled"}
        
        else:
            return {
                "type": "error",
                "error": f"No handler for message type: {message_type}"
            }
    
    # ========================================================================
    # MESSAGE FORMATTING
    # ========================================================================
    
    def format_error_response(self, error: str) -> Dict[str, Any]:
        """Format error response"""
        return {
            "type": "error",
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
    
    def format_success_response(self, message: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Format success response"""
        response = {
            "type": "success",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        if data:
            response["data"] = data
        
        return response
    
    # ========================================================================
    # MESSAGE LOGGING
    # ========================================================================
    
    def log_incoming_message(self, user_id: str, message_type: str, data: Dict):
        """Log incoming message"""
        logger.info(f"Incoming WS message: user={user_id}, type={message_type}")
        logger.debug(f"Message data: {data}")
    
    def log_outgoing_message(self, user_id: str, message_type: str):
        """Log outgoing message"""
        logger.info(f"Outgoing WS message: user={user_id}, type={message_type}")


# ========================================================================
# GLOBAL INSTANCE
# ========================================================================

message_handler = WebSocketMessageHandler()

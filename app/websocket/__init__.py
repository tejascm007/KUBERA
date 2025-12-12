"""
WebSocket Module
Real-time communication handling
"""

from app.websocket.connection_manager import ConnectionManager, connection_manager
from app.websocket.message_handler import WebSocketMessageHandler, message_handler
from app.websocket.response_streamer import ResponseStreamer
from app.websocket.protocols import (
    WSChatMessage,
    WSPingMessage,
    WSTypingIndicator,
    WSTextChunk,
    WSToolExecuting,
    WSToolComplete,
    WSError,
    WSMessageComplete,
    get_protocol_documentation
)

__all__ = [
    "ConnectionManager",
    "connection_manager",
    "WebSocketMessageHandler",
    "message_handler",
    "ResponseStreamer",
    "WSChatMessage",
    "WSPingMessage",
    "WSTypingIndicator",
    "WSTextChunk",
    "WSToolExecuting",
    "WSToolComplete",
    "WSError",
    "WSMessageComplete",
    "get_protocol_documentation"
]

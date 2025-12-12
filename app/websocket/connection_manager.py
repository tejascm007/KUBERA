"""
WebSocket Connection Manager
Manages active WebSocket connections, broadcasting, and connection pool
"""

import logging
from typing import Dict, List, Set, Optional
from fastapi import WebSocket
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages all active WebSocket connections
    Supports per-user connections, broadcasting, and connection tracking
    """
    
    def __init__(self):
        # Active connections by user_id
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
        # Connection metadata
        self.connection_metadata: Dict[WebSocket, Dict] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    # ========================================================================
    # CONNECTION MANAGEMENT
    # ========================================================================
    
    async def connect(self, websocket: WebSocket, user_id: str, metadata: Optional[Dict] = None):
        """
        Add a new WebSocket connection
        
        Args:
            websocket: WebSocket instance
            user_id: User UUID
            metadata: Optional connection metadata (IP, user agent, chat_id, etc.)
        
        Note: websocket.accept() should be called BEFORE this method
        """
        async with self._lock:
            # Add to user's connections list
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            
            self.active_connections[user_id].append(websocket)
            
            # Store metadata
            self.connection_metadata[websocket] = {
                "user_id": user_id,
                "chat_id": metadata.get("chat_id") if metadata else None,
                "connected_at": datetime.now(),
                "ip_address": metadata.get("ip_address") if metadata else None,
                "user_agent": metadata.get("user_agent") if metadata else None
            }
            
            logger.info(f"WebSocket registered: user={user_id}, total_connections={len(self.active_connections[user_id])}")
    
    async def disconnect(self, websocket: WebSocket, user_id: str):
        """
        Remove a WebSocket connection
        
        Args:
            websocket: WebSocket instance
            user_id: User UUID
        """
        async with self._lock:
            # Remove from user's connections
            if user_id in self.active_connections:
                if websocket in self.active_connections[user_id]:
                    self.active_connections[user_id].remove(websocket)
                
                # Remove user entry if no more connections
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Remove metadata
            if websocket in self.connection_metadata:
                del self.connection_metadata[websocket]
            
            logger.info(f"WebSocket disconnected: user={user_id}")
    
    # ========================================================================
    # SENDING MESSAGES
    # ========================================================================
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send message to a specific WebSocket connection
        
        Args:
            message: Message dict to send
            websocket: Target WebSocket
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def send_to_user(self, message: dict, user_id: str):
        """
        Send message to all connections of a user
        
        Args:
            message: Message dict to send
            user_id: Target user UUID
        """
        if user_id in self.active_connections:
            disconnected = []
            
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to user {user_id}: {e}")
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                await self.disconnect(conn, user_id)
    
    async def broadcast(self, message: dict):
        """
        Broadcast message to all active connections
        
        Args:
            message: Message dict to send
        """
        disconnected = []
        
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")
                    disconnected.append((connection, user_id))
        
        # Clean up disconnected connections
        for conn, uid in disconnected:
            await self.disconnect(conn, uid)
    
    async def broadcast_to_users(self, message: dict, user_ids: List[str]):
        """
        Broadcast message to specific users
        
        Args:
            message: Message dict to send
            user_ids: List of target user UUIDs
        """
        for user_id in user_ids:
            await self.send_to_user(message, user_id)
    
    # ========================================================================
    # CONNECTION QUERIES
    # ========================================================================
    
    def is_user_connected(self, user_id: str) -> bool:
        """Check if user has any active connections"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0
    
    def get_user_connection_count(self, user_id: str) -> int:
        """Get number of active connections for a user"""
        return len(self.active_connections.get(user_id, []))
    
    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        return sum(len(conns) for conns in self.active_connections.values())
    
    def get_connected_users(self) -> List[str]:
        """Get list of all connected user IDs"""
        return list(self.active_connections.keys())
    
    def get_connection_metadata(self, websocket: WebSocket) -> Optional[Dict]:
        """Get metadata for a specific connection"""
        return self.connection_metadata.get(websocket)
    
    # ========================================================================
    # CONNECTION STATISTICS
    # ========================================================================
    
    def get_statistics(self) -> Dict:
        """
        Get connection statistics
        
        Returns:
            Dict with statistics
        """
        return {
            "total_connections": self.get_total_connections(),
            "unique_users": len(self.active_connections),
            "connections_per_user": {
                user_id: len(conns) 
                for user_id, conns in self.active_connections.items()
            }
        }
    
    # ========================================================================
    # CLEANUP
    # ========================================================================
    
    async def close_all_connections(self):
        """Close all active WebSocket connections (for shutdown)"""
        logger.info("Closing all WebSocket connections...")
        
        for user_id, connections in list(self.active_connections.items()):
            for connection in connections:
                try:
                    await connection.close()
                except Exception as e:
                    logger.error(f"Error closing connection for user {user_id}: {e}")
        
        self.active_connections.clear()
        self.connection_metadata.clear()
        
        logger.info("All WebSocket connections closed")


# ========================================================================
# GLOBAL INSTANCE
# ========================================================================

connection_manager = ConnectionManager()

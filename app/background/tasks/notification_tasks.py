"""
Background Notification Tasks
Handles push notifications and real-time updates
"""

import logging
from typing import Dict, Any, List

from app.websocket.connection_manager import connection_manager

logger = logging.getLogger(__name__)


async def send_notification_to_user(user_id: str, notification: Dict[str, Any]):
    """
    Send real-time notification to user via WebSocket
    
    Args:
        user_id: User UUID
        notification: Notification dict
    """
    try:
        if connection_manager.is_user_connected(user_id):
            await connection_manager.send_to_user(notification, user_id)
            logger.info(f" Notification sent to user {user_id}")
        else:
            logger.info(f"User {user_id} not connected, notification not sent")
    
    except Exception as e:
        logger.error(f" Failed to send notification to user {user_id}: {e}")


async def broadcast_system_notification(notification: Dict[str, Any]):
    """
    Broadcast system notification to all connected users
    
    Args:
        notification: Notification dict
    """
    try:
        await connection_manager.broadcast(notification)
        
        total_users = len(connection_manager.get_connected_users())
        logger.info(f" System notification broadcast to {total_users} users")
    
    except Exception as e:
        logger.error(f" Failed to broadcast system notification: {e}")


async def notify_rate_limit_exceeded(user_id: str, violation_type: str, details: Dict):
    """
    Send rate limit exceeded notification
    
    Args:
        user_id: User UUID
        violation_type: Type of violation
        details: Violation details
    """
    notification = {
        "type": "notification",
        "category": "rate_limit",
        "title": "Rate Limit Exceeded",
        "message": f"You have exceeded the {violation_type} rate limit",
        "details": details
    }
    
    await send_notification_to_user(user_id, notification)


async def notify_portfolio_update(user_id: str, message: str):
    """
    Send portfolio update notification
    
    Args:
        user_id: User UUID
        message: Update message
    """
    notification = {
        "type": "notification",
        "category": "portfolio",
        "title": "Portfolio Update",
        "message": message
    }
    
    await send_notification_to_user(user_id, notification)

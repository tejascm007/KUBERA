"""
API Routes Module
All API route handlers
"""

from app.api.routes import (
    auth_routes,
    user_routes,
    portfolio_routes,
    chat_routes,
    admin_routes,
    websocket_routes
)

__all__ = [
    "auth_routes",
    "user_routes",
    "portfolio_routes",
    "chat_routes",
    "admin_routes",
    "websocket_routes"
]

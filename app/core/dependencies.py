"""
FastAPI Dependencies
Authentication, database connection, rate limiting
"""

from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging
from app.utils.validators import PasswordValidator
from app.core.security import verify_token
from app.core.database import get_db_pool
from app.db.repositories.user_repository import UserRepository
from app.exceptions.custom_exceptions import (
    UnauthorizedException,
    ForbiddenException,
    UserNotFoundException
)

logger = logging.getLogger(__name__)

# HTTP Bearer token security
security = HTTPBearer()


# ============================================================================
# DATABASE DEPENDENCY
# ============================================================================

async def get_db():
    """
    Get database connection pool
    
    Usage in endpoint:
        async def endpoint(db = Depends(get_db)):
            ...
    """
    return await get_db_pool()


# ============================================================================
# AUTHENTICATION DEPENDENCIES
# ============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = Depends(get_db)
):
    """
    Get current authenticated user from JWT token
    
    Args:
        credentials: Bearer token from Authorization header
        db: Database connection pool
    
    Returns:
        User dict
    
    Raises:
        UnauthorizedException: Invalid or expired token
        UserNotFoundException: User not found
    """
    token = credentials.credentials
    
    # Verify token
    payload = verify_token(token, token_type="access")
    
    if not payload:
        raise UnauthorizedException("Invalid or expired token")
    
    # Get user_id from token
    user_id = payload.get("sub")
    
    if not user_id:
        raise UnauthorizedException("Invalid token payload")
    
    # Get user from database
    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_id(user_id)
    
    if not user:
        raise UserNotFoundException(f"User {user_id} not found")
    
    # Check if account is active
    if user["account_status"] != "active":
        raise ForbiddenException(f"Account is {user['account_status']}")
    
    return user


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current active user (account must be active)
    
    Args:
        current_user: User from get_current_user
    
    Returns:
        User dict
    
    Raises:
        ForbiddenException: Account not active
    """
    if current_user["account_status"] != "active":
        raise ForbiddenException("Account is not active")
    
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db = Depends(get_db)
) -> Optional[dict]:
    """
    Get user if token provided, otherwise None (for optional auth)
    
    Args:
        credentials: Optional Bearer token
        db: Database connection pool
    
    Returns:
        User dict or None
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except (UnauthorizedException, UserNotFoundException):
        return None


# ============================================================================
# ADMIN AUTHENTICATION
# ============================================================================

async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = Depends(get_db)
):
    """
    Get current authenticated admin from JWT token
    
    Args:
        credentials: Bearer token
        db: Database connection pool
    
    Returns:
        Admin dict
    
    Raises:
        UnauthorizedException: Invalid token
        ForbiddenException: Not an admin
    """
    token = credentials.credentials
    
    # Verify token
    payload = verify_token(token, token_type="access")
    
    if not payload:
        raise UnauthorizedException("Invalid or expired token")
    
    # Check if token is for admin
    if payload.get("role") != "admin":
        raise ForbiddenException("Admin access required")
    
    # Get admin_id from token
    admin_id = payload.get("sub")
    
    if not admin_id:
        raise UnauthorizedException("Invalid token payload")
    
    # Get admin from database
    from app.db.repositories.admin_repository import AdminRepository
    admin_repo = AdminRepository(db)
    admin = await admin_repo.get_admin_by_id(admin_id)
    
    if not admin:
        raise ForbiddenException("Admin not found")
    
    # Check if admin is active
    if not admin["is_active"]:
        raise ForbiddenException("Admin account is inactive")
    
    return admin


# ============================================================================
# WEBSOCKET AUTHENTICATION
# ============================================================================

async def get_user_from_websocket(
    websocket: WebSocket,
    token: str,
    db = Depends(get_db)
):
    """
    Authenticate user from WebSocket connection
    
    Args:
        websocket: WebSocket connection
        token: JWT token from query params or headers
        db: Database connection pool
    
    Returns:
        User dict
    
    Raises:
        Exception: Authentication failed
    """
    # Verify token
    payload = verify_token(token, token_type="access")
    
    if not payload:
        await websocket.close(code=4001, reason="Invalid or expired token")
        raise UnauthorizedException("Invalid or expired token")
    
    # Get user_id
    user_id = payload.get("sub")
    
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token payload")
        raise UnauthorizedException("Invalid token payload")
    
    # Get user
    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_id(user_id)
    
    if not user:
        await websocket.close(code=4004, reason="User not found")
        raise UserNotFoundException(f"User {user_id} not found")
    
    # Check account status
    if user["account_status"] != "active":
        await websocket.close(code=4003, reason="Account not active")
        raise ForbiddenException("Account not active")
    
    return user


# ============================================================================
# UTILITY DEPENDENCIES
# ============================================================================

async def verify_user_owns_resource(
    resource_user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Verify that current user owns the resource
    
    Args:
        resource_user_id: User ID that owns the resource
        current_user: Current authenticated user
    
    Raises:
        ForbiddenException: User doesn't own resource
    """
    if str(current_user["user_id"]) != str(resource_user_id):
        raise ForbiddenException("You don't have permission to access this resource")


async def verify_user_owns_chat(
    chat_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Verify that current user owns the chat
    
    Args:
        chat_id: Chat UUID
        current_user: Current authenticated user
        db: Database connection pool
    
    Returns:
        Chat dict
    
    Raises:
        ForbiddenException: User doesn't own chat
    """
    from app.db.repositories.chat_repository import ChatRepository
    
    chat_repo = ChatRepository(db)
    chat = await chat_repo.get_chat_by_id(chat_id)
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if str(chat["user_id"]) != str(current_user["user_id"]):
        raise ForbiddenException("You don't have permission to access this chat")
    
    return chat


async def verify_user_owns_portfolio(
    portfolio_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Verify that current user owns the portfolio entry
    
    Args:
        portfolio_id: Portfolio UUID
        current_user: Current authenticated user
        db: Database connection pool
    
    Returns:
        Portfolio dict
    
    Raises:
        ForbiddenException: User doesn't own portfolio
    """
    from app.db.repositories.portfolio_repository import PortfolioRepository
    
    portfolio_repo = PortfolioRepository(db)
    portfolio = await portfolio_repo.get_portfolio_by_id(portfolio_id)
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio entry not found")
    
    if str(portfolio["user_id"]) != str(current_user["user_id"]):
        raise ForbiddenException("You don't have permission to access this portfolio")
    
    return portfolio


# Password validator instance
password_validator = PasswordValidator()

async def get_password_validator() -> PasswordValidator:
    """Get password validator instance"""
    return password_validator


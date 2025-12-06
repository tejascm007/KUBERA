"""
User Service
Business logic for user profile management
"""

from typing import Dict, Any
import logging

from app.db.repositories.user_repository import UserRepository
from app.db.repositories.email_repository import EmailRepository
from app.db.repositories.token_repository import TokenRepository
from app.core.security import hash_password, verify_password, validate_password_strength
from app.exceptions.custom_exceptions import (
    UserAlreadyExistsException,
    InvalidCredentialsException,
    WeakPasswordException
)
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class UserService:
    """User profile service"""
    
    def __init__(self, db_pool):
        self.db = db_pool
        self.user_repo = UserRepository(db_pool)
        self.email_repo = EmailRepository(db_pool)
        self.token_repo = TokenRepository(db_pool)
        self.email_service = EmailService(db_pool)
    
    # ========================================================================
    # PROFILE OPERATIONS
    # ========================================================================
    
    async def get_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get user profile
        
        Args:
            user_id: User UUID
        
        Returns:
            User profile dict
        """
        user = await self.user_repo.get_user_by_id(user_id)
        
        # Remove sensitive data
        if user:
            user.pop('password_hash', None)
        
        return user
    
    async def update_profile(
        self,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update user profile
        
        Args:
            user_id: User UUID
            updates: Fields to update
        
        Returns:
            Updated user profile
        """
        # Remove fields that shouldn't be updated via this method
        updates.pop('email', None)
        updates.pop('username', None)
        updates.pop('password_hash', None)
        updates.pop('user_id', None)
        updates.pop('account_status', None)
        
        user = await self.user_repo.update_user(user_id, updates)
        
        # Remove sensitive data
        if user:
            user.pop('password_hash', None)
        
        logger.info(f"Profile updated for user: {user_id}")
        
        return user
    
    # ========================================================================
    # USERNAME UPDATE
    # ========================================================================
    
    async def update_username(
        self,
        user_id: str,
        new_username: str
    ) -> Dict[str, Any]:
        """
        Update username
        
        Args:
            user_id: User UUID
            new_username: New username
        
        Returns:
            Updated user profile
        
        Raises:
            UserAlreadyExistsException: Username already taken
        """
        # Check if username is taken
        if await self.user_repo.check_username_exists(new_username):
            raise UserAlreadyExistsException("Username is already taken")
        
        user = await self.user_repo.update_username(user_id, new_username)
        
        if user:
            user.pop('password_hash', None)
        
        logger.info(f"Username updated for user: {user_id}")
        
        return user
    
    # ========================================================================
    # PASSWORD UPDATE
    # ========================================================================
    
    async def update_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> None:
        """
        Update password
        
        Args:
            user_id: User UUID
            current_password: Current password
            new_password: New password
        
        Raises:
            InvalidCredentialsException: Wrong current password
            WeakPasswordException: New password too weak
        """
        # Get user
        user = await self.user_repo.get_user_by_id(user_id)
        
        # Verify current password
        if not verify_password(current_password, user['password_hash']):
            raise InvalidCredentialsException("Current password is incorrect")
        
        # Validate new password
        is_valid, errors = validate_password_strength(new_password)
        if not is_valid:
            raise WeakPasswordException("Password is too weak", details=errors)
        
        # Update password
        new_password_hash = hash_password(new_password)
        await self.user_repo.update_password(user_id, new_password_hash)
        
        # Revoke all refresh tokens
        await self.token_repo.revoke_all_user_tokens(user_id, reason="password_change")
        
        # Send confirmation email
        await self.email_service.send_password_changed_email(user)
        
        logger.info(f"Password updated for user: {user_id}")
    
    # ========================================================================
    # EMAIL PREFERENCES
    # ========================================================================
    
    async def get_email_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get email preferences"""
        return await self.email_repo.get_email_preferences(user_id)
    
    async def update_email_preferences(
        self,
        user_id: str,
        preferences: Dict[str, bool]
    ) -> Dict[str, Any]:
        """Update email preferences"""
        updated = await self.email_repo.update_email_preferences(user_id, preferences)
        
        logger.info(f"Email preferences updated for user: {user_id}")
        
        return updated
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics"""
        return await self.user_repo.get_user_statistics(user_id)

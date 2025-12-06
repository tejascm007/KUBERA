"""
User Routes
Endpoints for user profile management
"""

from fastapi import APIRouter, Depends, status
from typing import Dict, Any

from app.schemas.requests.user_requests import (
    UpdateProfileRequest,
    UpdateUsernameRequest,
    UpdatePasswordRequest,
    UpdateEmailPreferencesRequest
)
from app.schemas.responses.user_responses import (
    ProfileResponse,
    UpdateProfileResponse,
    UpdateUsernameResponse,
    UpdatePasswordResponse,
    EmailPreferencesResponse,
    UpdateEmailPreferencesResponse
)
from app.services.user_service import UserService
from app.core.dependencies import get_current_user
from app.core.database import get_db_pool

router = APIRouter(prefix="/user", tags=["User Profile"])


# ============================================================================
# PROFILE
# ============================================================================

@router.get(
    "/profile",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user profile",
    description="Get current user's profile information"
)
async def get_profile(current_user: Dict = Depends(get_current_user)):
    """
    **Get User Profile**
    
    - Returns complete user profile
    - Requires authentication
    """
    db_pool = await get_db_pool()
    user_service = UserService(db_pool)
    
    profile = await user_service.get_profile(current_user["user_id"])
    return profile


@router.put(
    "/profile",
    response_model=UpdateProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user profile",
    description="Update user profile fields"
)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    **Update User Profile**
    
    - Update personal information
    - Cannot change email, username, or password via this endpoint
    - Use dedicated endpoints for those
    """
    db_pool = await get_db_pool()
    user_service = UserService(db_pool)
    
    updates = request.dict(exclude_unset=True)
    profile = await user_service.update_profile(current_user["user_id"], updates)
    
    return {
        "success": True,
        "message": "Profile updated successfully",
        "user": profile
    }


# ============================================================================
# USERNAME
# ============================================================================

@router.put(
    "/username",
    response_model=UpdateUsernameResponse,
    status_code=status.HTTP_200_OK,
    summary="Update username",
    description="Change username (must be unique)"
)
async def update_username(
    request: UpdateUsernameRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    **Update Username**
    
    - Username must be unique
    - Cannot revert for 30 days (consider implementing cooldown)
    """
    db_pool = await get_db_pool()
    user_service = UserService(db_pool)
    
    profile = await user_service.update_username(
        current_user["user_id"],
        request.new_username
    )
    
    return {
        "success": True,
        "message": "Username updated successfully",
        "new_username": profile["username"]
    }


# ============================================================================
# PASSWORD
# ============================================================================

@router.put(
    "/password",
    response_model=UpdatePasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Update password",
    description="Change account password"
)
async def update_password(
    request: UpdatePasswordRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    **Update Password**
    
    - Requires current password
    - New password must meet strength requirements
    - Logs out all other sessions
    - Sends confirmation email
    """
    db_pool = await get_db_pool()
    user_service = UserService(db_pool)
    
    await user_service.update_password(
        current_user["user_id"],
        request.current_password,
        request.new_password
    )
    
    return {
        "success": True,
        "message": "Password updated successfully"
    }


# ============================================================================
# EMAIL PREFERENCES
# ============================================================================

@router.get(
    "/email-preferences",
    response_model=EmailPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get email preferences",
    description="Get current email notification preferences"
)
async def get_email_preferences(current_user: Dict = Depends(get_current_user)):
    """
    **Get Email Preferences**
    
    - Returns all email notification settings
    """
    db_pool = await get_db_pool()
    user_service = UserService(db_pool)
    
    preferences = await user_service.get_email_preferences(current_user["user_id"])
    return preferences


@router.put(
    "/email-preferences",
    response_model=UpdateEmailPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Update email preferences",
    description="Update email notification preferences"
)
async def update_email_preferences(
    request: UpdateEmailPreferencesRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    **Update Email Preferences**
    
    - Control which emails you receive
    - Portfolio reports, rate limit notifications, etc.
    """
    db_pool = await get_db_pool()
    user_service = UserService(db_pool)
    
    preferences_dict = request.dict(exclude_unset=True)
    preferences = await user_service.update_email_preferences(
        current_user["user_id"],
        preferences_dict
    )
    
    return {
        "success": True,
        "message": "Email preferences updated successfully",
        "preferences": preferences
    }


# ============================================================================
# STATISTICS
# ============================================================================

@router.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    summary="Get user statistics",
    description="Get user activity statistics"
)
async def get_user_stats(current_user: Dict = Depends(get_current_user)):
    """
    **Get User Statistics**
    
    - Total chats, messages, prompts
    - Portfolio count
    - Account activity
    """
    db_pool = await get_db_pool()
    user_service = UserService(db_pool)
    
    stats = await user_service.get_user_stats(current_user["user_id"])
    return {
        "success": True,
        "stats": stats
    }

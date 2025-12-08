"""
User Profile Response Schemas
Pydantic models for user endpoint responses
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class ProfileResponse(BaseModel):
    """Response schema for user profile"""
    
    user_id: str
    email: EmailStr
    username: str
    full_name: str
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    profile_picture_url: Optional[str] = None
    investment_style: Optional[str] = None
    risk_tolerance: Optional[str] = None
    interested_sectors: Optional[list[str]] = None
    account_status: str
    email_verified: bool
    theme_preference: Optional[str] = "light" 
    language_preference: Optional[str] = "en" 
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None


class UpdateProfileResponse(BaseModel):
    """Response schema for profile update"""
    
    success: bool = True
    message: str
    user: ProfileResponse


class UpdateUsernameResponse(BaseModel):
    """Response schema for username update"""
    
    success: bool = True
    message: str
    new_username: str


class UpdatePasswordResponse(BaseModel):
    """Response schema for password update"""
    
    success: bool = True
    message: str = "Password updated successfully"


class EmailPreferencesResponse(BaseModel):
    """Response schema for email preferences"""
    
    preference_id: str
    user_id: str
    portfolio_reports: bool
    security_alerts: bool
    rate_limit_notifications: bool
    system_notifications: bool
    promotional_emails: bool
    updated_at: datetime


class UpdateEmailPreferencesResponse(BaseModel):
    """Response schema for updating email preferences"""
    
    success: bool = True
    message: str
    preferences: EmailPreferencesResponse

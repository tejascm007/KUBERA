"""
User Profile Request Schemas
Pydantic models for user profile endpoints
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
import re


class UpdateProfileRequest(BaseModel):
    """Request schema for updating user profile"""
    
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None)
    date_of_birth: Optional[str] = Field(None, description="YYYY-MM-DD")
    profile_picture_url: Optional[str] = Field(None)
    investment_style: Optional[str] = Field(None)
    risk_tolerance: Optional[str] = Field(None)
    interested_sectors: Optional[list[str]] = Field(None)
    theme_preference: Optional[str] = Field(None)
    language_preference: Optional[str] = Field(None)
    
    @validator('investment_style')
    def validate_investment_style(cls, v):
        if v and v not in ['long-term', 'short-term', 'mixed']:
            raise ValueError('Investment style must be long-term, short-term, or mixed')
        return v
    
    @validator('risk_tolerance')
    def validate_risk_tolerance(cls, v):
        if v and v not in ['low', 'medium', 'high']:
            raise ValueError('Risk tolerance must be low, medium, or high')
        return v
    
    @validator('theme_preference')
    def validate_theme(cls, v):
        if v and v not in ['light', 'dark']:
            raise ValueError('Theme must be light or dark')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Doe",
                "phone": "+919876543210",
                "investment_style": "long-term",
                "risk_tolerance": "medium",
                "interested_sectors": ["Technology", "Banking"],
                "theme_preference": "dark"
            }
        }


class UpdateUsernameRequest(BaseModel):
    """Request schema for updating username"""
    
    new_username: str = Field(..., min_length=3, max_length=50)
    
    @validator('new_username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v.lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "new_username": "newusername"
            }
        }


class UpdatePasswordRequest(BaseModel):
    """Request schema for updating password"""
    
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "OldPass123!",
                "new_password": "NewSecurePass123!"
            }
        }


class UpdateEmailPreferencesRequest(BaseModel):
    """Request schema for updating email preferences"""
    
    portfolio_reports: Optional[bool] = None
    security_alerts: Optional[bool] = None
    rate_limit_notifications: Optional[bool] = None
    system_notifications: Optional[bool] = None
    promotional_emails: Optional[bool] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "portfolio_reports": True,
                "security_alerts": True,
                "rate_limit_notifications": False,
                "system_notifications": True,
                "promotional_emails": False
            }
        }

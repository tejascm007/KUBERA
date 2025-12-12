"""
Admin Request Schemas
Pydantic models for admin endpoints
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional


class AdminLoginSendOTPRequest(BaseModel):
    """Request schema for admin login (Step 1: Send OTP)"""
    
    email: EmailStr = Field(..., description="Admin email address")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "admin@kubera.com"
            }
        }


class AdminLoginVerifyOTPRequest(BaseModel):
    """Request schema for admin OTP verification (Step 2: Verify OTP)"""
    
    email: EmailStr = Field(..., description="Admin email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")
    
    @validator('otp')
    def validate_otp(cls, v):
        if not v.isdigit():
            raise ValueError('OTP must contain only digits')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "admin@kubera.com",
                "otp": "123456"
            }
        }


class UpdateRateLimitGlobalRequest(BaseModel):
    """Request schema for updating global rate limits"""
    
    burst_limit_per_minute: Optional[int] = Field(None, gt=0, description="Prompts per minute")
    per_chat_limit: Optional[int] = Field(None, gt=0, description="Prompts per chat")
    per_hour_limit: Optional[int] = Field(None, gt=0, description="Prompts per hour")
    per_day_limit: Optional[int] = Field(None, gt=0, description="Prompts per day")
    
    class Config:
        json_schema_extra = {
            "example": {
                "burst_limit_per_minute": 15,
                "per_chat_limit": 75,
                "per_hour_limit": 200,
                "per_day_limit": 1500
            }
        }


class UpdateRateLimitUserRequest(BaseModel):
    """Request schema for updating user-specific rate limits"""
    
    burst_limit_per_minute: Optional[int] = Field(None, gt=0)
    per_chat_limit: Optional[int] = Field(None, gt=0)
    per_hour_limit: Optional[int] = Field(None, gt=0)
    per_day_limit: Optional[int] = Field(None, gt=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "burst_limit_per_minute": 20,
                "per_chat_limit": 100,
                "per_hour_limit": 300,
                "per_day_limit": 2000
            }
        }


class WhitelistUserRequest(BaseModel):
    """Request schema for whitelisting a user (no rate limits)"""
    
    user_id: str = Field(..., description="User UUID to whitelist")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }


class UpdatePortfolioReportSettingsRequest(BaseModel):
    """Request schema for updating portfolio report settings"""
    
    frequency: str = Field(..., description="disabled, daily, weekly, or monthly")
    send_time: str = Field(..., description="Time in HH:MM:SS format (IST)")
    send_day_weekly: Optional[int] = Field(None, ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")
    send_day_monthly: Optional[int] = Field(None, ge=1, le=28, description="Day of month (1-28)")
    
    @validator('frequency')
    def validate_frequency(cls, v):
        if v not in ['disabled', 'daily', 'weekly', 'monthly']:
            raise ValueError('Frequency must be disabled, daily, weekly, or monthly')
        return v
    
    @validator('send_day_weekly', pre=True)
    def validate_day_weekly(cls, v, values):
        if values.get('frequency') == 'weekly' and v is None:
            raise ValueError('send_day_weekly is required for weekly frequency')
        # Convert string to int if needed (frontend may send as string)
        if v is not None and isinstance(v, str):
            try:
                v = int(v)
            except ValueError:
                raise ValueError('send_day_weekly must be an integer 0-6')
        return v
    
    @validator('send_day_monthly')
    def validate_day_monthly(cls, v, values):
        if values.get('frequency') == 'monthly' and not v:
            raise ValueError('send_day_monthly is required for monthly frequency')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "frequency": "weekly",
                "send_time": "09:00:00",
                "send_day_weekly": 0
            }
        }


class DeactivateUserRequest(BaseModel):
    """Request schema for deactivating a user"""
    
    reason: Optional[str] = Field(None, max_length=500, description="Reason for deactivation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Multiple violations of terms of service"
            }
        }


class SystemControlRequest(BaseModel):
    """Request schema for system control (stop/start/restart)"""
    
    action: str = Field(..., description="stop, start, or restart")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for action")
    
    @validator('action')
    def validate_action(cls, v):
        if v not in ['stop', 'start', 'restart']:
            raise ValueError('Action must be stop, start, or restart')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "action": "restart",
                "reason": "System maintenance"
            }
        }

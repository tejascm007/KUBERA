"""
Authentication Response Schemas
Pydantic models for auth endpoint responses
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class TokenResponse(BaseModel):
    """Response schema for login and token refresh"""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400
            }
        }


class UserInfoResponse(BaseModel):
    """Response schema for user information"""
    
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
    theme_preference: str
    language_preference: str
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "phone": "+919876543210",
                "investment_style": "long-term",
                "risk_tolerance": "medium",
                "interested_sectors": ["Technology", "Banking"],
                "account_status": "active",
                "email_verified": True,
                "theme_preference": "light",
                "language_preference": "en",
                "created_at": "2024-01-15T10:30:00+05:30",
                "last_login_at": "2024-12-05T11:00:00+05:30"
            }
        }


class RegisterStepOneResponse(BaseModel):
    """Response schema for registration step 1 (OTP sent)"""
    
    success: bool = True
    message: str
    email: EmailStr
    otp_expires_in: int  # minutes
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "OTP sent to your email",
                "email": "user@example.com",
                "otp_expires_in": 10
            }
        }


class VerifyOTPResponse(BaseModel):
    """Response schema for OTP verification"""
    
    success: bool = True
    message: str
    email: EmailStr
    verified: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "OTP verified successfully",
                "email": "user@example.com",
                "verified": True
            }
        }


class CompleteRegistrationResponse(BaseModel):
    """Response schema for complete registration"""
    
    success: bool = True
    message: str
    user: UserInfoResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Registration completed successfully",
                "user": {
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "user@example.com",
                    "username": "johndoe",
                    "full_name": "John Doe"
                },
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }


class LoginResponse(BaseModel):
    """Response schema for login"""
    
    success: bool = True
    message: str
    user: UserInfoResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class CheckUsernameResponse(BaseModel):
    """Response schema for username availability check"""
    
    available: bool
    username: str
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "available": True,
                "username": "johndoe",
                "message": "Username is available"
            }
        }


class LogoutResponse(BaseModel):
    """Response schema for logout"""
    
    success: bool = True
    message: str = "Logged out successfully"


# ==========================================
# FORGOT PASSWORD SCHEMAS
# ==========================================

class ForgotPasswordResponse(BaseModel):
    """Response for forgot password initiation"""
    success: bool
    message: str
    email: str
    otp_expires_in: int = Field(default=10, description="OTP expiration in minutes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Password reset OTP sent to your email",
                "email": "user@example.com",
                "otp_expires_in": 10
            }
        }


class ForgotPasswordConfirmResponse(BaseModel):
    """Response for forgot password confirmation"""
    success: bool
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Password reset successful. You can now login with your new password."
            }
        }
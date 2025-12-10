"""
Authentication Request Schemas
Pydantic models for auth endpoints
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
import re


class RegisterRequest(BaseModel):
    """Request schema for user registration (Step 1: Send OTP)"""
    
    email: EmailStr = Field(..., description="User email address")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class VerifyOTPRequest(BaseModel):
    """Request schema for OTP verification (Step 2: Verify OTP)"""
    
    email: EmailStr = Field(..., description="User email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")
    
    @validator('otp')
    def validate_otp(cls, v):
        if not v.isdigit():
            raise ValueError('OTP must contain only digits')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "otp": "123456"
            }
        }


class CompleteRegistrationRequest(BaseModel):
    """Request schema for completing registration (Step 3: Set profile)"""
    
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=8, description="Password")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name")
    
    # Optional profile fields
    phone: Optional[str] = Field(None, description="Phone number")
    date_of_birth: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD)")
    
    # Investment preferences (optional, can skip)
    investment_style: Optional[str] = Field(None, description="long-term, short-term, or mixed")
    risk_tolerance: Optional[str] = Field(None, description="low, medium, or high")
    interested_sectors: Optional[list[str]] = Field(None, description="Array of sectors")
    
    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v.lower()
    
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
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "password": "SecurePass123!",
                "full_name": "John Doe",
                "phone": "+919876543210",
                "investment_style": "long-term",
                "risk_tolerance": "medium",
                "interested_sectors": ["Technology", "Banking", "Healthcare"]
            }
        }


class LoginRequest(BaseModel):
    """Request schema for user login"""
    username: str = Field(..., min_length=5, description="User's username")
    password: str = Field(..., description="Password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "SecurePass123!"
            }
        }


class RefreshTokenRequest(BaseModel):
    """Request schema for refreshing access token"""
    
    refresh_token: str = Field(..., description="Refresh token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class CheckUsernameRequest(BaseModel):
    """Request schema for checking username availability"""
    
    username: str = Field(..., min_length=3, max_length=50, description="Username to check")
    
    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v.lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe"
            }
        }


class PasswordResetRequest(BaseModel):
    """Request schema for password reset (Step 1: Send OTP)"""
    
    email: EmailStr = Field(..., description="User email address")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class PasswordResetConfirmRequest(BaseModel):
    """Request schema for confirming password reset (Step 2: Verify OTP & Set password)"""
    
    email: EmailStr = Field(..., description="User email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @validator('otp')
    def validate_otp(cls, v):
        if not v.isdigit():
            raise ValueError('OTP must contain only digits')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "otp": "123456",
                "new_password": "NewSecurePass123!"
            }
        }


# ==========================================
# FORGOT PASSWORD SCHEMAS
# ==========================================

class ForgotPasswordRequest(BaseModel):
    """Request schema for initiating forgot password flow"""
    email: str = Field(..., description="User's registered email")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class ForgotPasswordVerifyRequest(BaseModel):
    """Request schema for verifying OTP and resetting password"""
    email: str = Field(..., description="User's email")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")
    new_password: str = Field(
        ..., 
        min_length=8, 
        description="New password (min 8 chars, must contain uppercase, lowercase, number, special char)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "otp": "123456",
                "new_password": "NewSecurePass@123"
            }
        }

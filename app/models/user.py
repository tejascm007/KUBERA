from datetime import datetime, date
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    full_name: str
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None

    investment_style: Optional[str] = Field(
        default=None,
        description="value, growth, dividend, swing",
    )
    risk_tolerance: Optional[str] = Field(
        default=None,
        description="low, medium, high",
    )
    interested_sectors: Optional[List[str]] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    investment_style: Optional[str] = None
    risk_tolerance: Optional[str] = None
    interested_sectors: Optional[List[str]] = None


class UserInDBBase(UserBase):
    user_id: str
    account_status: str
    email_verified: bool = False
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # Pydantic v2


class User(UserInDBBase):
    """Public user model (no password hash)."""
    pass


class UserInDB(UserInDBBase):
    password_hash: str


class UserPreferences(BaseModel):
    user_id: str
    portfolio_reports: bool = True
    rate_limit_notifications: bool = True
    system_notifications: bool = True
    security_alerts: bool = True

    class Config:
        from_attributes = True

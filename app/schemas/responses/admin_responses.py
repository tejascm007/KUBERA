"""
Admin Response Schemas
Pydantic models for admin endpoint responses
"""

from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime


class AdminTokenResponse(BaseModel):
    """Response schema for admin login"""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    admin_id: str
    email: EmailStr
    full_name: str
    is_super_admin: bool


class DashboardStatsResponse(BaseModel):
    """Response schema for admin dashboard statistics"""
    
    total_users: int
    active_users: int
    deactivated_users: int
    total_chats: int
    total_messages: int
    total_prompts_today: int
    total_prompts_this_week: int
    total_prompts_this_month: int
    total_rate_limit_violations: int
    violations_today: int
    system_status: str
    portfolio_report_frequency: str
    portfolio_report_last_sent: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_users": 1250,
                "active_users": 1180,
                "deactivated_users": 70,
                "total_chats": 8543,
                "total_messages": 45321,
                "total_prompts_today": 3421,
                "total_prompts_this_week": 18765,
                "total_prompts_this_month": 76543,
                "total_rate_limit_violations": 234,
                "violations_today": 12,
                "system_status": "running",
                "portfolio_report_frequency": "weekly",
                "portfolio_report_last_sent": "2024-12-02T09:00:00+05:30"
            }
        }


class UserListItemResponse(BaseModel):
    """Response schema for user list item"""
    
    user_id: str
    email: EmailStr
    username: str
    full_name: str
    account_status: str
    email_verified: bool
    total_chats: int
    total_prompts: int
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UserListResponse(BaseModel):
    """Response schema for user list"""
    
    success: bool = True
    total_users: int
    users: List[UserListItemResponse]


class UserDetailResponse(BaseModel):
    """Response schema for detailed user info"""
    
    user_id: str
    email: EmailStr
    username: str
    full_name: str
    phone: Optional[str] = None
    account_status: str
    email_verified: bool
    investment_style: Optional[str] = None
    risk_tolerance: Optional[str] = None
    interested_sectors: Optional[List[str]] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    # Statistics
    total_chats: int
    total_prompts: int
    prompts_today: int
    prompts_this_week: int
    prompts_this_month: int
    
    # Rate limits
    current_rate_limits: Dict[str, int]
    rate_limit_violations: int
    
    # Portfolio
    total_portfolio_entries: int


class RateLimitConfigResponse(BaseModel):
    """Response schema for rate limit configuration"""
    
    config_id: str
    burst_limit_per_minute: int
    per_chat_limit: int
    per_hour_limit: int
    per_day_limit: int
    user_specific_overrides: Dict[str, Any]
    whitelisted_users: List[str]
    updated_at: datetime


class UpdateRateLimitResponse(BaseModel):
    """Response schema for updating rate limits"""
    
    success: bool = True
    message: str
    config: RateLimitConfigResponse


class PortfolioReportSettingsResponse(BaseModel):
    """Response schema for portfolio report settings"""
    
    frequency: str
    send_time: str
    send_day_weekly: Optional[str] = None
    send_day_monthly: Optional[int] = None
    timezone: str
    last_sent: Optional[datetime] = None
    next_scheduled: Optional[datetime] = None


class UpdatePortfolioReportResponse(BaseModel):
    """Response schema for updating portfolio report settings"""
    
    success: bool = True
    message: str
    settings: PortfolioReportSettingsResponse


class DeactivateUserResponse(BaseModel):
    """Response schema for deactivating user"""
    
    success: bool = True
    message: str
    user_id: str
    new_status: str


class SystemControlResponse(BaseModel):
    """Response schema for system control"""
    
    success: bool = True
    message: str
    action: str
    system_status: str
    timestamp: datetime


class RateLimitViolationResponse(BaseModel):
    """Response schema for rate limit violation"""
    
    violation_id: str
    user_id: str
    user_email: EmailStr
    chat_id: Optional[str] = None
    violation_type: str
    limit_value: int
    prompts_used: int
    action_taken: str
    user_message: Optional[str] = None
    violated_at: datetime


class RateLimitViolationsListResponse(BaseModel):
    """Response schema for violations list"""
    
    success: bool = True
    total_violations: int
    violations: List[RateLimitViolationResponse]


class ActivityLogResponse(BaseModel):
    """Response schema for admin activity log"""
    
    log_id: str
    admin_id: str
    admin_email: EmailStr
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    performed_at: datetime


class ActivityLogListResponse(BaseModel):
    """Response schema for activity log list"""
    
    success: bool = True
    total_logs: int
    logs: List[ActivityLogResponse]

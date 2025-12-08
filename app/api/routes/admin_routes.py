"""
Admin Routes
Endpoints for admin operations (15+ endpoints)
"""

from fastapi import APIRouter, Depends, status, Path, Query
from typing import Dict, Any, Optional
from app.db.repositories.rate_limit_repository import RateLimitRepository
from app.db.repositories.system_repository import SystemRepository    
from app.db.repositories.admin_repository import AdminRepository
from datetime import datetime


from app.schemas.requests.admin_requests import (
    AdminLoginSendOTPRequest,
    AdminLoginVerifyOTPRequest,
    UpdateRateLimitGlobalRequest,
    UpdateRateLimitUserRequest,
    WhitelistUserRequest,
    UpdatePortfolioReportSettingsRequest,
    DeactivateUserRequest,
    SystemControlRequest
)
from app.schemas.responses.admin_responses import (
    AdminTokenResponse,
    DashboardStatsResponse,
    UserListResponse,
    UserDetailResponse,
    RateLimitConfigResponse,
    UpdateRateLimitResponse,
    PortfolioReportSettingsResponse,
    UpdatePortfolioReportResponse,
    DeactivateUserResponse,
    SystemControlResponse,
    RateLimitViolationsListResponse,
    ActivityLogListResponse
)
from app.services.admin_service import AdminService
from app.services.rate_limit_service import RateLimitService
from app.core.dependencies import get_current_admin
from app.core.database import get_db_pool

router = APIRouter(prefix="/admin", tags=["Admin"])


# ============================================================================
# ADMIN AUTHENTICATION
# ============================================================================

@router.post(
    "/login/send-otp",
    status_code=status.HTTP_200_OK,
    summary="Admin login - Send OTP",
    description="Send OTP to admin email for login"
)
async def admin_login_send_otp(request: AdminLoginSendOTPRequest):
    """
    **Admin Login: Step 1 - Send OTP**
    
    - Validates admin email exists
    - Sends 6-digit OTP to admin email
    - OTP expires in 10 minutes
    """
    db_pool = await get_db_pool()
    admin_service = AdminService(db_pool)
    
    result = await admin_service.admin_login_send_otp(request.email)
    return result


@router.post(
    "/login/verify-otp",
    response_model=AdminTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin login - Verify OTP",
    description="Verify OTP and receive admin access token"
)
async def admin_login_verify_otp(request: AdminLoginVerifyOTPRequest):
    """
    **Admin Login: Step 2 - Verify OTP**
    
    - Verifies OTP
    - Returns admin access token
    - Token expires in 24 hours
    """
    db_pool = await get_db_pool()
    admin_service = AdminService(db_pool)
    
    result = await admin_service.admin_login_verify_otp(request.email, request.otp)
    return result


# ============================================================================
# DASHBOARD
# ============================================================================

@router.get(
    "/dashboard",
    response_model=DashboardStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dashboard statistics",
    description="Get comprehensive admin dashboard statistics"
)
async def get_dashboard_stats(current_admin: Dict = Depends(get_current_admin)):
    """
    **Admin Dashboard Statistics**
    
    Returns comprehensive stats:
    - Total users, active, deactivated
    - Total chats and messages
    - Prompt usage (today, week, month)
    - Rate limit violations
    - System status
    - Portfolio report settings
    """
    db_pool = await get_db_pool()
    admin_service = AdminService(db_pool)
    
    stats = await admin_service.get_dashboard_stats()
    return stats


# ============================================================================
# USER MANAGEMENT
# ============================================================================

@router.get(
    "/users",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all users",
    description="Get list of all users with pagination"
)
async def get_all_users(
    limit: int = Query(100, ge=1, le=500, description="Number of users"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    account_status: Optional[str] = Query(None, description="Filter by status: active, deactivated, suspended"),
    current_admin: Dict = Depends(get_current_admin)
):
    """
    **Get All Users**
    
    - Paginated user list
    - Filter by account status
    - Includes basic user info and stats
    """
    db_pool = await get_db_pool()
    admin_service = AdminService(db_pool)
    
    result = await admin_service.get_all_users(limit, offset, account_status)
    return result


@router.get(
    "/users/{user_id}",
    response_model=UserDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user details",
    description="Get detailed information about a specific user"
)
async def get_user_detail(
    user_id: str = Path(..., description="User UUID"),
    current_admin: Dict = Depends(get_current_admin)
):
    """
    **Get User Details**
    
    Returns comprehensive user information:
    - Profile details
    - Usage statistics
    - Rate limit info
    - Portfolio count
    - Recent activity
    """
    db_pool = await get_db_pool()
    admin_service = AdminService(db_pool)
    
    # Use the service method that handles UUID conversion
    user = await admin_service.get_user_detail(user_id)
    return user


@router.put(
    "/users/{user_id}/deactivate",
    response_model=DeactivateUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate user",
    description="Deactivate a user account"
)
async def deactivate_user(
    user_id: str = Path(..., description="User UUID"),
    request: DeactivateUserRequest = None,
    current_admin: Dict = Depends(get_current_admin)
):
    """
    **Deactivate User**
    
    - Sets account status to 'deactivated'
    - User cannot login
    - Sends notification email to user
    - Logs admin action
    """
    db_pool = await get_db_pool()
    admin_service = AdminService(db_pool)
    
    user = await admin_service.deactivate_user(
        user_id,
        current_admin["admin_id"],
        request.reason if request else None
    )
    
    return {
        "success": True,
        "message": "User deactivated successfully",
        "user_id": user_id,
        "new_status": "deactivated"
    }


@router.put(
    "/users/{user_id}/reactivate",
    status_code=status.HTTP_200_OK,
    summary="Reactivate user",
    description="Reactivate a deactivated user account"
)
async def reactivate_user(
    user_id: str = Path(..., description="User UUID"),
    current_admin: Dict = Depends(get_current_admin)
):
    """
    **Reactivate User**
    
    - Sets account status to 'active'
    - User can login again
    - Sends notification email
    - Logs admin action
    """
    db_pool = await get_db_pool()
    admin_service = AdminService(db_pool)
    
    user = await admin_service.reactivate_user(user_id, current_admin["admin_id"])
    
    return {
        "success": True,
        "message": "User reactivated successfully",
        "user_id": user_id,
        "new_status": "active"
    }


# ============================================================================
# RATE LIMIT MANAGEMENT
# ============================================================================

@router.get(
    "/rate-limits/config",
    response_model=RateLimitConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Get rate limit configuration",
    description="Get current global and user-specific rate limits"
)
async def get_rate_limit_config(current_admin: Dict = Depends(get_current_admin)):
    """
    **Get Rate Limit Configuration**
    
    Returns:
    - Global rate limits (burst, per-chat, hourly, daily)
    - User-specific overrides
    - Whitelisted users
    """
    db_pool = await get_db_pool()
    rate_limit_service = RateLimitService(db_pool)
    
    config = await rate_limit_service.get_rate_limit_config()
    return config


@router.put(
    "/rate-limits/global",
    response_model=UpdateRateLimitResponse,
    status_code=status.HTTP_200_OK,
    summary="Update global rate limits",
    description="Update global rate limit settings"
)
async def update_global_rate_limits(
    request: UpdateRateLimitGlobalRequest,
    current_admin: Dict = Depends(get_current_admin)
):
    """
    **Update Global Rate Limits**
    
    - Updates default rate limits for all users
    - Does not affect user-specific overrides
    - Logs admin action
    """
    db_pool = await get_db_pool()
    rate_limit_service = RateLimitService(db_pool)
    
    updates = request.dict(exclude_unset=True)
    config = await rate_limit_service.update_global_rate_limits(
        updates,
        current_admin["admin_id"]
    )
    
    return {
        "success": True,
        "message": "Global rate limits updated successfully",
        "config": config
    }


@router.put(
    "/rate-limits/user/{user_id}",
    response_model=UpdateRateLimitResponse,
    status_code=status.HTTP_200_OK,
    summary="Set user-specific rate limits",
    description="Set custom rate limits for a specific user"
)
async def set_user_rate_limits(
    user_id: str = Path(..., description="User UUID"),
    request: UpdateRateLimitUserRequest = None,
    current_admin: Dict = Depends(get_current_admin)
):
    """
    **Set User-Specific Rate Limits**
    
    - Override global limits for specific user
    - Higher or lower limits than default
    - Logs admin action
    """
    db_pool = await get_db_pool()
    rate_limit_service = RateLimitService(db_pool)
    
    limits = request.dict(exclude_unset=True)
    await rate_limit_service.set_user_rate_limits(
        user_id,
        limits,
        current_admin["admin_id"]
    )
    
    config = await rate_limit_service.get_rate_limit_config()
    
    return {
        "success": True,
        "message": "User rate limits updated successfully",
        "config": config
    }


@router.post(
    "/rate-limits/whitelist",
    status_code=status.HTTP_200_OK,
    summary="Add user to whitelist",
    description="Add user to whitelist (no rate limits)"
)
async def whitelist_user(
    request: WhitelistUserRequest,
    current_admin: Dict = Depends(get_current_admin)
):
    """
    **Whitelist User**
    
    - User bypasses all rate limits
    - Use for VIP users or testing
    - Logs admin action
    """
    db_pool = await get_db_pool()
    rate_limit_service = RateLimitService(db_pool)
    
    await rate_limit_service.whitelist_user(request.user_id, current_admin["admin_id"])
    
    return {
        "success": True,
        "message": "User whitelisted successfully",
        "user_id": request.user_id
    }


@router.delete(
    "/rate-limits/whitelist/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove user from whitelist",
    description="Remove user from whitelist"
)
async def remove_whitelist(
    user_id: str = Path(..., description="User UUID"),
    current_admin: Dict = Depends(get_current_admin)
):
    """
    **Remove User from Whitelist**
    
    - User will be subject to rate limits again
    - Logs admin action
    """
    db_pool = await get_db_pool()
    rate_limit_service = RateLimitService(db_pool)
    
    await rate_limit_service.remove_whitelist(user_id, current_admin["admin_id"])
    
    return {
        "success": True,
        "message": "User removed from whitelist",
        "user_id": user_id
    }


@router.post(
    "/rate-limits/reset/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Reset user rate limit counters",
    description="Reset all rate limit counters for a user"
)
async def reset_user_rate_limits(
    user_id: str = Path(..., description="User UUID"),
    current_admin: Dict = Depends(get_current_admin)
):
    """
    **Reset User Rate Limit Counters**
    
    - Resets all counters (burst, hourly, daily)
    - User can send prompts again immediately
    - Use for support/troubleshooting
    """
    db_pool = await get_db_pool()
    rate_limit_service = RateLimitService(db_pool)
    
    await rate_limit_service.reset_user_limits(user_id)
    
    return {
        "success": True,
        "message": "User rate limit counters reset",
        "user_id": user_id
    }


# ============================================================================
# RATE LIMIT VIOLATIONS
# ============================================================================

@router.get(
    "/rate-limits/violations",
    response_model=RateLimitViolationsListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get rate limit violations",
    description="Get list of rate limit violations"
)
async def get_violations(
    limit: int = Query(100, ge=1, le=500, description="Number of violations"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    violation_type: Optional[str] = Query(None, description="Filter by type: burst, per_chat, hourly, daily"),
    current_admin: Dict = Depends(get_current_admin)
):
    """
    **Get Rate Limit Violations**
    
    - List of all rate limit violations
    - Filter by violation type
    - Includes user info and timestamps
    """
    db_pool = await get_db_pool()
    rate_limit_service = RateLimitService(db_pool)
    
    violations = await rate_limit_service.get_violations(limit, offset, violation_type)
    
    rate_limit_repo = RateLimitRepository(db_pool)
    total = await rate_limit_repo.count_violations()
    
    return {
        "success": True,
        "total_violations": total,
        "violations": violations
    }


# ============================================================================
# PORTFOLIO REPORT SETTINGS
# ============================================================================

@router.get(
    "/portfolio-reports/settings",
    response_model=PortfolioReportSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get portfolio report settings",
    description="Get current portfolio report schedule settings"
)
async def get_portfolio_report_settings(current_admin: Dict = Depends(get_current_admin)):
    """
    **Get Portfolio Report Settings**
    
    - Frequency (disabled, daily, weekly, monthly)
    - Send time
    - Day of week/month
    - Next scheduled run
    """
    db_pool = await get_db_pool()
    
    system_repo = SystemRepository(db_pool)
    system_status = await system_repo.get_system_status()
    
    # ========================================================================
    # FIX: Convert time and int to strings
    # ========================================================================
    send_time = system_status['portfolio_report_send_time']
    if send_time and hasattr(send_time, 'isoformat'):
        send_time = send_time.isoformat()
    
    return {
        "frequency": system_status['portfolio_report_frequency'],
        "send_time": send_time,
        "send_day_weekly": str(system_status['portfolio_report_send_day_weekly']) if system_status['portfolio_report_send_day_weekly'] else None,
        "send_day_monthly": str(system_status['portfolio_report_send_day_monthly']) if system_status['portfolio_report_send_day_monthly'] else None,
        "timezone": "Asia/Kolkata",
        "last_sent": system_status['portfolio_report_last_sent'],
        "next_scheduled": system_status['portfolio_report_next_scheduled']
    }


@router.put(
    "/portfolio-reports/settings",
    response_model=UpdatePortfolioReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Update portfolio report settings",
    description="Update portfolio report schedule"
)
async def update_portfolio_report_settings(
    request: UpdatePortfolioReportSettingsRequest,
    current_admin: Dict = Depends(get_current_admin)
):
    """
    **Update Portfolio Report Settings**
    
    - Set frequency (disabled, daily, weekly, monthly)
    - Set send time (IST)
    - Set day for weekly/monthly reports
    - Logs admin action
    """
    db_pool = await get_db_pool()
    
    system_repo = SystemRepository(db_pool)
    
    settings_dict = request.dict()
    updated = await system_repo.update_portfolio_report_settings(settings_dict)
    
    # ========================================================================
    # FIX: Convert time and int to strings
    # ========================================================================
    send_time = updated['portfolio_report_send_time']
    if send_time and hasattr(send_time, 'isoformat'):
        send_time = send_time.isoformat()
    
    return {
        "success": True,
        "message": "Portfolio report settings updated successfully",
        "settings": {
            "frequency": updated['portfolio_report_frequency'],
            "send_time": send_time,
            "send_day_weekly": str(updated['portfolio_report_send_day_weekly']) if updated['portfolio_report_send_day_weekly'] else None,
            "send_day_monthly": str(updated['portfolio_report_send_day_monthly']) if updated['portfolio_report_send_day_monthly'] else None,
            "timezone": "Asia/Kolkata",
            "last_sent": updated['portfolio_report_last_sent'],
            "next_scheduled": updated['portfolio_report_next_scheduled']
        }
    }



# ============================================================================
# SYSTEM CONTROL
# ============================================================================

@router.post(
    "/system/control",
    response_model=SystemControlResponse,
    status_code=status.HTTP_200_OK,
    summary="System control",
    description="Stop, start, or restart the system"
)
async def system_control(
    request: SystemControlRequest,
    current_admin: Dict = Depends(get_current_admin)
):
    """
    **System Control**
    
    Actions:
    - **stop**: Stop accepting new prompts (maintenance mode)
    - **start**: Resume normal operations
    - **restart**: Restart system services
    
    - Sends notification email to all users
    - Logs admin action
    """
    db_pool = await get_db_pool()
    admin_service = AdminService(db_pool)
    
    result = await admin_service.system_control(
        request.action,
        current_admin["admin_id"],
        request.reason
    )
    
    
    return {
        "success": True,
        "message": f"System {request.action} completed",
        "action": request.action,
        "system_status": result['current_status'],
        "timestamp": datetime.now()
    }


# ============================================================================
# ACTIVITY LOGS
# ============================================================================

@router.get(
    "/activity-logs",
    response_model=ActivityLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get admin activity logs",
    description="Get audit trail of admin actions"
)
async def get_activity_logs(
    limit: int = Query(100, ge=1, le=500, description="Number of logs"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    admin_id: Optional[str] = Query(None, description="Filter by admin ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    current_admin: Dict = Depends(get_current_admin)
):
    """
    **Get Admin Activity Logs**
    
    - Complete audit trail of admin actions
    - Filter by admin or action type
    - Includes old/new values for changes
    """
    db_pool = await get_db_pool()
    
    admin_repo = AdminRepository(db_pool)
    
    logs = await admin_repo.get_activity_logs(limit, offset, admin_id, action)
    total = await admin_repo.count_activity_logs(admin_id)
    
    return {
        "success": True,
        "total_logs": total,
        "logs": logs
    }

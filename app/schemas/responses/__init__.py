"""
Response Schemas Module
All API response schemas
"""

from app.schemas.responses.auth_responses import *
from app.schemas.responses.user_responses import *
from app.schemas.responses.portfolio_responses import *
from app.schemas.responses.chat_responses import *
from app.schemas.responses.admin_responses import *

__all__ = [
    # Auth
    "TokenResponse",
    "UserInfoResponse",
    "RegisterStepOneResponse",
    "VerifyOTPResponse",
    "CompleteRegistrationResponse",
    "LoginResponse",
    "CheckUsernameResponse",
    "LogoutResponse",
    
    # User
    "ProfileResponse",
    "UpdateProfileResponse",
    "UpdateUsernameResponse",
    "UpdatePasswordResponse",
    "EmailPreferencesResponse",
    "UpdateEmailPreferencesResponse",
        
    # Portfolio
    "PortfolioEntryResponse",
    "PortfolioSummaryResponse",
    "PortfolioListResponse",
    "AddPortfolioResponse",
    "UpdatePortfolioResponse",
    "DeletePortfolioResponse",
    
    # Chat
    "ChatResponse",
    "ChatListResponse",
    "CreateChatResponse",
    "RenameChatResponse",
    "DeleteChatResponse",
    "MessageResponse",
    "ChatMessagesResponse",
    "WebSocketMessageResponse",
    
    # Admin
    "AdminTokenResponse",
    "DashboardStatsResponse",
    "UserListItemResponse",
    "UserListResponse",
    "UserDetailResponse",
    "RateLimitConfigResponse",
    "UpdateRateLimitResponse",
    "PortfolioReportSettingsResponse",
    "UpdatePortfolioReportResponse",
    "DeactivateUserResponse",
    "SystemControlResponse",
    "RateLimitViolationResponse",
    "RateLimitViolationsListResponse",
    "ActivityLogResponse",
    "ActivityLogListResponse"
]

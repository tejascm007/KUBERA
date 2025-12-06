"""
Request Schemas Module
All API request schemas
"""

from app.schemas.requests.auth_requests import (
    RegisterRequest,
    VerifyOTPRequest,
    CompleteRegistrationRequest,
    LoginRequest,
    RefreshTokenRequest,
    CheckUsernameRequest,
    PasswordResetRequest,
    PasswordResetConfirmRequest
)

from app.schemas.requests.user_requests import *
from app.schemas.requests.portfolio_requests import *
from app.schemas.requests.chat_requests import *
from app.schemas.requests.admin_requests import *

# Create aliases for backward compatibility
RegisterStep1Request = RegisterRequest
RegisterStep2Request = VerifyOTPRequest
RegisterStep3Request = CompleteRegistrationRequest
PasswordResetRequestRequest = PasswordResetRequest

__all__ = [
    # Auth - Original names
    "RegisterRequest",
    "VerifyOTPRequest",
    "CompleteRegistrationRequest",
    "LoginRequest",
    "RefreshTokenRequest",
    "CheckUsernameRequest",
    "PasswordResetRequest",
    "PasswordResetConfirmRequest",
    
    # Auth - Aliases
    "RegisterStep1Request",
    "RegisterStep2Request",
    "RegisterStep3Request",
    "PasswordResetRequestRequest",
    
    # User
    "UpdateProfileRequest",
    "UpdateUsernameRequest",
    "UpdatePasswordRequest",
    "UpdateEmailPreferencesRequest",
    
    # Portfolio
    "AddPortfolioRequest",
    "UpdatePortfolioRequest",
    
    # Chat
    "CreateChatRequest",
    "RenameChatRequest",
    "SendMessageRequest",

    
    # Admin
    "AdminLoginSendOTPRequest",
    "AdminLoginVerifyOTPRequest",
    "UpdateRateLimitGlobalRequest",
    "UpdateRateLimitUserRequest",
    "WhitelistUserRequest",
    "UpdatePortfolioReportSettingsRequest",
    "DeactivateUserRequest",
    "SystemControlRequest"

]

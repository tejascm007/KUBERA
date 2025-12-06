"""
Authentication Routes
Endpoints for registration, login, logout, token refresh
"""

from fastapi import APIRouter, Depends, status, Body
from typing import Dict, Any

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
from app.schemas.responses.auth_responses import (
    RegisterStepOneResponse,
    VerifyOTPResponse,
    CompleteRegistrationResponse,
    LoginResponse,
    TokenResponse,
    CheckUsernameResponse,
    LogoutResponse
)
from app.services.auth_service import AuthService
from app.core.dependencies import get_current_user
from app.core.database import get_db_pool

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# REGISTRATION FLOW (3 STEPS)
# ============================================================================

@router.post(
    "/register/step1",
    response_model=RegisterStepOneResponse,
    status_code=status.HTTP_200_OK,
    summary="Step 1: Send OTP to email",
    description="Start registration by sending OTP to email address"
)
async def register_step_1(request: RegisterRequest):
    """
    **Registration Step 1: Send OTP**
    
    - Validates email is not already registered
    - Generates 6-digit OTP
    - Sends OTP to email
    - OTP expires in 10 minutes
    """
    db_pool = await get_db_pool()
    auth_service = AuthService(db_pool)
    
    result = await auth_service.register_step_1_send_otp(request.email)
    return result


@router.post(
    "/register/step2",
    response_model=VerifyOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Step 2: Verify OTP",
    description="Verify the OTP sent to email"
)
async def register_step_2(request: VerifyOTPRequest):
    """
    **Registration Step 2: Verify OTP**
    
    - Verifies the 6-digit OTP
    - Maximum 3 attempts allowed
    - OTP must not be expired
    """
    db_pool = await get_db_pool()
    auth_service = AuthService(db_pool)
    
    result = await auth_service.register_step_2_verify_otp(
        email=request.email,
        otp=request.otp
    )
    return result


@router.post(
    "/register/step3",
    response_model=CompleteRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Step 3: Complete registration",
    description="Complete registration with user details and password"
)
async def register_step_3(request: CompleteRegistrationRequest):
    """
    **Registration Step 3: Complete Registration**
    
    - Creates user account
    - Validates username availability
    - Validates password strength
    - Sends welcome email
    - Returns access and refresh tokens
    """
    db_pool = await get_db_pool()
    auth_service = AuthService(db_pool)
    
    registration_data = request.dict()
    result = await auth_service.register_step_3_complete(registration_data)
    
    return result


# ============================================================================
# LOGIN
# ============================================================================

@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
    description="Authenticate user and receive access tokens"
)
async def login(request: LoginRequest):
    """
    **Login**
    
    - Authenticates user with email and password
    - Returns access token (24h expiry) and refresh token (30d expiry)
    - Updates last login timestamp
    """
    db_pool = await get_db_pool()
    auth_service = AuthService(db_pool)
    
    result = await auth_service.login(
        email=request.email,
        password=request.password
    )
    
    return result


# ============================================================================
# TOKEN REFRESH
# ============================================================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Get new access token using refresh token"
)
async def refresh_token(request: RefreshTokenRequest):
    """
    **Refresh Access Token**
    
    - Validates refresh token
    - Issues new access token
    - Refresh token remains valid
    """
    db_pool = await get_db_pool()
    auth_service = AuthService(db_pool)
    
    result = await auth_service.refresh_access_token(request.refresh_token)
    return result


# ============================================================================
# LOGOUT
# ============================================================================

@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout user",
    description="Revoke refresh token and logout"
)
async def logout(
    request: RefreshTokenRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    **Logout**
    
    - Revokes refresh token
    - User must login again to get new tokens
    """
    db_pool = await get_db_pool()
    auth_service = AuthService(db_pool)
    
    result = await auth_service.logout(request.refresh_token)
    return result


# ============================================================================
# USERNAME CHECK
# ============================================================================

@router.get(
    "/check-username/{username}",
    response_model=CheckUsernameResponse,
    status_code=status.HTTP_200_OK,
    summary="Check username availability",
    description="Check if username is available for registration"
)
async def check_username(username: str):
    """
    **Check Username Availability**
    
    - Returns whether username is available
    - Case-insensitive check
    """
    db_pool = await get_db_pool()
    auth_service = AuthService(db_pool)
    
    result = await auth_service.check_username_availability(username)
    return result


# ============================================================================
# PASSWORD RESET
# ============================================================================

@router.post(
    "/password-reset/send-otp",
    status_code=status.HTTP_200_OK,
    summary="Send OTP for password reset",
    description="Send OTP to email for password reset"
)
async def password_reset_send_otp(request: PasswordResetRequest):
    """
    **Password Reset: Send OTP**
    
    - Sends OTP to registered email
    - OTP expires in 10 minutes
    """
    db_pool = await get_db_pool()
    auth_service = AuthService(db_pool)
    
    result = await auth_service.password_reset_send_otp(request.email)
    return result


@router.post(
    "/password-reset/confirm",
    status_code=status.HTTP_200_OK,
    summary="Confirm password reset with OTP",
    description="Reset password using OTP verification"
)
async def password_reset_confirm(request: PasswordResetConfirmRequest):
    """
    **Password Reset: Confirm**
    
    - Verifies OTP
    - Updates password
    - Revokes all existing refresh tokens
    - Sends confirmation email
    """
    db_pool = await get_db_pool()
    auth_service = AuthService(db_pool)
    
    result = await auth_service.password_reset_confirm(
        email=request.email,
        otp=request.otp,
        new_password=request.new_password
    )
    return result

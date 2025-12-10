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
from app.schemas.requests.auth_requests import (
    ForgotPasswordRequest,
    ForgotPasswordVerifyRequest
)
from app.schemas.responses.auth_responses import (
    ForgotPasswordResponse,
    ForgotPasswordConfirmResponse
)
from app.exceptions.custom_exceptions import InvalidOTP, RateLimitExceeded, InvalidPassword

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
    summary="Login with username and password",
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
        username=request.username,
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



# ==========================================
# FORGOT PASSWORD ENDPOINTS
# ==========================================

@router.post(
    "/forgot-password/send-otp",
    response_model=ForgotPasswordResponse,
    summary="Send forgot password OTP",
    tags=["Auth - forgot Password Reset"]
)
async def send_forgot_password_otp(
    request: ForgotPasswordRequest
):
    """
    Send OTP to user's email for password reset
    
    Endpoint: POST /auth/password-reset/send-otp
    
    Request body:
    {
        "email": "user@example.com"
    }
    
    Response:
    {
        "success": true,
        "message": "Password reset OTP sent to your email",
        "email": "user@example.com",
        "otp_expires_in": 10
    }
    """
    db_pool = await get_db_pool()
    auth_service = AuthService(db_pool)
    
    try:
        result = await auth_service.send_forgot_password_otp(request.email)
        logger.info(f"Forgot password OTP sent to {request.email}")
        return result
        
    except UserNotFound as e:
        logger.warning(f"Forgot password request for non-existent user: {request.email}")
        raise e
    except RateLimitExceeded as e:
        logger.warning(f"Rate limit exceeded for {request.email}")
        raise e
    except Exception as e:
        logger.error(f"Error sending forgot password OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send reset OTP. Please try again."
        )


@router.post(
    "/forgot-password/confirm",
    response_model=ForgotPasswordConfirmResponse,
    summary="Reset password with OTP",
    tags=["Auth - forgot Password Reset"]
)
async def reset_password_with_otp(
    request: ForgotPasswordVerifyRequest
):
    """
    Reset password using OTP verification
    
    Endpoint: POST /auth/password-reset/confirm
    
    Request body:
    {
        "email": "user@example.com",
        "otp": "123456",
        "new_password": "NewSecurePass@123"
    }
    
    Response:
    {
        "success": true,
        "message": "Password reset successful. You can now login with your new password."
    }
    """
    db_pool = await get_db_pool()
    auth_service = AuthService(db_pool)
    
    try:
        result = await auth_service.reset_password_with_otp(
            email=request.email,
            otp_code=request.otp,
            new_password=request.new_password
        )
        logger.info(f"Password reset successful for {request.email}")
        return result
        
    except UserNotFound as e:
        logger.warning(f"Password reset for non-existent user: {request.email}")
        raise e
    except InvalidOTP as e:
        logger.warning(f"Invalid OTP for {request.email}")
        raise e
    except InvalidPassword as e:
        logger.warning(f"Invalid password for {request.email}")
        raise e
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password. Please try again."
        )

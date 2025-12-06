"""
Authentication Service
Business logic for user authentication, registration, login
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

from app.db.repositories.user_repository import UserRepository
from app.db.repositories.otp_repository import OTPRepository
from app.db.repositories.token_repository import TokenRepository
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    generate_otp,
    verify_otp,
    is_otp_expired,
    validate_password_strength
)
from app.core.config import settings
from app.exceptions.custom_exceptions import (
    InvalidCredentialsException,
    UserAlreadyExistsException,
    UserNotFoundException,
    AccountDeactivatedException,
    AccountSuspendedException,
    OTPExpiredException,
    OTPInvalidException,
    OTPMaxAttemptsException,
    OTPNotFoundException,
    WeakPasswordException,
    TokenExpiredException,
    InvalidTokenException
)
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service"""
    
    def __init__(self, db_pool):
        self.db = db_pool
        self.user_repo = UserRepository(db_pool)
        self.otp_repo = OTPRepository(db_pool)
        self.token_repo = TokenRepository(db_pool)
        self.email_service = EmailService(db_pool)
    
    # ========================================================================
    # REGISTRATION FLOW (3 STEPS)
    # ========================================================================
    
    async def register_step_1_send_otp(self, email: str) -> Dict[str, Any]:
        """
        Step 1: Send OTP to email for registration
        
        Args:
            email: User email
        
        Returns:
            Success response with OTP expiry info
        
        Raises:
            UserAlreadyExistsException: Email already registered
        """
        # Check if email already exists
        existing_user = await self.user_repo.get_user_by_email(email)
        if existing_user:
            raise UserAlreadyExistsException("Email is already registered")
        
        # Generate OTP
        otp = generate_otp(length=settings.OTP_LENGTH)
        
        # Save OTP to database
        await self.otp_repo.create_otp(
            email=email,
            otp=otp,
            otp_type="registration",
            expire_minutes=settings.OTP_EXPIRE_MINUTES
        )
        
        # Send OTP email
        await self.email_service.send_otp_email(
            email=email,
            otp=otp,
            purpose="registration"
        )
        
        logger.info(f"Registration OTP sent to {email}")
        
        return {
            "success": True,
            "message": "OTP sent to your email",
            "email": email,
            "otp_expires_in": settings.OTP_EXPIRE_MINUTES
        }
    
    async def register_step_2_verify_otp(
        self,
        email: str,
        otp: str
    ) -> Dict[str, Any]:
        """
        Step 2: Verify OTP
        
        Args:
            email: User email
            otp: OTP from user
        
        Returns:
            Success response
        
        Raises:
            OTPNotFoundException: No OTP found
            OTPExpiredException: OTP expired
            OTPMaxAttemptsException: Too many attempts
            OTPInvalidException: Wrong OTP
        """
        # Get latest OTP
        otp_record = await self.otp_repo.get_latest_otp(email, "registration")
        
        if not otp_record:
            raise OTPNotFoundException("No OTP found for this email")
        
        # Check if expired
        if is_otp_expired(otp_record['created_at'], settings.OTP_EXPIRE_MINUTES):
            raise OTPExpiredException("OTP has expired")
        
        # Check attempt count
        if otp_record['attempt_count'] >= settings.OTP_MAX_ATTEMPTS:
            raise OTPMaxAttemptsException("Maximum OTP attempts exceeded")
        
        # Verify OTP
        if not verify_otp(otp, otp_record['otp_hash']):
            # Increment attempt count
            await self.otp_repo.increment_attempt_count(otp_record['otp_id'])
            raise OTPInvalidException("Invalid OTP")
        
        # Mark as verified
        await self.otp_repo.mark_verified(otp_record['otp_id'])
        
        logger.info(f"OTP verified for {email}")
        
        return {
            "success": True,
            "message": "OTP verified successfully",
            "email": email,
            "verified": True
        }
    
    async def register_step_3_complete(
        self,
        registration_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 3: Complete registration with user details
        
        Args:
            registration_data: User profile data
        
        Returns:
            User info with tokens
        
        Raises:
            OTPNotFoundException: OTP not verified
            UserAlreadyExistsException: Username taken
            WeakPasswordException: Password too weak
        """
        email = registration_data['email']
        
        # Verify OTP was completed
        otp_record = await self.otp_repo.get_latest_otp(email, "registration")
        if not otp_record or not otp_record['is_verified']:
            raise OTPNotFoundException("Please verify OTP first")
        
        # Check username availability
        username = registration_data['username']
        if await self.user_repo.check_username_exists(username):
            raise UserAlreadyExistsException("Username is already taken")
        
        # Validate password strength
        password = registration_data['password']
        is_valid, errors = validate_password_strength(password)
        if not is_valid:
            raise WeakPasswordException("Password is too weak", details=errors)
        
        # Hash password
        password_hash = hash_password(password)
        
        # Create user
        user_data = {
            'email': email,
            'username': username,
            'password_hash': password_hash,
            'full_name': registration_data['full_name'],
            'phone': registration_data.get('phone'),
            'date_of_birth': registration_data.get('date_of_birth'),
            'investment_style': registration_data.get('investment_style'),
            'risk_tolerance': registration_data.get('risk_tolerance'),
            'interested_sectors': registration_data.get('interested_sectors', [])
        }
        
        user = await self.user_repo.create_user(user_data)
        
        # Mark email as verified
        await self.user_repo.verify_email(user['user_id'])
        
        # Generate tokens
        access_token = create_access_token(
            data={"sub": str(user['user_id']), "email": user['email']}
        )
        refresh_token, jti = create_refresh_token(str(user['user_id']))
        
        # Save refresh token
        expires_at = datetime.now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.token_repo.create_refresh_token(
            user_id=str(user['user_id']),
            jti=jti,
            expires_at=expires_at
        )
        
        # Delete OTP
        await self.otp_repo.delete_user_otps(email)
        
        # Send welcome email
        await self.email_service.send_welcome_email(user)
        
        logger.info(f"User registered: {user['email']}")
        
        # Remove sensitive data
        user.pop('password_hash', None)
        
        return {
            "success": True,
            "message": "Registration completed successfully",
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    # ========================================================================
    # LOGIN
    # ========================================================================
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Login user with email and password
        
        Args:
            email: User email
            password: User password
        
        Returns:
            User info with tokens
        
        Raises:
            InvalidCredentialsException: Invalid email or password
            AccountDeactivatedException: Account deactivated
            AccountSuspendedException: Account suspended
        """
        # Get user
        user = await self.user_repo.get_user_by_email(email)
        
        if not user:
            raise InvalidCredentialsException("Invalid email or password")
        
        # Verify password
        if not verify_password(password, user['password_hash']):
            raise InvalidCredentialsException("Invalid email or password")
        
        # Check account status
        if user['account_status'] == 'deactivated':
            raise AccountDeactivatedException("Your account has been deactivated")
        elif user['account_status'] == 'suspended':
            raise AccountSuspendedException("Your account has been suspended")
        
        # Update last login
        await self.user_repo.update_last_login(user['user_id'])
        
        # Generate tokens
        access_token = create_access_token(
            data={"sub": str(user['user_id']), "email": user['email']}
        )
        refresh_token, jti = create_refresh_token(str(user['user_id']))
        
        # Save refresh token
        expires_at = datetime.now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.token_repo.create_refresh_token(
            user_id=str(user['user_id']),
            jti=jti,
            expires_at=expires_at
        )
        
        logger.info(f"User logged in: {user['email']}")
        
        # Remove sensitive data
        user.pop('password_hash', None)
        
        return {
            "success": True,
            "message": "Login successful",
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    # ========================================================================
    # TOKEN REFRESH
    # ========================================================================
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Refresh token
        
        Returns:
            New access token
        
        Raises:
            InvalidTokenException: Invalid refresh token
            TokenExpiredException: Token expired or revoked
        """
        # Verify token
        payload = verify_token(refresh_token, token_type="refresh")
        
        if not payload:
            raise InvalidTokenException("Invalid refresh token")
        
        # Get JTI
        jti = payload.get("jti")
        user_id = payload.get("sub")
        
        if not jti or not user_id:
            raise InvalidTokenException("Invalid token payload")
        
        # Check if token is revoked
        if await self.token_repo.is_token_revoked(jti):
            raise TokenExpiredException("Token has been revoked")
        
        # Get user
        user = await self.user_repo.get_user_by_id(user_id)
        
        if not user:
            raise UserNotFoundException("User not found")
        
        # Check account status
        if user['account_status'] != 'active':
            raise InvalidTokenException("Account is not active")
        
        # Update last used
        await self.token_repo.update_last_used(jti)
        
        # Generate new access token
        access_token = create_access_token(
            data={"sub": str(user['user_id']), "email": user['email']}
        )
        
        logger.info(f"Access token refreshed for user: {user['email']}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    # ========================================================================
    # LOGOUT
    # ========================================================================
    
    async def logout(self, refresh_token: str) -> Dict[str, Any]:
        """
        Logout user by revoking refresh token
        
        Args:
            refresh_token: Refresh token to revoke
        
        Returns:
            Success response
        """
        # Verify token
        payload = verify_token(refresh_token, token_type="refresh")
        
        if payload:
            jti = payload.get("jti")
            if jti:
                # Revoke token
                await self.token_repo.revoke_token(jti, reason="user_logout")
                logger.info(f"User logged out, token revoked: {jti}")
        
        return {
            "success": True,
            "message": "Logged out successfully"
        }
    
    # ========================================================================
    # USERNAME CHECK
    # ========================================================================
    
    async def check_username_availability(self, username: str) -> Dict[str, Any]:
        """
        Check if username is available
        
        Args:
            username: Username to check
        
        Returns:
            Availability status
        """
        exists = await self.user_repo.check_username_exists(username)
        
        return {
            "available": not exists,
            "username": username,
            "message": "Username is available" if not exists else "Username is already taken"
        }
    
    # ========================================================================
    # PASSWORD RESET
    # ========================================================================
    
    async def password_reset_send_otp(self, email: str) -> Dict[str, Any]:
        """
        Send OTP for password reset
        
        Args:
            email: User email
        
        Returns:
            Success response
        
        Raises:
            UserNotFoundException: Email not registered
        """
        # Check if user exists
        user = await self.user_repo.get_user_by_email(email)
        if not user:
            raise UserNotFoundException("No account found with this email")
        
        # Generate OTP
        otp = generate_otp(length=settings.OTP_LENGTH)
        
        # Save OTP
        await self.otp_repo.create_otp(
            email=email,
            otp=otp,
            otp_type="password_reset",
            expire_minutes=settings.OTP_EXPIRE_MINUTES
        )
        
        # Send OTP email
        await self.email_service.send_otp_email(
            email=email,
            otp=otp,
            purpose="password_reset"
        )
        
        logger.info(f"Password reset OTP sent to {email}")
        
        return {
            "success": True,
            "message": "OTP sent to your email",
            "email": email,
            "otp_expires_in": settings.OTP_EXPIRE_MINUTES
        }
    
    async def password_reset_confirm(
        self,
        email: str,
        otp: str,
        new_password: str
    ) -> Dict[str, Any]:
        """
        Confirm password reset with OTP and new password
        
        Args:
            email: User email
            otp: OTP from email
            new_password: New password
        
        Returns:
            Success response
        
        Raises:
            OTPNotFoundException: No OTP found
            OTPExpiredException: OTP expired
            OTPInvalidException: Wrong OTP
            WeakPasswordException: Password too weak
        """
        # Verify OTP
        otp_record = await self.otp_repo.get_latest_otp(email, "password_reset")
        
        if not otp_record:
            raise OTPNotFoundException("No OTP found for this email")
        
        if is_otp_expired(otp_record['created_at'], settings.OTP_EXPIRE_MINUTES):
            raise OTPExpiredException("OTP has expired")
        
        if otp_record['attempt_count'] >= settings.OTP_MAX_ATTEMPTS:
            raise OTPMaxAttemptsException("Maximum OTP attempts exceeded")
        
        if not verify_otp(otp, otp_record['otp_hash']):
            await self.otp_repo.increment_attempt_count(otp_record['otp_id'])
            raise OTPInvalidException("Invalid OTP")
        
        # Validate new password
        is_valid, errors = validate_password_strength(new_password)
        if not is_valid:
            raise WeakPasswordException("Password is too weak", details=errors)
        
        # Get user
        user = await self.user_repo.get_user_by_email(email)
        
        # Update password
        new_password_hash = hash_password(new_password)
        await self.user_repo.update_password(user['user_id'], new_password_hash)
        
        # Revoke all existing refresh tokens
        await self.token_repo.revoke_all_user_tokens(
            user['user_id'],
            reason="password_change"
        )
        
        # Mark OTP as verified and delete
        await self.otp_repo.mark_verified(otp_record['otp_id'])
        await self.otp_repo.delete_user_otps(email)
        
        # Send confirmation email
        await self.email_service.send_password_changed_email(user)
        
        logger.info(f"Password reset completed for {email}")
        
        return {
            "success": True,
            "message": "Password has been reset successfully"
        }

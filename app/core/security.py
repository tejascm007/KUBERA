"""
Security Utilities
JWT token management, password hashing, OTP generation
"""

import jwt
import bcrypt
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import uuid4
import pytz

from app.core.config import settings

# Timezone
IST = pytz.timezone(settings.TIMEZONE)

# ============================================================================
# PASSWORD HASHING
# ============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password string
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
    
    Returns:
        True if password matches, False otherwise
    """
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


# ============================================================================
# JWT TOKEN MANAGEMENT
# ============================================================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token
    
    Args:
        data: Payload data (must include 'sub' for user_id)
        expires_delta: Token expiration time
    
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(IST) + expires_delta
    else:
        expire = datetime.now(IST) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(IST),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None
) -> tuple[str, str]:
    """
    Create JWT refresh token with unique JTI
    
    Args:
        user_id: User UUID
        expires_delta: Token expiration time
    
    Returns:
        Tuple of (token, jti)
    """
    jti = str(uuid4())  # Unique token identifier
    
    if expires_delta:
        expire = datetime.now(IST) + expires_delta
    else:
        expire = datetime.now(IST) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": user_id,
        "jti": jti,
        "exp": expire,
        "iat": datetime.now(IST),
        "type": "refresh"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt, jti


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload
    
    Raises:
        jwt.ExpiredSignatureError: Token expired
        jwt.InvalidTokenError: Invalid token
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise jwt.ExpiredSignatureError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise jwt.InvalidTokenError(f"Invalid token: {str(e)}")


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Verify token and check type
    
    Args:
        token: JWT token string
        token_type: "access" or "refresh"
    
    Returns:
        Token payload if valid, None otherwise
    """
    try:
        payload = decode_token(token)
        
        # Check token type
        if payload.get("type") != token_type:
            return None
        
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    Get token expiration datetime
    
    Args:
        token: JWT token string
    
    Returns:
        Expiration datetime or None
    """
    try:
        payload = decode_token(token)
        exp_timestamp = payload.get("exp")
        
        if exp_timestamp:
            return datetime.fromtimestamp(exp_timestamp, tz=IST)
        
        return None
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ============================================================================
# OTP GENERATION & VERIFICATION
# ============================================================================

def generate_otp(length: int = 6) -> str:
    """
    Generate random numeric OTP
    
    Args:
        length: OTP length (default: 6)
    
    Returns:
        OTP string
    """
    otp = ''.join([str(secrets.randbelow(10)) for _ in range(length)])
    return otp


def hash_otp(otp: str) -> str:
    """
    Hash OTP for secure storage
    
    Args:
        otp: Plain OTP
    
    Returns:
        Hashed OTP
    """
    return hashlib.sha256(otp.encode()).hexdigest()


def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    """
    Verify OTP against hash
    
    Args:
        plain_otp: Plain OTP from user
        hashed_otp: Hashed OTP from database
    
    Returns:
        True if matches, False otherwise
    """
    return hash_otp(plain_otp) == hashed_otp


def is_otp_expired(created_at: datetime, expire_minutes: int = None) -> bool:
    """
    Check if OTP is expired
    
    Args:
        created_at: OTP creation datetime
        expire_minutes: Expiration time in minutes
    
    Returns:
        True if expired, False otherwise
    """
    if expire_minutes is None:
        expire_minutes = settings.OTP_EXPIRE_MINUTES
    
    # Ensure created_at is timezone-aware
    if created_at.tzinfo is None:
        created_at = IST.localize(created_at)
    
    expiry_time = created_at + timedelta(minutes=expire_minutes)
    current_time = datetime.now(IST)
    
    return current_time > expiry_time


# ============================================================================
# RANDOM TOKEN GENERATION
# ============================================================================

def generate_secure_token(length: int = 32) -> str:
    """
    Generate cryptographically secure random token
    
    Args:
        length: Token length in bytes
    
    Returns:
        Random token string (hex)
    """
    return secrets.token_hex(length)


def generate_jti() -> str:
    """
    Generate unique JWT ID (JTI)
    
    Returns:
        UUID string
    """
    return str(uuid4())


# ============================================================================
# PASSWORD VALIDATION
# ============================================================================

def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Validate password strength
    
    Args:
        password: Password to validate
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Minimum length
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long")
    
    # Contains uppercase
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    
    # Contains lowercase
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    
    # Contains digit
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")
    
    # Contains special character
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        errors.append("Password must contain at least one special character")
    
    is_valid = len(errors) == 0
    
    return is_valid, errors


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_current_ist_time() -> datetime:
    """
    Get current time in IST timezone
    
    Returns:
        Current datetime in IST
    """
    return datetime.now(IST)


def convert_to_ist(dt: datetime) -> datetime:
    """
    Convert datetime to IST timezone
    
    Args:
        dt: Datetime object
    
    Returns:
        Datetime in IST
    """
    if dt.tzinfo is None:
        # Naive datetime, assume UTC
        dt = pytz.UTC.localize(dt)
    
    return dt.astimezone(IST)

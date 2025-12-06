"""
Custom Exception Classes
Application-specific exceptions with proper status codes
"""

from fastapi import HTTPException, status
from typing import Any, Optional


class KuberaException(Exception):
    """Base exception for Kubera application"""
    
    def __init__(self, message: str, status_code: int = 500, details: Optional[Any] = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


# ============================================================================
# AUTHENTICATION EXCEPTIONS
# ============================================================================

class UnauthorizedException(KuberaException):
    """User is not authenticated"""
    
    def __init__(self, message: str = "Authentication required", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class ForbiddenException(KuberaException):
    """User doesn't have permission"""
    
    def __init__(self, message: str = "Permission denied", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class InvalidCredentialsException(KuberaException):
    """Invalid username or password"""
    
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class TokenExpiredException(KuberaException):
    """JWT token has expired"""
    
    def __init__(self, message: str = "Token has expired"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class InvalidTokenException(KuberaException):
    """Invalid JWT token"""
    
    def __init__(self, message: str = "Invalid token"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


# ============================================================================
# USER EXCEPTIONS
# ============================================================================

class UserNotFoundException(KuberaException):
    """User not found in database"""
    
    def __init__(self, message: str = "User not found"):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND
        )


class UserAlreadyExistsException(KuberaException):
    """User with email/username already exists"""
    
    def __init__(self, message: str = "User already exists"):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT
        )


class AccountDeactivatedException(KuberaException):
    """User account is deactivated"""
    
    def __init__(self, message: str = "Account is deactivated"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN
        )


class AccountSuspendedException(KuberaException):
    """User account is suspended"""
    
    def __init__(self, message: str = "Account is suspended"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN
        )


# ============================================================================
# VALIDATION EXCEPTIONS
# ============================================================================

class ValidationException(KuberaException):
    """Input validation failed"""
    
    def __init__(self, message: str = "Validation error", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class WeakPasswordException(KuberaException):
    """Password doesn't meet strength requirements"""
    
    def __init__(self, message: str = "Password is too weak", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


# ============================================================================
# OTP EXCEPTIONS
# ============================================================================

class OTPException(KuberaException):
    """Base OTP exception"""
    pass


class OTPExpiredException(OTPException):
    """OTP has expired"""
    
    def __init__(self, message: str = "OTP has expired"):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class OTPInvalidException(OTPException):
    """Invalid OTP"""
    
    def __init__(self, message: str = "Invalid OTP"):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class OTPMaxAttemptsException(OTPException):
    """Max OTP verification attempts exceeded"""
    
    def __init__(self, message: str = "Maximum OTP attempts exceeded"):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )


class OTPNotFoundException(OTPException):
    """OTP not found or already verified"""
    
    def __init__(self, message: str = "OTP not found or already verified"):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND
        )


# ============================================================================
# RATE LIMIT EXCEPTIONS
# ============================================================================

class RateLimitException(KuberaException):
    """Base rate limit exception"""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        violation_type: str = "unknown",
        limit: int = 0,
        used: int = 0,
        reset_at: Optional[str] = None
    ):
        details = {
            "violation_type": violation_type,
            "limit": limit,
            "used": used,
            "reset_at": reset_at
        }
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )


class BurstRateLimitException(RateLimitException):
    """Burst rate limit exceeded (per minute)"""
    
    def __init__(self, limit: int, used: int, reset_at: str):
        super().__init__(
            message=f"Burst rate limit exceeded. Maximum {limit} prompts per minute.",
            violation_type="burst",
            limit=limit,
            used=used,
            reset_at=reset_at
        )


class PerChatRateLimitException(RateLimitException):
    """Per-chat rate limit exceeded"""
    
    def __init__(self, limit: int, used: int):
        super().__init__(
            message=f"Chat rate limit exceeded. Maximum {limit} prompts per chat.",
            violation_type="per_chat",
            limit=limit,
            used=used
        )


class HourlyRateLimitException(RateLimitException):
    """Hourly rate limit exceeded"""
    
    def __init__(self, limit: int, used: int, reset_at: str):
        super().__init__(
            message=f"Hourly rate limit exceeded. Maximum {limit} prompts per hour.",
            violation_type="hourly",
            limit=limit,
            used=used,
            reset_at=reset_at
        )


class DailyRateLimitException(RateLimitException):
    """Daily rate limit exceeded"""
    
    def __init__(self, limit: int, used: int, reset_at: str):
        super().__init__(
            message=f"Daily rate limit exceeded. Maximum {limit} prompts per 24 hours.",
            violation_type="daily",
            limit=limit,
            used=used,
            reset_at=reset_at
        )


# ============================================================================
# RESOURCE EXCEPTIONS
# ============================================================================

class ResourceNotFoundException(KuberaException):
    """Generic resource not found"""
    
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} with ID {resource_id} not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


class ChatNotFoundException(KuberaException):
    """Chat not found"""
    
    def __init__(self, chat_id: str):
        super().__init__(
            message=f"Chat {chat_id} not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


class PortfolioNotFoundException(KuberaException):
    """Portfolio entry not found"""
    
    def __init__(self, portfolio_id: str):
        super().__init__(
            message=f"Portfolio entry {portfolio_id} not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


class MessageNotFoundException(KuberaException):
    """Message not found"""
    
    def __init__(self, message_id: str):
        super().__init__(
            message=f"Message {message_id} not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


# ============================================================================
# BUSINESS LOGIC EXCEPTIONS
# ============================================================================

class DuplicatePortfolioException(KuberaException):
    """Portfolio entry already exists for this stock"""
    
    def __init__(self, stock_symbol: str):
        super().__init__(
            message=f"Portfolio entry for {stock_symbol} already exists",
            status_code=status.HTTP_409_CONFLICT
        )


class InvalidStockSymbolException(KuberaException):
    """Invalid or unknown stock symbol"""
    
    def __init__(self, stock_symbol: str):
        super().__init__(
            message=f"Invalid or unknown stock symbol: {stock_symbol}",
            status_code=status.HTTP_400_BAD_REQUEST
        )


# ============================================================================
# DATABASE EXCEPTIONS
# ============================================================================

class DatabaseException(KuberaException):
    """Database operation failed"""
    
    def __init__(self, message: str = "Database error", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


# ============================================================================
# EMAIL EXCEPTIONS
# ============================================================================

class EmailException(KuberaException):
    """Email sending failed"""
    
    def __init__(self, message: str = "Failed to send email"):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ============================================================================
# MCP EXCEPTIONS
# ============================================================================


class MCPException(KuberaException):
    """MCP server error"""
    
    def __init__(self, message: str = "MCP server error", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class MCPInitializationException(MCPException):
    """MCP client initialization failed"""
    
    def __init__(self, message: str = "Failed to initialize MCP client", details: Optional[Any] = None):
        super().__init__(
            message=message,
            details=details
        )


class MCPServerUnavailableException(MCPException):
    """MCP server is unavailable"""
    
    def __init__(self, server_name: str):
        super().__init__(
            message=f"MCP server '{server_name}' is unavailable",
            details={"server": server_name}
        )


class MCPToolNotFoundException(MCPException):
    """MCP tool not found"""
    
    def __init__(self, tool_name: str):
        super().__init__(
            message=f"MCP tool '{tool_name}' not found",
            details={"tool": tool_name}
        )


class MCPToolExecutionException(MCPException):
    """MCP tool execution failed"""
    
    def __init__(self, tool_name: str, error: str):
        super().__init__(
            message=f"Tool '{tool_name}' execution failed: {error}",
            details={"tool": tool_name, "error": error}
        )

# ============================================================================
# ADMIN EXCEPTIONS
# ============================================================================

class AdminNotFoundException(KuberaException):
    """Admin not found"""
    
    def __init__(self, message: str = "Admin not found"):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND
        )


class AdminInactiveException(KuberaException):
    """Admin account is inactive"""
    
    def __init__(self, message: str = "Admin account is inactive"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN
        )


# ============================================================================
# WEBSOCKET EXCEPTIONS
# ============================================================================

class WebSocketException(KuberaException):
    """WebSocket error"""
    
    def __init__(self, message: str = "WebSocket error"):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# ALIASES FOR BACKWARD COMPATIBILITY
# ============================================================================

# Alias for consistency
AuthenticationException = UnauthorizedException
AuthorizationException = ForbiddenException
ResourceNotFoundException = ResourceNotFoundException  # Already exists

"""
Exceptions Module
Custom exceptions and handlers
"""

from app.exceptions.custom_exceptions import (
    # Base
    KuberaException,
    
    # Authentication
    UnauthorizedException,
    ForbiddenException,
    InvalidCredentialsException,
    TokenExpiredException,
    InvalidTokenException,
    
    # User
    UserNotFoundException,
    UserAlreadyExistsException,
    AccountDeactivatedException,
    AccountSuspendedException,
    
    # Validation
    ValidationException,
    WeakPasswordException,
    
    # OTP
    OTPException,
    OTPExpiredException,
    OTPInvalidException,
    OTPMaxAttemptsException,
    OTPNotFoundException,
    
    # Rate Limit
    RateLimitException,
    BurstRateLimitException,
    PerChatRateLimitException,
    HourlyRateLimitException,
    DailyRateLimitException,
    
    # Resources
    ResourceNotFoundException,
    ChatNotFoundException,
    PortfolioNotFoundException,
    MessageNotFoundException,
    
    # Business Logic
    DuplicatePortfolioException,
    InvalidStockSymbolException,
    
    # Database
    DatabaseException,
    
    # Email
    EmailException,
    
    # MCP
    MCPException,
    MCPInitializationException, 
    MCPServerUnavailableException,
    MCPToolNotFoundException,
    MCPToolExecutionException,
    
    # Admin
    AdminNotFoundException,
    AdminInactiveException,
    
    # WebSocket
    WebSocketException
)

from app.exceptions.handlers import (
    kubera_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)

# Aliases for backward compatibility
AuthenticationException = UnauthorizedException
AuthorizationException = ForbiddenException

__all__ = [
    # Base
    "KuberaException",
    
    # Authentication
    "UnauthorizedException",
    "ForbiddenException",
    "InvalidCredentialsException",
    "TokenExpiredException",
    "InvalidTokenException",
    "AuthenticationException",  # Alias
    "AuthorizationException",    # Alias
    
    # User
    "UserNotFoundException",
    "UserAlreadyExistsException",
    "AccountDeactivatedException",
    "AccountSuspendedException",
    
    # Validation
    "ValidationException",
    "WeakPasswordException",
    
    # OTP
    "OTPException",
    "OTPExpiredException",
    "OTPInvalidException",
    "OTPMaxAttemptsException",
    "OTPNotFoundException",
    
    # Rate Limit
    "RateLimitException",
    "BurstRateLimitException",
    "PerChatRateLimitException",
    "HourlyRateLimitException",
    "DailyRateLimitException",
    
    # Resources
    "ResourceNotFoundException",
    "ChatNotFoundException",
    "PortfolioNotFoundException",
    "MessageNotFoundException",
    
    # Business Logic
    "DuplicatePortfolioException",
    "InvalidStockSymbolException",
    
    # Database
    "DatabaseException",
    
    # Email
    "EmailException",
    
    # MCP
    "MCPException",
    "MCPInitializationException", 
    "MCPServerUnavailableException",
    "MCPToolNotFoundException",
    "MCPToolExecutionException", 
    
    # Admin
    "AdminNotFoundException",
    "AdminInactiveException",
    
    # WebSocket
    "WebSocketException",
    
    # Handlers
    "kubera_exception_handler",
    "validation_exception_handler",
    "generic_exception_handler"
]

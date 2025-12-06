"""
Core Module
Configuration, security, database, and dependencies
"""

from app.core.config import settings
from app.core.database import (
    init_db,
    close_db,
    get_db_pool,
    get_db_connection
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token
)
from app.core.dependencies import (
    get_current_user,
    get_current_active_user,
    get_current_admin
)

__all__ = [
    # Config
    "settings",
    
    # Database
    "init_db",
    "close_db",
    "get_db_pool",
    "get_db_connection",
    
    # Security
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "get_current_admin"
]

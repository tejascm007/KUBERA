"""
Input Validators
Validation functions for various inputs
"""

import re
from typing import Optional
from datetime import datetime, date


def validate_email(email: str) -> bool:
    """
    Validate email format
    
    Args:
        email: Email address
    
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """
    Validate Indian phone number
    
    Formats accepted:
    - 9876543210
    - +919876543210
    - 919876543210
    
    Args:
        phone: Phone number
    
    Returns:
        True if valid, False otherwise
    """
    # Remove spaces and dashes
    phone = phone.replace(' ', '').replace('-', '')
    
    # Check format
    pattern = r'^(\+91|91)?[6-9]\d{9}$'
    return bool(re.match(pattern, phone))


def validate_username(username: str) -> tuple[bool, Optional[str]]:
    """
    Validate username
    
    Rules:
    - 3-100 characters
    - Alphanumeric, underscore, dot allowed
    - Must start with letter
    
    Args:
        username: Username
    
    Returns:
        (is_valid, error_message)
    """
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if len(username) > 100:
        return False, "Username must be at most 100 characters"
    
    if not username[0].isalpha():
        return False, "Username must start with a letter"
    
    pattern = r'^[a-zA-Z][a-zA-Z0-9_.]*$'
    if not re.match(pattern, username):
        return False, "Username can only contain letters, numbers, underscore, and dot"
    
    return True, None


def validate_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength
    
    Rules:
    - At least 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    - At least 1 special character
    
    Args:
        password: Password
    
    Returns:
        (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least 1 uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least 1 lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least 1 digit"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least 1 special character"
    
    return True, None


def validate_stock_symbol(symbol: str) -> tuple[bool, Optional[str]]:
    """
    Validate stock symbol
    
    Args:
        symbol: Stock symbol (e.g., INFY, TCS, RELIANCE)
    
    Returns:
        (is_valid, error_message)
    """
    if not symbol:
        return False, "Stock symbol is required"
    
    if len(symbol) < 2 or len(symbol) > 20:
        return False, "Stock symbol must be 2-20 characters"
    
    # Alphanumeric only
    if not symbol.isalnum():
        return False, "Stock symbol must be alphanumeric"
    
    return True, None


def validate_date_not_future(input_date: date) -> tuple[bool, Optional[str]]:
    """
    Validate that date is not in the future
    
    Args:
        input_date: Date to validate
    
    Returns:
        (is_valid, error_message)
    """
    if input_date > date.today():
        return False, "Date cannot be in the future"
    
    return True, None


def validate_positive_number(value: float, name: str = "Value") -> tuple[bool, Optional[str]]:
    """
    Validate that number is positive
    
    Args:
        value: Number to validate
        name: Name for error message
    
    Returns:
        (is_valid, error_message)
    """
    if value <= 0:
        return False, f"{name} must be positive"
    
    return True, None


def validate_otp(otp: str) -> tuple[bool, Optional[str]]:
    """
    Validate OTP format
    
    Rules:
    - Exactly 6 digits
    
    Args:
        otp: OTP string
    
    Returns:
        (is_valid, error_message)
    """
    if not otp:
        return False, "OTP is required"
    
    if len(otp) != 6:
        return False, "OTP must be 6 digits"
    
    if not otp.isdigit():
        return False, "OTP must contain only digits"
    
    return True, None


def sanitize_string(text: str, max_length: int = None) -> str:
    """
    Sanitize string input
    
    Args:
        text: Input text
        max_length: Maximum length (optional)
    
    Returns:
        Sanitized string
    """
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Truncate if needed
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text


def validate_exchange(exchange: str) -> tuple[bool, Optional[str]]:
    """
    Validate stock exchange
    
    Args:
        exchange: Exchange name (NSE or BSE)
    
    Returns:
        (is_valid, error_message)
    """
    valid_exchanges = ['NSE', 'BSE']
    
    if exchange.upper() not in valid_exchanges:
        return False, f"Exchange must be one of: {', '.join(valid_exchanges)}"
    
    return True, None

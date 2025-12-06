"""
Data Formatters
Format data for display and processing
"""

from datetime import datetime, date
from typing import Optional, Union
import locale


def format_inr(amount: Union[int, float], decimals: int = 2) -> str:
    """
    Format amount in Indian Rupees
    
    Args:
        amount: Amount to format
        decimals: Number of decimal places
    
    Returns:
        Formatted string (e.g., "₹1,23,456.78")
    """
    if amount is None:
        return "₹0.00"
    
    # Indian number system formatting
    s = f"{abs(amount):,.{decimals}f}"
    
    # Convert to Indian format (lakhs, crores)
    parts = s.split('.')
    integer_part = parts[0].replace(',', '')
    decimal_part = parts[1] if len(parts) > 1 else '0' * decimals
    
    # Format integer part with Indian commas
    if len(integer_part) <= 3:
        formatted = integer_part
    else:
        last_three = integer_part[-3:]
        rest = integer_part[:-3]
        
        # Add commas every 2 digits
        formatted_rest = ''
        for i, digit in enumerate(reversed(rest)):
            if i > 0 and i % 2 == 0:
                formatted_rest = ',' + formatted_rest
            formatted_rest = digit + formatted_rest
        
        formatted = formatted_rest + ',' + last_three
    
    # Add sign if negative
    sign = '-' if amount < 0 else ''
    
    return f"{sign}₹{formatted}.{decimal_part}"


def format_inr_short(amount: Union[int, float]) -> str:
    """
    Format amount in short form (K, L, Cr)
    
    Args:
        amount: Amount to format
    
    Returns:
        Formatted string (e.g., "₹1.23L", "₹12.5Cr")
    """
    if amount is None:
        return "₹0"
    
    abs_amount = abs(amount)
    sign = '-' if amount < 0 else ''
    
    if abs_amount >= 10000000:  # 1 Crore
        return f"{sign}₹{abs_amount / 10000000:.2f}Cr"
    elif abs_amount >= 100000:  # 1 Lakh
        return f"{sign}₹{abs_amount / 100000:.2f}L"
    elif abs_amount >= 1000:  # 1 Thousand
        return f"{sign}₹{abs_amount / 1000:.2f}K"
    else:
        return f"{sign}₹{abs_amount:.2f}"


def format_percentage(value: Union[int, float], decimals: int = 2, include_sign: bool = True) -> str:
    """
    Format percentage
    
    Args:
        value: Percentage value
        decimals: Number of decimal places
        include_sign: Include + sign for positive values
    
    Returns:
        Formatted string (e.g., "+12.34%", "-5.67%")
    """
    if value is None:
        return "0.00%"
    
    sign = ''
    if include_sign and value > 0:
        sign = '+'
    elif value < 0:
        sign = '-'
    
    return f"{sign}{abs(value):.{decimals}f}%"


def format_date(input_date: Union[datetime, date], format: str = '%d-%m-%Y') -> str:
    """
    Format date
    
    Args:
        input_date: Date to format
        format: Date format string
    
    Returns:
        Formatted date string
    """
    if input_date is None:
        return ""
    
    if isinstance(input_date, datetime):
        return input_date.strftime(format)
    elif isinstance(input_date, date):
        return input_date.strftime(format)
    else:
        return str(input_date)


def format_datetime(dt: datetime, format: str = '%d-%m-%Y %H:%M:%S') -> str:
    """
    Format datetime
    
    Args:
        dt: Datetime to format
        format: Datetime format string
    
    Returns:
        Formatted datetime string
    """
    if dt is None:
        return ""
    
    return dt.strftime(format)


def format_relative_time(dt: datetime) -> str:
    """
    Format datetime as relative time (e.g., "2 hours ago")
    
    Args:
        dt: Datetime to format
    
    Returns:
        Relative time string
    """
    if dt is None:
        return ""
    
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} {'minute' if minutes == 1 else 'minutes'} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} {'hour' if hours == 1 else 'hours'} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} {'day' if days == 1 else 'days'} ago"
    else:
        return format_date(dt)


def format_number(value: Union[int, float], decimals: int = 2) -> str:
    """
    Format number with thousand separators
    
    Args:
        value: Number to format
        decimals: Number of decimal places
    
    Returns:
        Formatted string (e.g., "1,234.56")
    """
    if value is None:
        return "0"
    
    return f"{value:,.{decimals}f}"


def format_quantity(value: Union[int, float]) -> str:
    """
    Format stock quantity
    
    Args:
        value: Quantity value
    
    Returns:
        Formatted string
    """
    if value is None:
        return "0"
    
    # If whole number, show without decimals
    if value == int(value):
        return f"{int(value):,}"
    else:
        return f"{value:,.4f}"


def format_change(current: float, previous: float) -> dict:
    """
    Calculate and format change
    
    Args:
        current: Current value
        previous: Previous value
    
    Returns:
        Dict with change, change_percent, and direction
    """
    if previous == 0:
        return {
            "change": 0,
            "change_percent": 0,
            "direction": "neutral",
            "formatted_change": "₹0.00",
            "formatted_percent": "0.00%"
        }
    
    change = current - previous
    change_percent = (change / previous) * 100
    
    direction = "up" if change > 0 else "down" if change < 0 else "neutral"
    
    return {
        "change": change,
        "change_percent": change_percent,
        "direction": direction,
        "formatted_change": format_inr(change),
        "formatted_percent": format_percentage(change_percent)
    }


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted string (e.g., "1.23 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.2f} PB"

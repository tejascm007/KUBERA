"""
OTP Generator and Verifier
Generate and verify OTPs for authentication
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional


class OTPGenerator:
    """OTP generation and verification"""
    
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 10
    MAX_ATTEMPTS = 3
    
    @staticmethod
    def generate_otp() -> str:
        """
        Generate a 6-digit OTP
        
        Returns:
            6-digit OTP string
        """
        # Generate cryptographically secure random 6-digit number
        otp = ''.join([str(secrets.randbelow(10)) for _ in range(OTPGenerator.OTP_LENGTH)])
        return otp
    
    @staticmethod
    def hash_otp(otp: str) -> str:
        """
        Hash OTP for secure storage
        
        Args:
            otp: Plain OTP
        
        Returns:
            Hashed OTP
        """
        return hashlib.sha256(otp.encode()).hexdigest()
    
    @staticmethod
    def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
        """
        Verify OTP against hash
        
        Args:
            plain_otp: Plain OTP entered by user
            hashed_otp: Hashed OTP from database
        
        Returns:
            True if match, False otherwise
        """
        return OTPGenerator.hash_otp(plain_otp) == hashed_otp
    
    @staticmethod
    def is_expired(created_at: datetime) -> bool:
        """
        Check if OTP has expired
        
        Args:
            created_at: OTP creation timestamp
        
        Returns:
            True if expired, False otherwise
        """
        expiry_time = created_at + timedelta(minutes=OTPGenerator.OTP_EXPIRY_MINUTES)
        return datetime.now(created_at.tzinfo) > expiry_time
    
    @staticmethod
    def get_expiry_minutes() -> int:
        """Get OTP expiry duration in minutes"""
        return OTPGenerator.OTP_EXPIRY_MINUTES
    
    @staticmethod
    def get_max_attempts() -> int:
        """Get maximum OTP verification attempts"""
        return OTPGenerator.MAX_ATTEMPTS

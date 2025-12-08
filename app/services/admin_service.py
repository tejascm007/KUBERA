"""
Admin Service
Business logic for admin operations
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json

from app.db.repositories.admin_repository import AdminRepository
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.rate_limit_repository import RateLimitRepository
from app.db.repositories.system_repository import SystemRepository
from app.db.repositories.otp_repository import OTPRepository
from app.core.security import (
    create_access_token,
    generate_otp,
    verify_otp,
    is_otp_expired
)
from app.core.config import settings
from app.exceptions.custom_exceptions import (
    AdminNotFoundException,
    AdminInactiveException,
    OTPExpiredException,
    OTPInvalidException,
    OTPNotFoundException
)
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class AdminService:
    """Admin operations service"""
    
    def __init__(self, db_pool):
        self.db = db_pool
        self.admin_repo = AdminRepository(db_pool)
        self.user_repo = UserRepository(db_pool)
        self.rate_limit_repo = RateLimitRepository(db_pool)
        self.system_repo = SystemRepository(db_pool)
        self.otp_repo = OTPRepository(db_pool)
        self.email_service = EmailService(db_pool)
    
    # ========================================================================
    # ADMIN LOGIN (OTP-BASED)
    # ========================================================================
    
    async def admin_login_send_otp(self, email: str) -> Dict[str, Any]:
        """Send OTP to admin email"""
        
        admin = await self.admin_repo.get_admin_by_email(email)
        
        if not admin:
            raise AdminNotFoundException("Admin not found")
        
        if not admin['is_active']:
            raise AdminInactiveException("Admin account is inactive")
        
        # Generate OTP
        otp = generate_otp(length=6)
        
        # Save OTP
        await self.otp_repo.create_otp(
            email=email,
            otp=otp,
            otp_type="admin_login",
            expire_minutes=settings.OTP_EXPIRE_MINUTES
        )
        
        # Send OTP email
        await self.email_service.send_otp_email(email, otp, purpose="admin_login")
        
        logger.info(f"Admin login OTP sent to {email}")
        
        return {
            "success": True,
            "message": "OTP sent to your email",
            "email": email,
            "otp_expires_in": settings.OTP_EXPIRE_MINUTES
        }
    
    async def admin_login_verify_otp(self, email: str, otp: str) -> Dict[str, Any]:
        """Verify OTP and login admin"""
        
        # Verify OTP
        otp_record = await self.otp_repo.get_latest_otp(email, "admin_login")
        
        if not otp_record:
            raise OTPNotFoundException("No OTP found")
        
        if is_otp_expired(otp_record['created_at'], settings.OTP_EXPIRE_MINUTES):
            raise OTPExpiredException("OTP has expired")
        
        if not verify_otp(otp, otp_record['otp_hash']):
            await self.otp_repo.increment_attempt_count(otp_record['otp_id'])
            raise OTPInvalidException("Invalid OTP")
        
        # Get admin
        admin = await self.admin_repo.get_admin_by_email(email)
        
        # Update last login
        await self.admin_repo.update_last_login(admin['admin_id'])
        
        # Mark OTP as verified
        await self.otp_repo.mark_verified(otp_record['otp_id'])
        
        # Generate access token
        access_token = create_access_token(
            data={
                "sub": str(admin['admin_id']),
                "email": admin['email'],
                "role": "admin"
            }
        )
        
        logger.info(f"Admin logged in: {email}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "admin_id": str(admin['admin_id']),
            "email": admin['email'],
            "full_name": admin['full_name'],
            "is_super_admin": admin['is_super_admin']
        }
    
    # ========================================================================
    # DASHBOARD
    # ========================================================================
    
    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get admin dashboard statistics"""
        
        from app.db.repositories.chat_repository import ChatRepository
        chat_repo = ChatRepository(self.db)
        
        # User stats
        total_users = await self.user_repo.count_users()
        active_users = await self.user_repo.count_users("active")
        deactivated_users = await self.user_repo.count_users("deactivated")
        
        # Chat stats
        total_messages = await chat_repo.get_total_messages_count()
        
        # Rate limit violations
        from datetime import timedelta
        today = datetime.now().date()
        violations_today = await self.rate_limit_repo.count_violations(
            since=datetime.combine(today, datetime.min.time())
        )
        total_violations = await self.rate_limit_repo.count_violations()
        
        # System status
        system_status = await self.system_repo.get_system_status()
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "deactivated_users": deactivated_users,
            "total_chats": 0,  # Add if needed
            "total_messages": total_messages,
            "total_prompts_today": 0,  # Add if needed
            "total_prompts_this_week": 0,
            "total_prompts_this_month": 0,
            "total_rate_limit_violations": total_violations,
            "violations_today": violations_today,
            "system_status": system_status['current_status'],
            "portfolio_report_frequency": system_status['portfolio_report_frequency'],
            "portfolio_report_last_sent": system_status['portfolio_report_last_sent']
        }
    
    # ========================================================================
    # USER MANAGEMENT
    # ========================================================================
    
    async def get_all_users(
        self,
        limit: int = 50,
        offset: int = 0,
        account_status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all users with stats"""
        
        # Use user_repo instead of admin_repo
        users = await self.user_repo.get_all_users(limit, offset, account_status)
        total = await self.user_repo.count_users(account_status)
        
        # ========================================================================
        # FIX: Add stats and convert UUIDs for each user
        # ========================================================================
        for user in users:
            # Convert UUID to string
            if user.get('user_id'):
                user_id = str(user['user_id'])
                user['user_id'] = user_id
                
                # Get user stats
                stats = await self.user_repo.get_user_statistics(user_id)
                user['total_chats'] = stats.get('total_chats', 0)
                user['total_prompts'] = stats.get('total_prompts', 0)
            
            # Convert date to string
            if user.get('date_of_birth') and hasattr(user['date_of_birth'], 'isoformat'):
                user['date_of_birth'] = user['date_of_birth'].isoformat()
            
            # Remove sensitive data
            user.pop('password_hash', None)
        
        return {
            "success": True,
            "total_users": total,
            "users": users
        }

    async def get_user_detail(self, user_id: str) -> Dict[str, Any]:
        """Get detailed user information"""
        
        # Get user
        user = await self.user_repo.get_user_by_id(user_id)
        
        if not user:
            from app.exceptions.custom_exceptions import UserNotFoundException
            raise UserNotFoundException(user_id)
        
        # Convert UUID to string
        user_id_str = str(user['user_id']) if user.get('user_id') else user_id
        user['user_id'] = user_id_str
        
        # Convert date to string
        if user.get('date_of_birth') and hasattr(user['date_of_birth'], 'isoformat'):
            user['date_of_birth'] = user['date_of_birth'].isoformat()
        
        # Get user stats
        stats = await self.user_repo.get_user_statistics(user_id_str)
        user['total_chats'] = stats.get('total_chats', 0)
        user['total_prompts'] = stats.get('total_prompts', 0)
        user['portfolio_entries'] = stats.get('portfolio_entries', 0)
        
        # Convert Decimal to float
        if user.get('total_invested'):
            user['total_invested'] = float(user['total_invested'])
        
        # ========================================================================
        # ADD MISSING FIELDS
        # ========================================================================
        user['prompts_today'] = 0
        user['prompts_this_week'] = 0
        user['prompts_this_month'] = 0
        
        # Get rate limit info
        rate_limit_config = await self.rate_limit_repo.get_rate_limit_config()
        user_limits = await self.rate_limit_repo.get_user_specific_limits(user_id_str)
        
        if user_limits:
            user['current_rate_limits'] = user_limits
        else:
            user['current_rate_limits'] = {
                "burst": rate_limit_config.get('burst_limit_per_minute', 10),
                "per_chat": rate_limit_config.get('per_chat_limit', 50),
                "hourly": rate_limit_config.get('per_hour_limit', 100),
                "daily": rate_limit_config.get('per_day_limit', 500)
            }
        
        # Get violations count
        violations_count = await self.rate_limit_repo.count_violations(user_id_str)
        user['rate_limit_violations'] = violations_count
        
        user['total_portfolio_entries'] = user['portfolio_entries']
        
        # Remove sensitive data
        user.pop('password_hash', None)
        
        return user


    async def deactivate_user(
        self,
        user_id: str,
        admin_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Deactivate a user"""
        
        user = await self.user_repo.update_account_status(user_id, "deactivated")
        
        # Log activity
        await self.admin_repo.log_activity({
            "admin_id": admin_id,
            "action": "user_deactivated",
            "target_type": "user",
            "target_id": user_id,
            "old_value": json.dumps({"status": "active"}),  # Convert to JSON string
            "new_value": json.dumps({"status": "deactivated", "reason": reason})  # Convert to JSON string
        })
        
        # Send email to user (optional, may fail if email service not implemented)
        try:
            await self.email_service.send_account_deactivated_email(user, reason)
        except Exception as e:
            logger.warning(f"Failed to send deactivation email: {e}")
        
        logger.info(f"User deactivated by admin: {user_id}")
        
        return user


    async def reactivate_user(
        self,
        user_id: str,
        admin_id: str
    ) -> Dict[str, Any]:
        """Reactivate a user"""
        
        user = await self.user_repo.update_account_status(user_id, "active")
        
        # Log activity
        await self.admin_repo.log_activity({
            "admin_id": admin_id,
            "action": "user_reactivated",
            "target_type": "user",
            "target_id": user_id,
            "old_value": json.dumps({"status": "deactivated"}),  # Convert to JSON string
            "new_value": json.dumps({"status": "active"})  # Convert to JSON string
        })
        
        # Send email to user (optional)
        try:
            await self.email_service.send_account_reactivated_email(user)
        except Exception as e:
            logger.warning(f"Failed to send reactivation email: {e}")
        
        logger.info(f"User reactivated by admin: {user_id}")
        
        return user
    
    # ========================================================================
    # SYSTEM CONTROL
    # ========================================================================
    
    async def system_control(
    self,
    action: str,
    admin_id: str,
    reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Control system status (stop/start/restart)"""
        
        current_status = await self.system_repo.get_system_status()
        old_status = current_status['current_status']
        
        status_map = {
            "stop": "stopped",
            "start": "running",
            "restart": "running"
        }
        
        new_status = status_map[action]
        
        # Update system status
        updated = await self.system_repo.update_system_status(new_status)
        
        # Log activity - WITH JSON CONVERSION
        import json
        await self.admin_repo.log_activity({
            "admin_id": admin_id,
            "action": f"system_{action}",
            "target_type": "system",
            "old_value": json.dumps({"status": old_status}),  # CONVERT TO JSON STRING
            "new_value": json.dumps({"status": new_status, "reason": reason})  # CONVERT TO JSON STRING
        })
        
        # Send email to all users (optional - may not be implemented)
        try:
            await self.email_service.send_system_status_email(new_status, reason)
        except Exception as e:
            logger.warning(f"Failed to send system status email: {e}")
        
        logger.info(f"System {action} by admin: {admin_id}")
        
        return updated


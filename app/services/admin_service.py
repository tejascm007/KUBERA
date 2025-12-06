"""
Admin Service
Business logic for admin operations
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

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
            expire_minutes=settings.ADMIN_OTP_EXPIRE_MINUTES
        )
        
        # Send OTP email
        await self.email_service.send_otp_email(email, otp, purpose="admin_login")
        
        logger.info(f"Admin login OTP sent to {email}")
        
        return {
            "success": True,
            "message": "OTP sent to your email",
            "email": email,
            "otp_expires_in": settings.ADMIN_OTP_EXPIRE_MINUTES
        }
    
    async def admin_login_verify_otp(self, email: str, otp: str) -> Dict[str, Any]:
        """Verify OTP and login admin"""
        
        # Verify OTP
        otp_record = await self.otp_repo.get_latest_otp(email, "admin_login")
        
        if not otp_record:
            raise OTPNotFoundException("No OTP found")
        
        if is_otp_expired(otp_record['created_at'], settings.ADMIN_OTP_EXPIRE_MINUTES):
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
        limit: int = 100,
        offset: int = 0,
        account_status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all users"""
        
        users = await self.user_repo.get_all_users(limit, offset, account_status)
        total = await self.user_repo.count_users(account_status)
        
        return {
            "success": True,
            "total_users": total,
            "users": users
        }
    
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
            "old_value": {"status": "active"},
            "new_value": {"status": "deactivated", "reason": reason}
        })
        
        # Send email to user
        await self.email_service.send_account_deactivated_email(user, reason)
        
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
            "old_value": {"status": "deactivated"},
            "new_value": {"status": "active"}
        })
        
        # Send email to user
        await self.email_service.send_account_reactivated_email(user)
        
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
        
        # Log activity
        await self.admin_repo.log_activity({
            "admin_id": admin_id,
            "action": f"system_{action}",
            "target_type": "system",
            "old_value": {"status": old_status},
            "new_value": {"status": new_status, "reason": reason}
        })
        
        # Send email to all users
        await self.email_service.send_system_status_email(new_status, reason)
        
        logger.info(f"System {action} by admin: {admin_id}")
        
        return updated

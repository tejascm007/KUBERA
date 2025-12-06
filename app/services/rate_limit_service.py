"""
Rate Limit Service
Business logic for 4-level rate limiting (FAIL-FAST)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from app.db.repositories.rate_limit_repository import RateLimitRepository
from app.core.security import get_current_ist_time
from app.exceptions.custom_exceptions import (
    BurstRateLimitException,
    PerChatRateLimitException,
    HourlyRateLimitException,
    DailyRateLimitException
)
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class RateLimitService:
    """4-level rate limiting service with fail-fast logic"""
    
    def __init__(self, db_pool):
        self.db = db_pool
        self.rate_limit_repo = RateLimitRepository(db_pool)
        self.email_service = EmailService(db_pool)
    
    # ========================================================================
    # RATE LIMIT CHECK (4-LEVEL FAIL-FAST)
    # ========================================================================
    
    async def check_rate_limits(
        self,
        user_id: str,
        chat_id: str,
        user_message: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """
        Check all 4 rate limit levels (FAIL-FAST)
        
        Order of checks:
        1. Burst (10/min) - FASTEST TO CHECK, FAIL FIRST
        2. Per-chat (50/chat)
        3. Hourly (150/hour)
        4. Daily (1000/24h)
        
        Args:
            user_id: User UUID
            chat_id: Chat UUID
            user_message: User's message (for logging)
            ip_address: User IP
            user_agent: User agent
        
        Returns:
            Success response if all limits passed
        
        Raises:
            BurstRateLimitException: Burst limit exceeded
            PerChatRateLimitException: Per-chat limit exceeded
            HourlyRateLimitException: Hourly limit exceeded
            DailyRateLimitException: Daily limit exceeded
        """
        # Check if user is whitelisted (no limits)
        if await self.rate_limit_repo.is_user_whitelisted(user_id):
            return {"allowed": True, "reason": "whitelisted"}
        
        # Get rate limit configuration
        config = await self.rate_limit_repo.get_rate_limit_config()
        
        # Check for user-specific overrides
        user_limits = await self.rate_limit_repo.get_user_specific_limits(user_id)
        
        # Set limits (use user-specific if available, else global)
        burst_limit = user_limits.get('burst', config['burst_limit_per_minute']) if user_limits else config['burst_limit_per_minute']
        per_chat_limit = user_limits.get('per_chat', config['per_chat_limit']) if user_limits else config['per_chat_limit']
        hourly_limit = user_limits.get('hourly', config['per_hour_limit']) if user_limits else config['per_hour_limit']
        daily_limit = user_limits.get('daily', config['per_day_limit']) if user_limits else config['per_day_limit']
        
        # Get or create tracking record
        tracking = await self.rate_limit_repo.get_or_create_tracking(user_id)
        
        # Get current counts with window resets
        current_counts = await self.rate_limit_repo.get_current_counts(user_id)
        
        # Get per-chat count
        from app.db.repositories.chat_repository import ChatRepository
        chat_repo = ChatRepository(self.db)
        per_chat_count = await chat_repo.get_chat_prompt_count(chat_id)
        
        current_time = get_current_ist_time()
        
        # ====================================================================
        # LEVEL 1: BURST (10/minute) - CHECK FIRST (FAIL-FAST)
        # ====================================================================
        if current_counts['minute'] >= burst_limit:
            reset_at = (tracking['minute_window_start'] + timedelta(minutes=1)).isoformat()
            
            # Log violation
            await self._log_violation(
                user_id=user_id,
                chat_id=chat_id,
                violation_type="burst",
                limit_value=burst_limit,
                prompts_used=current_counts['minute'],
                user_message=user_message,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Send email notification
            await self.email_service.send_rate_limit_violation_email(
                user_id=user_id,
                violation_type="burst",
                limit=burst_limit
            )
            
            logger.warning(f"Burst rate limit exceeded for user {user_id}: {current_counts['minute']}/{burst_limit}")
            
            raise BurstRateLimitException(
                limit=burst_limit,
                used=current_counts['minute'],
                reset_at=reset_at
            )
        
        # ====================================================================
        # LEVEL 2: PER-CHAT (50/chat)
        # ====================================================================
        if per_chat_count >= per_chat_limit:
            # Log violation
            await self._log_violation(
                user_id=user_id,
                chat_id=chat_id,
                violation_type="per_chat",
                limit_value=per_chat_limit,
                prompts_used=per_chat_count,
                user_message=user_message,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Send email notification
            await self.email_service.send_rate_limit_violation_email(
                user_id=user_id,
                violation_type="per_chat",
                limit=per_chat_limit
            )
            
            logger.warning(f"Per-chat rate limit exceeded for user {user_id} in chat {chat_id}: {per_chat_count}/{per_chat_limit}")
            
            raise PerChatRateLimitException(
                limit=per_chat_limit,
                used=per_chat_count
            )
        
        # ====================================================================
        # LEVEL 3: HOURLY (150/hour)
        # ====================================================================
        if current_counts['hour'] >= hourly_limit:
            reset_at = (tracking['hour_window_start'] + timedelta(hours=1)).isoformat()
            
            # Log violation
            await self._log_violation(
                user_id=user_id,
                chat_id=chat_id,
                violation_type="hourly",
                limit_value=hourly_limit,
                prompts_used=current_counts['hour'],
                user_message=user_message,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Send email notification
            await self.email_service.send_rate_limit_violation_email(
                user_id=user_id,
                violation_type="hourly",
                limit=hourly_limit
            )
            
            logger.warning(f"Hourly rate limit exceeded for user {user_id}: {current_counts['hour']}/{hourly_limit}")
            
            raise HourlyRateLimitException(
                limit=hourly_limit,
                used=current_counts['hour'],
                reset_at=reset_at
            )
        
        # ====================================================================
        # LEVEL 4: DAILY (1000/24h)
        # ====================================================================
        if current_counts['day'] >= daily_limit:
            reset_at = (tracking['window_24h_start'] + timedelta(hours=24)).isoformat()
            
            # Log violation
            await self._log_violation(
                user_id=user_id,
                chat_id=chat_id,
                violation_type="daily",
                limit_value=daily_limit,
                prompts_used=current_counts['day'],
                user_message=user_message,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Send email notification
            await self.email_service.send_rate_limit_violation_email(
                user_id=user_id,
                violation_type="daily",
                limit=daily_limit
            )
            
            logger.warning(f"Daily rate limit exceeded for user {user_id}: {current_counts['day']}/{daily_limit}")
            
            raise DailyRateLimitException(
                limit=daily_limit,
                used=current_counts['day'],
                reset_at=reset_at
            )
        
        # ====================================================================
        # ALL CHECKS PASSED - INCREMENT COUNTERS
        # ====================================================================
        await self.rate_limit_repo.increment_counters(user_id, current_time)
        
        logger.info(f"Rate limit check passed for user {user_id}")
        
        return {
            "allowed": True,
            "current_usage": {
                "burst": current_counts['minute'] + 1,
                "per_chat": per_chat_count + 1,
                "hourly": current_counts['hour'] + 1,
                "daily": current_counts['day'] + 1
            },
            "limits": {
                "burst": burst_limit,
                "per_chat": per_chat_limit,
                "hourly": hourly_limit,
                "daily": daily_limit
            }
        }
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    async def _log_violation(
        self,
        user_id: str,
        chat_id: str,
        violation_type: str,
        limit_value: int,
        prompts_used: int,
        user_message: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> None:
        """Log rate limit violation to database"""
        violation_data = {
            'user_id': user_id,
            'chat_id': chat_id,
            'violation_type': violation_type,
            'limit_value': limit_value,
            'prompts_used': prompts_used,
            'action_taken': 'blocked',
            'user_message': user_message,
            'ip_address': ip_address,
            'user_agent': user_agent
        }
        
        await self.rate_limit_repo.log_violation(violation_data)
    
    # ========================================================================
    # ADMIN OPERATIONS
    # ========================================================================
    
    async def get_rate_limit_config(self) -> Dict[str, Any]:
        """Get current rate limit configuration"""
        return await self.rate_limit_repo.get_rate_limit_config()
    
    async def update_global_rate_limits(
        self,
        updates: Dict[str, Any],
        admin_id: str
    ) -> Dict[str, Any]:
        """Update global rate limits"""
        return await self.rate_limit_repo.update_global_rate_limits(updates, admin_id)
    
    async def set_user_rate_limits(
        self,
        user_id: str,
        limits: Dict[str, int],
        admin_id: str
    ) -> None:
        """Set user-specific rate limits"""
        await self.rate_limit_repo.set_user_specific_limits(user_id, limits, admin_id)
    
    async def whitelist_user(self, user_id: str, admin_id: str) -> None:
        """Add user to whitelist"""
        await self.rate_limit_repo.add_user_to_whitelist(user_id, admin_id)
    
    async def remove_whitelist(self, user_id: str, admin_id: str) -> None:
        """Remove user from whitelist"""
        await self.rate_limit_repo.remove_user_from_whitelist(user_id, admin_id)
    
    async def reset_user_limits(self, user_id: str) -> None:
        """Reset all counters for a user (admin action)"""
        await self.rate_limit_repo.reset_user_counters(user_id)
    
    async def get_violations(
        self,
        limit: int = 100,
        offset: int = 0,
        violation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get rate limit violations"""
        return await self.rate_limit_repo.get_all_violations(limit, offset, violation_type)

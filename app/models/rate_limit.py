from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class RateLimitConfig(BaseModel):
    config_id: str
    burst_limit_per_minute: int
    per_chat_limit: int
    per_hour_limit: int
    per_day_limit: int

    user_specific_overrides: Dict[str, Any] = {}
    whitelisted_users: List[str] = []

    created_at: datetime
    updated_at: datetime
    updated_by: Optional[str] = None

    class Config:
        from_attributes = True


class RateLimitTracking(BaseModel):
    tracking_id: str
    user_id: str

    prompts_current_minute: int
    minute_window_start: datetime

    prompts_current_hour: int
    hour_window_start: datetime

    prompts_current_24h: int
    window_24h_start: datetime

    last_prompt_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RateLimitViolation(BaseModel):
    violation_id: str
    user_id: str
    chat_id: Optional[str] = None

    violation_type: str  # burst, per_chat, hourly, daily
    limit_value: int
    prompts_used: int

    action_taken: str = "blocked"
    user_message: Optional[str] = None

    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    violated_at: datetime

    class Config:
        from_attributes = True


# ========================================================================
# RATE LIMITER CLASS - ADD THIS
# ========================================================================

class RateLimiter:
    """
    Rate limiting service for user requests
    
    Limits:
    - Burst: 10 requests per minute
    - Per Chat: 50 requests per chat
    - Hourly: 150 requests per hour
    - Daily: 1000 requests per day
    """
    
    # Default limits
    DEFAULT_LIMITS = {
        "burst": 10,              # per minute
        "per_chat": 50,           # per chat session
        "hourly": 150,            # per hour
        "daily": 1000             # per day (24 hours)
    }
    
    def __init__(self, db_pool, user_id: str):
        """
        Initialize Rate Limiter
        
        Args:
            db_pool: Database connection pool
            user_id: User's ID
        """
        self.db_pool = db_pool
        self.user_id = user_id
        self.limits = self.DEFAULT_LIMITS.copy()
    
    async def check_limits(self) -> Dict[str, Any]:
        """
        Check if user has exceeded rate limits
        
        Returns:
            {
                "allowed": bool,
                "error": str,
                "details": {
                    "violation_type": str,
                    "limit": int,
                    "used": int,
                    "reset_time": datetime
                }
            }
        """
        
        try:
            #  GET OR CREATE TRACKING RECORD
            tracking = await self._get_or_create_tracking()
            
            #  CHECK BURST LIMIT (per minute)
            if tracking["prompts_current_minute"] >= self.limits["burst"]:
                return {
                    "allowed": False,
                    "error": "Burst limit exceeded. Please wait before sending more messages.",
                    "details": {
                        "violation_type": "burst",
                        "limit": self.limits["burst"],
                        "used": tracking["prompts_current_minute"],
                        "reset_time": (tracking["minute_window_start"] + timedelta(minutes=1)).isoformat()
                    }
                }
            
            #  CHECK HOURLY LIMIT
            if tracking["prompts_current_hour"] >= self.limits["hourly"]:
                return {
                    "allowed": False,
                    "error": "Hourly limit exceeded. Please try again later.",
                    "details": {
                        "violation_type": "hourly",
                        "limit": self.limits["hourly"],
                        "used": tracking["prompts_current_hour"],
                        "reset_time": (tracking["hour_window_start"] + timedelta(hours=1)).isoformat()
                    }
                }
            
            #  CHECK DAILY LIMIT
            if tracking["prompts_current_24h"] >= self.limits["daily"]:
                return {
                    "allowed": False,
                    "error": "Daily limit exceeded. Please try again tomorrow.",
                    "details": {
                        "violation_type": "daily",
                        "limit": self.limits["daily"],
                        "used": tracking["prompts_current_24h"],
                        "reset_time": (tracking["window_24h_start"] + timedelta(days=1)).isoformat()
                    }
                }
            
            #  INCREMENT COUNTERS
            await self._increment_counters(tracking)
            
            logger.info(f"Rate limit check passed for user {self.user_id}")
            
            return {"allowed": True}
        
        except Exception as e:
            logger.error(f"Error checking rate limits: {str(e)}")
            # Allow request if rate limiting fails
            return {"allowed": True}

    async def _increment_counters(self, tracking: Dict[str, Any]) -> None:
        tracking["prompts_current_minute"] += 1
        tracking["prompts_current_hour"] += 1
        tracking["prompts_current_24h"] += 1
        tracking["last_prompt_at"] = datetime.now(timezone.utc)

        update_query = """
            UPDATE rate_limit_tracking
            SET 
                prompts_current_minute = $1,
                prompts_current_hour = $2,
                prompts_current_24h = $3,
                minute_window_start = $4,
                hour_window_start = $5,
                window_24h_start = $6,
                last_prompt_at = $7,
                updated_at = NOW()
            WHERE user_id = $8
        """

        try:
            await self.db_pool.execute(
                update_query,
                tracking["prompts_current_minute"],
                tracking["prompts_current_hour"],
                tracking["prompts_current_24h"],
                tracking["minute_window_start"],
                tracking["hour_window_start"],
                tracking["window_24h_start"],
                tracking["last_prompt_at"],
                self.user_id,
            )
        except Exception as e:
            logger.error(f"Error updating rate limit tracking: {str(e)}")

    
    async def get_current_usage(self) -> Dict[str, Any]:
        """
        Get current usage statistics for user
        
        Returns:
            {
                "current": {
                    "burst": int,
                    "per_chat": int,
                    "hourly": int,
                    "daily": int
                },
                "limits": {
                    "burst": int,
                    "per_chat": int,
                    "hourly": int,
                    "daily": int
                }
            }
        """
        
        try:
            tracking = await self._get_or_create_tracking()
            
            return {
                "current": {
                    "burst": tracking["prompts_current_minute"],
                    "per_chat": 0,  # Per-chat tracking would be separate
                    "hourly": tracking["prompts_current_hour"],
                    "daily": tracking["prompts_current_24h"]
                },
                "limits": self.limits
            }
        
        except Exception as e:
            logger.error(f"Error getting current usage: {str(e)}")
            return {
                "current": {"burst": 0, "per_chat": 0, "hourly": 0, "daily": 0},
                "limits": self.limits
            }
    
    async def _get_or_create_tracking(self) -> Dict[str, Any]:
        """Get or create rate limit tracking record"""
        now = datetime.now(timezone.utc)

        query = """
            SELECT 
                tracking_id,
                prompts_current_minute,
                minute_window_start,
                prompts_current_hour,
                hour_window_start,
                prompts_current_24h,
                window_24h_start,
                last_prompt_at
            FROM rate_limit_tracking
            WHERE user_id = $1
        """

        try:
            row = await self.db_pool.fetchrow(query, self.user_id)

            if row:
                # ✅ convert asyncpg.Record → plain dict
                tracking = dict(row)
                tracking = await self._reset_expired_windows(tracking, now)
                return tracking

        except Exception as e:
            logger.warning(f"Error fetching tracking record: {str(e)}")

        # ✅ no existing row → try to create
        await self._create_tracking_record(now)

        # Return a fresh in-memory dict for use in code
        return {
            "tracking_id": None,
            "prompts_current_minute": 0,
            "minute_window_start": now,
            "prompts_current_hour": 0,
            "hour_window_start": now,
            "prompts_current_24h": 0,
            "window_24h_start": now,
            "last_prompt_at": None,
        }

    
    async def _reset_expired_windows(self, tracking: Dict[str, Any], now: datetime) -> Dict[str, Any]:
        minute_window_start = tracking["minute_window_start"]
        hour_window_start = tracking["hour_window_start"]
        day_window_start = tracking["window_24h_start"]

        if minute_window_start.tzinfo is None:
            minute_window_start = minute_window_start.replace(tzinfo=timezone.utc)
        if hour_window_start.tzinfo is None:
            hour_window_start = hour_window_start.replace(tzinfo=timezone.utc)
        if day_window_start.tzinfo is None:
            day_window_start = day_window_start.replace(tzinfo=timezone.utc)

        if (now - minute_window_start).total_seconds() > 60:
            tracking["prompts_current_minute"] = 0
            tracking["minute_window_start"] = now

        if (now - hour_window_start).total_seconds() > 3600:
            tracking["prompts_current_hour"] = 0
            tracking["hour_window_start"] = now

        if (now - day_window_start).total_seconds() > 86400:
            tracking["prompts_current_24h"] = 0
            tracking["window_24h_start"] = now

        return tracking

    
    async def _create_tracking_record(self, now: datetime) -> None:
        """
        Create new rate limit tracking record
        
        Args:
            now: Current time
        """
        
        import uuid
        tracking_id = str(uuid.uuid4())
        
        insert_query = """
            INSERT INTO rate_limit_tracking 
            (tracking_id, user_id, prompts_current_minute, minute_window_start,
             prompts_current_hour, hour_window_start, prompts_current_24h, 
             window_24h_start, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
        """
        
        try:
            await self.db_pool.execute(
                insert_query,
                tracking_id,
                self.user_id,
                0,  # prompts_current_minute
                now,
                0,  # prompts_current_hour
                now,
                0,  # prompts_current_24h
                now
            )
            
            logger.info(f"Created new rate limit tracking for user {self.user_id}")
        
        except Exception as e:
            logger.error(f"Error creating tracking record: {str(e)}")
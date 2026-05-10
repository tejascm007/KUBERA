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


# ============================================================================
# RATE LIMITER CLASS
# ============================================================================

class RateLimiter:
    """
    Full rate limiting service.

    Checks (in order):
      1. Whitelist  → unlimited access
      2. Burst      → prompts per minute
      3. Per-chat   → prompts per chat session
      4. Hourly     → prompts per hour
      5. Daily      → prompts per 24 h

    Config is loaded from the database on every check so that admin
    changes take effect immediately without a server restart.
    """

    DEFAULT_LIMITS = {
        "burst":    10,
        "per_chat": 50,
        "hourly":   150,
        "daily":    1000,
    }

    def __init__(self, db_pool, user_id: str):
        self.db_pool = db_pool
        self.user_id = user_id

    # ------------------------------------------------------------------
    # PUBLIC: check_limits
    # ------------------------------------------------------------------

    async def check_limits(
        self,
        chat_id: Optional[str] = None,
        chat_prompt_count: int = 0,
        user_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check all rate limits for the current user before allowing a prompt.

        Args:
            chat_id:           Current chat UUID (for per-chat limit logging).
            chat_prompt_count: Number of assistant messages already in this chat.
            user_message:      The user's message text (stored on violation).

        Returns:
            {"allowed": True}
            {"allowed": False, "error": "...", "details": {...}}
        """
        try:
            from app.db.repositories.rate_limit_repository import RateLimitRepository
            repo = RateLimitRepository(self.db_pool)

            # ── 1. Load config & resolve effective limits ──────────────────
            config = await repo.get_rate_limit_config()
            limits = self._resolve_limits(config)

            # ── 2. Whitelist check ─────────────────────────────────────────
            if await repo.is_user_whitelisted(self.user_id):
                logger.info(f"User {self.user_id} is whitelisted — no limits applied")
                await self._increment(repo)
                return {"allowed": True, "whitelisted": True}

            # ── 3. Get / reset tracking windows ───────────────────────────
            tracking = await repo.get_or_create_tracking(self.user_id)
            tracking = self._reset_expired_windows(tracking)

            # ── 4. Burst check ─────────────────────────────────────────────
            if tracking["prompts_current_minute"] >= limits["burst"]:
                return await self._blocked(
                    repo, chat_id, user_message,
                    violation_type="burst",
                    limit=limits["burst"],
                    used=tracking["prompts_current_minute"],
                    reset_time=(
                        tracking["minute_window_start"] + timedelta(minutes=1)
                    ).isoformat(),
                    error="Burst limit exceeded. Please wait a moment before sending more messages.",
                )

            # ── 5. Per-chat check ──────────────────────────────────────────
            if chat_prompt_count >= limits["per_chat"]:
                return await self._blocked(
                    repo, chat_id, user_message,
                    violation_type="per_chat",
                    limit=limits["per_chat"],
                    used=chat_prompt_count,
                    reset_time=None,
                    error=f"This chat has reached its limit of {limits['per_chat']} prompts. Please start a new chat.",
                )

            # ── 6. Hourly check ────────────────────────────────────────────
            if tracking["prompts_current_hour"] >= limits["hourly"]:
                return await self._blocked(
                    repo, chat_id, user_message,
                    violation_type="hourly",
                    limit=limits["hourly"],
                    used=tracking["prompts_current_hour"],
                    reset_time=(
                        tracking["hour_window_start"] + timedelta(hours=1)
                    ).isoformat(),
                    error="Hourly limit exceeded. Please try again later.",
                )

            # ── 7. Daily check ─────────────────────────────────────────────
            if tracking["prompts_current_24h"] >= limits["daily"]:
                return await self._blocked(
                    repo, chat_id, user_message,
                    violation_type="daily",
                    limit=limits["daily"],
                    used=tracking["prompts_current_24h"],
                    reset_time=(
                        tracking["window_24h_start"] + timedelta(days=1)
                    ).isoformat(),
                    error="Daily limit exceeded. Please try again tomorrow.",
                )

            # ── 8. All checks passed — increment counters ──────────────────
            await self._increment(repo)
            logger.info(f"Rate limit check passed for user {self.user_id}")
            return {"allowed": True}

        except Exception as e:
            logger.error(f"Rate limit check error for user {self.user_id}: {e}")
            # Fail-open: don't block users if the rate limiter itself errors
            return {"allowed": True}

    # ------------------------------------------------------------------
    # PUBLIC: get_current_usage  (for connect message)
    # ------------------------------------------------------------------

    async def get_current_usage(self) -> Dict[str, Any]:
        """Return current usage counters and effective limits."""
        try:
            from app.db.repositories.rate_limit_repository import RateLimitRepository
            repo = RateLimitRepository(self.db_pool)
            config = await repo.get_rate_limit_config()
            limits = self._resolve_limits(config)
            tracking = await repo.get_or_create_tracking(self.user_id)
            tracking = self._reset_expired_windows(tracking)
            return {
                "current": {
                    "burst":    tracking["prompts_current_minute"],
                    "per_chat": 0,  # per-chat is chat-scoped, not global
                    "hourly":   tracking["prompts_current_hour"],
                    "daily":    tracking["prompts_current_24h"],
                },
                "limits": limits,
            }
        except Exception as e:
            logger.error(f"Error getting usage for user {self.user_id}: {e}")
            return {
                "current": {"burst": 0, "per_chat": 0, "hourly": 0, "daily": 0},
                "limits": self.DEFAULT_LIMITS,
            }

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _resolve_limits(self, config: Optional[Dict[str, Any]]) -> Dict[str, int]:
        """
        Build effective limits dict.
        Priority: user-specific override > global DB config > DEFAULT_LIMITS
        """
        if not config:
            return self.DEFAULT_LIMITS.copy()

        # Start from global DB config
        effective = {
            "burst":    config.get("burst_limit_per_minute", self.DEFAULT_LIMITS["burst"]),
            "per_chat": config.get("per_chat_limit",         self.DEFAULT_LIMITS["per_chat"]),
            "hourly":   config.get("per_hour_limit",         self.DEFAULT_LIMITS["hourly"]),
            "daily":    config.get("per_day_limit",          self.DEFAULT_LIMITS["daily"]),
        }

        # Apply user-specific overrides if they exist
        import json
        overrides = config.get("user_specific_overrides") or {}
        if isinstance(overrides, str):
            try:
                overrides = json.loads(overrides)
            except Exception:
                overrides = {}

        user_override = overrides.get(self.user_id) or overrides.get(str(self.user_id))
        if user_override:
            if isinstance(user_override, str):
                try:
                    user_override = json.loads(user_override)
                except Exception:
                    user_override = {}
            if isinstance(user_override, dict):
                if "burst_limit_per_minute" in user_override:
                    effective["burst"]    = user_override["burst_limit_per_minute"]
                if "per_chat_limit" in user_override:
                    effective["per_chat"] = user_override["per_chat_limit"]
                if "per_hour_limit" in user_override:
                    effective["hourly"]   = user_override["per_hour_limit"]
                if "per_day_limit" in user_override:
                    effective["daily"]    = user_override["per_day_limit"]
                logger.info(
                    f"User-specific overrides applied for {self.user_id}: {user_override}"
                )

        return effective

    def _reset_expired_windows(self, tracking: Dict[str, Any]) -> Dict[str, Any]:
        """Reset time windows that have expired."""
        now = datetime.now(timezone.utc)

        def tz(dt):
            return dt.replace(tzinfo=timezone.utc) if dt and dt.tzinfo is None else dt

        minute_start = tz(tracking.get("minute_window_start", now))
        hour_start   = tz(tracking.get("hour_window_start", now))
        day_start    = tz(tracking.get("window_24h_start", now))

        if (now - minute_start).total_seconds() > 60:
            tracking["prompts_current_minute"] = 0
            tracking["minute_window_start"]    = now

        if (now - hour_start).total_seconds() > 3600:
            tracking["prompts_current_hour"] = 0
            tracking["hour_window_start"]    = now

        if (now - day_start).total_seconds() > 86400:
            tracking["prompts_current_24h"] = 0
            tracking["window_24h_start"]    = now

        return tracking

    async def _increment(self, repo) -> None:
        """Increment all counters via the repository (atomic SQL CASE logic)."""
        try:
            now = datetime.now(timezone.utc)
            await repo.increment_counters(self.user_id, now)
        except Exception as e:
            logger.error(f"Error incrementing counters for {self.user_id}: {e}")

    async def _blocked(
        self,
        repo,
        chat_id: Optional[str],
        user_message: Optional[str],
        *,
        violation_type: str,
        limit: int,
        used: int,
        reset_time: Optional[str],
        error: str,
    ) -> Dict[str, Any]:
        """Log a violation and return the blocked response."""
        # Log to DB
        try:
            await repo.log_violation({
                "user_id":        self.user_id,
                "chat_id":        chat_id,
                "violation_type": violation_type,
                "limit_value":    limit,
                "prompts_used":   used,
                "action_taken":   "blocked",
                "user_message":   (user_message or "")[:500] if user_message else None,
            })
            logger.warning(
                f"Violation logged — user={self.user_id} type={violation_type} "
                f"used={used}/{limit}"
            )
        except Exception as e:
            logger.error(f"Failed to log violation: {e}")

        details: Dict[str, Any] = {
            "violation_type": violation_type,
            "limit":          limit,
            "used":           used,
        }
        if reset_time:
            details["reset_time"] = reset_time

        return {"allowed": False, "error": error, "details": details}
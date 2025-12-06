from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


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

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class EmailLog(BaseModel):
    log_id: str
    recipient_email: EmailStr

    email_type: str
    subject: Optional[str] = None

    sent: bool = False
    sent_at: Optional[datetime] = None
    failed: bool = False
    failure_reason: Optional[str] = None

    created_at: datetime

    class Config:
        from_attributes = True


class EmailPreferences(BaseModel):
    preference_id: str
    user_id: str

    portfolio_reports: bool = True
    rate_limit_notifications: bool = True
    system_notifications: bool = True
    security_alerts: bool = True

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

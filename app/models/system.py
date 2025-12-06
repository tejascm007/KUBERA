from datetime import datetime, time
from typing import Optional

from pydantic import BaseModel


class SystemStatus(BaseModel):
    status_id: str

    current_status: str  # running, stopped, maintenance

    portfolio_report_frequency: str  # disabled, daily, weekly, monthly
    portfolio_report_send_time: time
    portfolio_report_send_day_weekly: int
    portfolio_report_send_day_monthly: int
    portfolio_report_last_sent: Optional[datetime] = None
    portfolio_report_next_scheduled: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

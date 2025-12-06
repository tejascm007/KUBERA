from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr


class AdminBase(BaseModel):
    email: EmailStr
    full_name: str


class AdminCreate(AdminBase):
    is_super_admin: bool = True


class AdminInDBBase(AdminBase):
    admin_id: str
    is_super_admin: bool = True
    is_active: bool = True

    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Admin(AdminInDBBase):
    pass


class AdminActivityLog(BaseModel):
    log_id: str
    admin_id: str
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None

    old_value: Optional[Any] = None
    new_value: Optional[Any] = None

    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    performed_at: datetime

    class Config:
        from_attributes = True

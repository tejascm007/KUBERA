from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field


class PortfolioBase(BaseModel):
    stock_symbol: str = Field(max_length=50)
    exchange: str = Field(default="NSE", description="NSE or BSE")
    quantity: float = Field(gt=0)
    buy_price: float = Field(gt=0)
    buy_date: date
    notes: Optional[str] = None


class PortfolioCreate(PortfolioBase):
    pass


class PortfolioUpdate(BaseModel):
    quantity: Optional[float] = None
    buy_price: Optional[float] = None
    buy_date: Optional[date] = None
    notes: Optional[str] = None


class PortfolioInDBBase(PortfolioBase):
    portfolio_id: str
    user_id: str

    current_price: Optional[float] = None
    last_price_update: Optional[datetime] = None

    invested_amount: float
    current_value: float
    gain_loss: float
    gain_loss_percent: float

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Portfolio(PortfolioInDBBase):
    pass

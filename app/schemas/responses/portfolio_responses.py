"""
Portfolio Response Schemas
Pydantic models for portfolio endpoint responses
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


class PortfolioEntryResponse(BaseModel):
    """Response schema for single portfolio entry"""
    
    portfolio_id: str
    user_id: str
    stock_symbol: str
    exchange: str
    quantity: int
    buy_price: float
    buy_date: date
    investment_type: Optional[str] = None
    notes: Optional[str] = None
    
    # Current values
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    gain_loss: Optional[float] = None
    gain_loss_percent: Optional[float] = None
    
    created_at: datetime
    updated_at: datetime
    price_last_updated: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "portfolio_id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "stock_symbol": "INFY",
                "exchange": "NSE",
                "quantity": 10,
                "buy_price": 1450.50,
                "buy_date": "2024-01-15",
                "investment_type": "long-term",
                "notes": "Good entry point",
                "current_price": 1520.75,
                "current_value": 15207.50,
                "gain_loss": 702.50,
                "gain_loss_percent": 4.84,
                "created_at": "2024-01-15T10:30:00+05:30",
                "updated_at": "2024-12-05T11:00:00+05:30",
                "price_last_updated": "2024-12-05T10:45:00+05:30"
            }
        }


class PortfolioSummaryResponse(BaseModel):
    """Response schema for portfolio summary"""
    
    total_entries: int
    total_invested: float
    current_value: float
    total_gain_loss: float
    total_gain_loss_percent: float
    last_updated: Optional[datetime] = None


class PortfolioListResponse(BaseModel):
    """Response schema for portfolio list"""
    
    success: bool = True
    summary: PortfolioSummaryResponse
    portfolio: List[PortfolioEntryResponse]


class AddPortfolioResponse(BaseModel):
    """Response schema for adding portfolio entry"""
    
    success: bool = True
    message: str
    portfolio_entry: PortfolioEntryResponse


class UpdatePortfolioResponse(BaseModel):
    """Response schema for updating portfolio entry"""
    
    success: bool = True
    message: str
    portfolio_entry: PortfolioEntryResponse


class DeletePortfolioResponse(BaseModel):
    """Response schema for deleting portfolio entry"""
    
    success: bool = True
    message: str
    deleted_portfolio_id: str

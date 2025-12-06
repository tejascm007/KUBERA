"""
Portfolio Request Schemas
Pydantic models for portfolio endpoints
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import date


class AddPortfolioRequest(BaseModel):
    """Request schema for adding portfolio entry"""
    
    stock_symbol: str = Field(..., description="Stock symbol (e.g., INFY, TCS, RELIANCE)")
    exchange: str = Field(default="NSE", description="NSE or BSE")
    quantity: int = Field(..., gt=0, description="Number of shares")
    buy_price: float = Field(..., gt=0, description="Purchase price per share in INR")
    buy_date: str = Field(..., description="Purchase date (YYYY-MM-DD)")
    investment_type: Optional[str] = Field(None, description="long-term or short-term")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional notes")
    
    @validator('stock_symbol')
    def validate_stock_symbol(cls, v):
        return v.upper().strip()
    
    @validator('exchange')
    def validate_exchange(cls, v):
        if v.upper() not in ['NSE', 'BSE']:
            raise ValueError('Exchange must be NSE or BSE')
        return v.upper()
    
    @validator('investment_type')
    def validate_investment_type(cls, v):
        if v and v not in ['long-term', 'short-term']:
            raise ValueError('Investment type must be long-term or short-term')
        return v
    
    @validator('buy_date')
    def validate_buy_date(cls, v):
        try:
            buy_date = date.fromisoformat(v)
            if buy_date > date.today():
                raise ValueError('Buy date cannot be in the future')
            return v
        except ValueError:
            raise ValueError('Invalid date format. Use YYYY-MM-DD')
    
    class Config:
        json_schema_extra = {
            "example": {
                "stock_symbol": "INFY",
                "exchange": "NSE",
                "quantity": 10,
                "buy_price": 1450.50,
                "buy_date": "2024-01-15",
                "investment_type": "long-term",
                "notes": "Good entry point"
            }
        }


class UpdatePortfolioRequest(BaseModel):
    """Request schema for updating portfolio entry"""
    
    quantity: Optional[int] = Field(None, gt=0)
    buy_price: Optional[float] = Field(None, gt=0)
    buy_date: Optional[str] = Field(None)
    investment_type: Optional[str] = Field(None)
    notes: Optional[str] = Field(None, max_length=1000)
    
    @validator('investment_type')
    def validate_investment_type(cls, v):
        if v and v not in ['long-term', 'short-term']:
            raise ValueError('Investment type must be long-term or short-term')
        return v
    
    @validator('buy_date')
    def validate_buy_date(cls, v):
        if v:
            try:
                buy_date = date.fromisoformat(v)
                if buy_date > date.today():
                    raise ValueError('Buy date cannot be in the future')
                return v
            except ValueError:
                raise ValueError('Invalid date format. Use YYYY-MM-DD')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "quantity": 15,
                "notes": "Increased position"
            }
        }

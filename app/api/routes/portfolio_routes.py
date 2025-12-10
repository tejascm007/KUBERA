"""
Portfolio Routes
Endpoints for portfolio management
"""

from fastapi import APIRouter, Depends, status, Path
from typing import Dict, Any

from app.schemas.requests.portfolio_requests import (
    AddPortfolioRequest,
    UpdatePortfolioRequest
)
from app.schemas.responses.portfolio_responses import (
    PortfolioListResponse,
    AddPortfolioResponse,
    UpdatePortfolioResponse,
    DeletePortfolioResponse
)
from app.services.portfolio_service import PortfolioService
from app.core.dependencies import get_current_user, verify_user_owns_portfolio
from app.core.database import get_db_pool

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


# ============================================================================
# GET PORTFOLIO
# ============================================================================

@router.get(
    "/",
    response_model=PortfolioListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user portfolio",
    description="Get complete portfolio with current prices and summary"
)
async def get_portfolio(current_user: Dict = Depends(get_current_user)):
    """
    **Get User Portfolio**
    
    - Returns all portfolio entries
    - Includes current prices and gain/loss
    - Portfolio summary with totals
    """
    db_pool = await get_db_pool()
    portfolio_service = PortfolioService(db_pool)
    
    result = await portfolio_service.get_user_portfolio(current_user["user_id"])
    return result


# ============================================================================
# ADD PORTFOLIO ENTRY
# ============================================================================

@router.post(
    "/",
    response_model=AddPortfolioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add portfolio entry",
    description="Add a new stock to portfolio"
)
async def add_portfolio_entry(
    request: AddPortfolioRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    **Add Portfolio Entry**
    
    - Adds stock to portfolio
    - Validates stock symbol
    - Fetches current price
    - Calculates initial gain/loss
    """
    db_pool = await get_db_pool()
    portfolio_service = PortfolioService(db_pool)
    
    portfolio_data = request.dict()
    entry = await portfolio_service.add_portfolio_entry(
        current_user["user_id"],
        portfolio_data
    )
    
    return {
        "success": True,
        "message": "Portfolio entry added successfully",
        "portfolio_entry": entry
    }


# ============================================================================
# UPDATE PORTFOLIO ENTRY
# ============================================================================

@router.put(
    "/{portfolio_id}",
    response_model=UpdatePortfolioResponse,
    status_code=status.HTTP_200_OK,
    summary="Update portfolio entry",
    description="Update portfolio entry details"
)
async def update_portfolio_entry(
    portfolio_id: str = Path(..., description="Portfolio entry UUID"),
    request: UpdatePortfolioRequest = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    **Update Portfolio Entry**
    
    - Update quantity, buy price, notes, etc.
    - Cannot change stock symbol
    """
    db_pool = await get_db_pool()
    
    # Verify user owns this portfolio entry
    await verify_user_owns_portfolio(portfolio_id, current_user, db_pool)
    
    portfolio_service = PortfolioService(db_pool)
    
    updates = request.dict(exclude_unset=True)
    entry = await portfolio_service.update_portfolio_entry(portfolio_id, updates)
    
    return {
        "success": True,
        "message": "Portfolio entry updated successfully",
        "portfolio_entry": entry
    }


# ============================================================================
# DELETE PORTFOLIO ENTRY
# ============================================================================

@router.delete(
    "/{portfolio_id}",
    response_model=DeletePortfolioResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete portfolio entry",
    description="Remove stock from portfolio"
)
async def delete_portfolio_entry(
    portfolio_id: str = Path(..., description="Portfolio entry UUID"),
    current_user: Dict = Depends(get_current_user)
):
    """
    **Delete Portfolio Entry**
    
    - Removes stock from portfolio
    - Cannot be undone
    """
    db_pool = await get_db_pool()
    
    # Verify user owns this portfolio entry
    await verify_user_owns_portfolio(portfolio_id, current_user, db_pool)
    
    portfolio_service = PortfolioService(db_pool)
    
    deleted = await portfolio_service.delete_portfolio_entry(portfolio_id)
    
    if deleted:
        return {
            "success": True,
            "message": "Portfolio entry deleted successfully",
            "deleted_portfolio_id": portfolio_id
        }


# ============================================================================
# UPDATE PRICES
# ============================================================================

@router.post(
    "/update-prices",
    status_code=status.HTTP_200_OK,
    summary="Update portfolio prices",
    description="Fetch latest prices for all stocks in portfolio"
)
async def update_portfolio_prices(current_user: Dict = Depends(get_current_user)):
    """
    **Update Portfolio Prices**
    
    - Fetches current prices from yfinance
    - Updates gain/loss calculations
    - Returns update summary
    """
    db_pool = await get_db_pool()
    portfolio_service = PortfolioService(db_pool)
    
    result = await portfolio_service.update_portfolio_prices(current_user["user_id"])
    return result

"""
Portfolio Price Update Job
Updates stock prices for all portfolios (every 30 minutes)
"""

import logging
from datetime import datetime
import asyncpg

from app.services.portfolio_service import PortfolioService

logger = logging.getLogger(__name__)


async def update_all_portfolio_prices(db_pool: asyncpg.Pool):
    """
    Update prices for all stocks across all portfolios
    
    This job runs every 30 minutes and fetches latest prices
    from yfinance for all unique stocks in user portfolios.
    
    Args:
        db_pool: Database connection pool
    """
    start_time = datetime.now()
    
    try:
        logger.info("=" * 70)
        logger.info(" STARTING PORTFOLIO PRICE UPDATE JOB")
        logger.info(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S IST')}")
        logger.info("=" * 70)
        
        # Create portfolio service
        portfolio_service = PortfolioService(db_pool)
        
        # Update all prices
        result = await portfolio_service.bulk_update_all_prices()
        
        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 70)
        logger.info(" PORTFOLIO PRICE UPDATE COMPLETED")
        logger.info(f"Updated: {result['updated']} stocks")
        logger.info(f"Total: {result['total']} stocks")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f" Portfolio price update job failed: {e}", exc_info=True)


async def update_single_user_portfolio_prices(db_pool: asyncpg.Pool, user_id: str):
    """
    Update prices for a specific user's portfolio
    
    Can be triggered on-demand by user or admin
    
    Args:
        db_pool: Database connection pool
        user_id: User UUID
    """
    try:
        logger.info(f" Updating portfolio prices for user: {user_id}")
        
        portfolio_service = PortfolioService(db_pool)
        result = await portfolio_service.update_portfolio_prices(user_id)
        
        logger.info(f" Updated {result['updated']}/{result['total']} stocks for user {user_id}")
        
        return result
        
    except Exception as e:
        logger.error(f" Failed to update prices for user {user_id}: {e}")
        raise

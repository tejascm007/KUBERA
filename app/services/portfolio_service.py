"""
Portfolio Service
Business logic for portfolio management
"""

from typing import Dict, Any, List
import logging
import yfinance as yf

from app.db.repositories.portfolio_repository import PortfolioRepository
from app.exceptions.custom_exceptions import (
    DuplicatePortfolioException,
    InvalidStockSymbolException,
    PortfolioNotFoundException
)

logger = logging.getLogger(__name__)


class PortfolioService:
    """Portfolio management service"""
    
    def __init__(self, db_pool):
        self.db = db_pool
        self.portfolio_repo = PortfolioRepository(db_pool)
    
    # ========================================================================
    # PORTFOLIO OPERATIONS
    # ========================================================================
    
    async def get_user_portfolio(self, user_id: str) -> Dict[str, Any]:
        """
        Get complete user portfolio with summary
        
        Args:
            user_id: User UUID
        
        Returns:
            Portfolio entries and summary
        """
        # Get all portfolio entries
        entries = await self.portfolio_repo.get_user_portfolio(user_id)
        
        # Get summary
        summary = await self.portfolio_repo.get_portfolio_summary(user_id)
        
        return {
            "success": True,
            "summary": summary,
            "portfolio": entries
        }
    
    async def add_portfolio_entry(
        self,
        user_id: str,
        portfolio_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add new portfolio entry
        
        Args:
            user_id: User UUID
            portfolio_data: Portfolio entry data
        
        Returns:
            Created portfolio entry
        
        Raises:
            DuplicatePortfolioException: Stock already in portfolio
            InvalidStockSymbolException: Invalid stock symbol
        """
        stock_symbol = portfolio_data['stock_symbol'].upper()
        exchange = portfolio_data.get('exchange', 'NSE').upper()
        
        # Check if stock already exists for user
        existing = await self.portfolio_repo.get_portfolio_by_stock(user_id, stock_symbol)
        if existing:
            raise DuplicatePortfolioException(stock_symbol)
        
        # Validate stock symbol by fetching current price
        try:
            current_price = await self._fetch_stock_price(stock_symbol, exchange)
        except Exception as e:
            logger.error(f"Invalid stock symbol {stock_symbol}: {e}")
            raise InvalidStockSymbolException(stock_symbol)
        
        # Add user_id and current_price to data
        portfolio_data['user_id'] = user_id
        portfolio_data['stock_symbol'] = stock_symbol
        portfolio_data['exchange'] = exchange
        
        # Create entry
        entry = await self.portfolio_repo.create_portfolio_entry(portfolio_data)
        
        # Update with current price
        if entry and current_price:
            await self.portfolio_repo.update_current_price(entry['portfolio_id'], current_price)
            entry = await self.portfolio_repo.get_portfolio_by_id(entry['portfolio_id'])
        
        logger.info(f"Portfolio entry added for user {user_id}: {stock_symbol}")
        
        return entry
    
    async def update_portfolio_entry(
        self,
        portfolio_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update portfolio entry
        
        Args:
            portfolio_id: Portfolio UUID
            updates: Fields to update
        
        Returns:
            Updated portfolio entry
        """
        # Remove fields that shouldn't be updated
        updates.pop('user_id', None)
        updates.pop('stock_symbol', None)
        updates.pop('exchange', None)
        updates.pop('portfolio_id', None)
        
        entry = await self.portfolio_repo.update_portfolio_entry(portfolio_id, updates)
        
        logger.info(f"Portfolio entry updated: {portfolio_id}")
        
        return entry
    
    async def delete_portfolio_entry(self, portfolio_id: str) -> bool:
        """
        Delete portfolio entry
        
        Args:
            portfolio_id: Portfolio UUID
        
        Returns:
            True if deleted
        """
        deleted = await self.portfolio_repo.delete_portfolio_entry(portfolio_id)
        
        if deleted:
            logger.info(f"Portfolio entry deleted: {portfolio_id}")
        
        return deleted
    
    # ========================================================================
    # PRICE UPDATES
    # ========================================================================
    
    async def _fetch_stock_price(self, stock_symbol: str, exchange: str = "NSE") -> float:
        """
        Fetch current stock price from Yahoo Finance
        
        Args:
            stock_symbol: Stock symbol
            exchange: NSE or BSE
        
        Returns:
            Current price in INR
        """
        # Add suffix for Yahoo Finance
        suffix = ".NS" if exchange == "NSE" else ".BO"
        ticker = f"{stock_symbol}{suffix}"
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Try different price fields
            price = (
                info.get('currentPrice') or
                info.get('regularMarketPrice') or
                info.get('previousClose')
            )
            
            if price:
                return float(price)
            
            # Fallback: try history
            hist = stock.history(period="1d")
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
            
            raise Exception("No price data available")
            
        except Exception as e:
            logger.error(f"Error fetching price for {ticker}: {e}")
            raise
    
    async def update_portfolio_prices(self, user_id: str) -> Dict[str, Any]:
        """
        Update all portfolio prices for a user
        
        Args:
            user_id: User UUID
        
        Returns:
            Update summary
        """
        entries = await self.portfolio_repo.get_user_portfolio(user_id)
        
        updated_count = 0
        failed_count = 0
        
        for entry in entries:
            try:
                current_price = await self._fetch_stock_price(
                    entry['stock_symbol'],
                    entry['exchange']
                )
                
                await self.portfolio_repo.update_current_price(
                    entry['portfolio_id'],
                    current_price
                )
                
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Failed to update price for {entry['stock_symbol']}: {e}")
                failed_count += 1
        
        logger.info(f"Portfolio prices updated for user {user_id}: {updated_count} success, {failed_count} failed")
        
        return {
            "success": True,
            "updated": updated_count,
            "failed": failed_count,
            "total": len(entries)
        }
    
    async def bulk_update_all_prices(self) -> Dict[str, Any]:
        """
        Update prices for all stocks across all users (background job)
        
        Returns:
            Update summary
        """
        # Get all unique stock symbols
        symbols = await self.portfolio_repo.get_all_unique_stock_symbols()
        
        price_updates = []
        
        for symbol in symbols:
            try:
                # Assume NSE by default
                price = await self._fetch_stock_price(symbol, "NSE")
                price_updates.append({
                    'stock_symbol': symbol,
                    'price': price
                })
            except:
                # Try BSE
                try:
                    price = await self._fetch_stock_price(symbol, "BSE")
                    price_updates.append({
                        'stock_symbol': symbol,
                        'price': price
                    })
                except Exception as e:
                    logger.error(f"Failed to fetch price for {symbol}: {e}")
        
        # Bulk update
        if price_updates:
            await self.portfolio_repo.bulk_update_prices(price_updates)
        
        logger.info(f"Bulk price update completed: {len(price_updates)}/{len(symbols)} stocks")
        
        return {
            "success": True,
            "updated": len(price_updates),
            "total": len(symbols)
        }

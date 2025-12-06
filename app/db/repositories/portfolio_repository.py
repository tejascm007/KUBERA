"""
Portfolio Repository
Database operations for portfolios table
"""

import asyncpg
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.core.security import get_current_ist_time

logger = logging.getLogger(__name__)


class PortfolioRepository:
    """Repository for portfolio database operations"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    # ========================================================================
    # CREATE
    # ========================================================================
    
    async def create_portfolio_entry(
        self,
        portfolio_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new portfolio entry"""
        query = """
            INSERT INTO portfolios (
                user_id, stock_symbol, exchange, quantity,
                buy_price, buy_date, investment_type, notes
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                query,
                portfolio_data.get('user_id'),
                portfolio_data.get('stock_symbol').upper(),
                portfolio_data.get('exchange', 'NSE').upper(),
                portfolio_data.get('quantity'),
                portfolio_data.get('buy_price'),
                portfolio_data.get('buy_date'),
                portfolio_data.get('investment_type'),
                portfolio_data.get('notes')
            )
            return dict(row) if row else None
    
    # ========================================================================
    # READ
    # ========================================================================
    
    async def get_portfolio_by_id(
        self,
        portfolio_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get portfolio entry by ID"""
        query = "SELECT * FROM portfolios WHERE portfolio_id = $1"
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, portfolio_id)
            return dict(row) if row else None
    
    async def get_user_portfolio(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Get all portfolio entries for a user"""
        query = """
            SELECT * FROM portfolios
            WHERE user_id = $1
            ORDER BY created_at DESC
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, user_id)
            return [dict(row) for row in rows]
    
    async def get_portfolio_by_stock(
        self,
        user_id: str,
        stock_symbol: str
    ) -> Optional[Dict[str, Any]]:
        """Check if user already has this stock in portfolio"""
        query = """
            SELECT * FROM portfolios
            WHERE user_id = $1 AND stock_symbol = $2
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, user_id, stock_symbol.upper())
            return dict(row) if row else None
    
    async def get_all_unique_stock_symbols(self) -> List[str]:
        """Get all unique stock symbols across all users"""
        query = "SELECT DISTINCT stock_symbol FROM portfolios"
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query)
            return [row['stock_symbol'] for row in rows]
    
    async def count_user_portfolio_entries(self, user_id: str) -> int:
        """Count portfolio entries for user"""
        query = "SELECT COUNT(*) FROM portfolios WHERE user_id = $1"
        
        async with self.db.acquire() as conn:
            return await conn.fetchval(query, user_id)
    
    # ========================================================================
    # UPDATE
    # ========================================================================
    
    async def update_portfolio_entry(
        self,
        portfolio_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update portfolio entry"""
        # Build dynamic update query
        set_clauses = []
        values = []
        param_count = 1
        
        for key, value in updates.items():
            if key not in ['portfolio_id', 'user_id', 'created_at', 'updated_at']:
                set_clauses.append(f"{key} = ${param_count}")
                values.append(value)
                param_count += 1
        
        if not set_clauses:
            return await self.get_portfolio_by_id(portfolio_id)
        
        # Add updated_at
        set_clauses.append(f"updated_at = ${param_count}")
        values.append(get_current_ist_time())
        param_count += 1
        
        # Add portfolio_id for WHERE clause
        values.append(portfolio_id)
        
        query = f"""
            UPDATE portfolios
            SET {', '.join(set_clauses)}
            WHERE portfolio_id = ${param_count}
            RETURNING *
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            return dict(row) if row else None
    
    async def update_current_price(
        self,
        portfolio_id: str,
        current_price: float
    ) -> None:
        """Update current price and calculate gains/losses"""
        query = """
            UPDATE portfolios
            SET 
                current_price = $1,
                current_value = quantity * $1,
                gain_loss = (quantity * $1) - (quantity * buy_price),
                gain_loss_percent = (((quantity * $1) - (quantity * buy_price)) / (quantity * buy_price)) * 100,
                price_last_updated = $2,
                updated_at = $2
            WHERE portfolio_id = $3
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(
                query,
                current_price,
                get_current_ist_time(),
                portfolio_id
            )
    
    async def bulk_update_prices(
        self,
        price_updates: List[Dict[str, Any]]
    ) -> None:
        """
        Bulk update prices for multiple stocks
        
        Args:
            price_updates: List of dicts with 'stock_symbol' and 'price'
        """
        query = """
            UPDATE portfolios
            SET 
                current_price = $1,
                current_value = quantity * $1,
                gain_loss = (quantity * $1) - (quantity * buy_price),
                gain_loss_percent = (((quantity * $1) - (quantity * buy_price)) / (quantity * buy_price)) * 100,
                price_last_updated = $2,
                updated_at = $2
            WHERE stock_symbol = $3
        """
        
        current_time = get_current_ist_time()
        
        async with self.db.acquire() as conn:
            async with conn.transaction():
                for update in price_updates:
                    await conn.execute(
                        query,
                        update['price'],
                        current_time,
                        update['stock_symbol']
                    )
    
    # ========================================================================
    # DELETE
    # ========================================================================
    
    async def delete_portfolio_entry(self, portfolio_id: str) -> bool:
        """Delete a portfolio entry"""
        query = "DELETE FROM portfolios WHERE portfolio_id = $1"
        
        async with self.db.acquire() as conn:
            result = await conn.execute(query, portfolio_id)
            return result == "DELETE 1"
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    async def get_portfolio_summary(self, user_id: str) -> Dict[str, Any]:
        """Get portfolio summary with totals"""
        query = """
            SELECT
                COUNT(*) as total_entries,
                COALESCE(SUM(quantity * buy_price), 0) as total_invested,
                COALESCE(SUM(current_value), 0) as current_value,
                COALESCE(SUM(gain_loss), 0) as total_gain_loss,
                CASE 
                    WHEN SUM(quantity * buy_price) > 0 THEN
                        (SUM(gain_loss) / SUM(quantity * buy_price)) * 100
                    ELSE 0
                END as total_gain_loss_percent,
                MAX(price_last_updated) as last_updated
            FROM portfolios
            WHERE user_id = $1
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            return dict(row) if row else {}

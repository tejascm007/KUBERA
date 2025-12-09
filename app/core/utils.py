"""
Utility functions for API calls with timeout protection
"""

import asyncio
import yfinance as yf
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# TIMEOUT WRAPPERS FOR YFINANCE
# ============================================================================

async def fetch_ticker_safe(ticker_symbol: str, timeout: int = 10) -> Optional[yf.Ticker]:
    """
    Fetch Yahoo Finance ticker with timeout protection.
    
    Args:
        ticker_symbol: Stock ticker (e.g., "INFY.NS")
        timeout: Timeout in seconds (default: 10)
    
    Returns:
        yfinance.Ticker object or None if timeout
    
    Raises:
        TimeoutError: If fetch exceeds timeout
        Exception: If ticker not found
    """
    loop = asyncio.get_event_loop()
    try:
        logger.debug(f"Fetching ticker {ticker_symbol} with {timeout}s timeout")
        stock = await asyncio.wait_for(
            loop.run_in_executor(None, yf.Ticker, ticker_symbol),
            timeout=timeout
        )
        logger.debug(f" Ticker {ticker_symbol} fetched successfully")
        return stock
    except asyncio.TimeoutError:
        logger.error(f"⏱ Timeout fetching {ticker_symbol} after {timeout}s")
        raise TimeoutError(f"Yahoo Finance timeout for {ticker_symbol} after {timeout}s")
    except Exception as e:
        logger.error(f"Error fetching ticker {ticker_symbol}: {str(e)}")
        raise Exception(f"Failed to fetch ticker {ticker_symbol}: {str(e)}")


async def fetch_history_safe(
    stock: yf.Ticker,
    period: str = "1y",
    timeout: int = 15
) -> Any:
    """
    Fetch historical price data with timeout protection.
    
    Args:
        stock: yfinance.Ticker object
        period: Time period (e.g., "1y", "6mo", "3mo")
        timeout: Timeout in seconds (default: 15)
    
    Returns:
        DataFrame with OHLCV data
    
    Raises:
        TimeoutError: If fetch exceeds timeout
    """
    loop = asyncio.get_event_loop()
    try:
        logger.debug(f"Fetching history for {period} with {timeout}s timeout")
        hist = await asyncio.wait_for(
            loop.run_in_executor(None, stock.history, period),
            timeout=timeout
        )
        logger.debug(f" History fetched: {len(hist)} records")
        return hist
    except asyncio.TimeoutError:
        logger.error(f"⏱ History timeout after {timeout}s")
        raise TimeoutError(f"History fetch timeout after {timeout}s")
    except Exception as e:
        logger.error(f" Error fetching history: {str(e)}")
        raise Exception(f"Failed to fetch history: {str(e)}")


async def fetch_info_safe(
    stock: yf.Ticker,
    timeout: int = 10
) -> dict:
    """Fetch company info with timeout"""
    loop = asyncio.get_event_loop()
    try:
        logger.debug(f"Fetching info with {timeout}s timeout")
        info = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: stock.info),
            timeout=timeout
        )
        return info
    except asyncio.TimeoutError:
        logger.error(f"⏱ Info timeout after {timeout}s")
        raise TimeoutError(f"Info fetch timeout after {timeout}s")
    except Exception as e:
        logger.error(f" Error fetching info: {str(e)}")
        raise Exception(f"Failed to fetch info: {str(e)}")


async def fetch_financials_safe(
    stock: yf.Ticker,
    timeout: int = 15
) -> Any:
    """Fetch financial statements with timeout"""
    loop = asyncio.get_event_loop()
    try:
        logger.debug(f"Fetching financials with {timeout}s timeout")
        financials = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: stock.financials),
            timeout=timeout
        )
        return financials
    except asyncio.TimeoutError:
        logger.error(f"⏱ Financials timeout after {timeout}s")
        raise TimeoutError(f"Financials fetch timeout after {timeout}s")
    except Exception as e:
        logger.error(f"Error fetching financials: {str(e)}")
        raise Exception(f"Failed to fetch financials: {str(e)}")

"""
Utility functions for API calls with timeout protection

Both sync and async versions are provided:
- Sync functions (fetch_ticker_safe, fetch_info_safe, etc.) - For use in MCP server tools
- Async functions (fetch_ticker_safe_async, etc.) - For use in async contexts
"""

import asyncio
import yfinance as yf
from typing import Optional, Any
import logging
import concurrent.futures
import signal
from functools import wraps

logger = logging.getLogger(__name__)

# ============================================================================
# SYNCHRONOUS WRAPPERS FOR MCP SERVERS
# These are the primary functions to use in MCP tool functions
# ============================================================================

def fetch_ticker_safe(ticker_symbol: str, timeout: int = 10) -> Optional[yf.Ticker]:
    """
    Fetch Yahoo Finance ticker with timeout protection (SYNCHRONOUS).
    
    Args:
        ticker_symbol: Stock ticker (e.g., "INFY.NS")
        timeout: Timeout in seconds (default: 10)
    
    Returns:
        yfinance.Ticker object
    
    Raises:
        TimeoutError: If fetch exceeds timeout
        Exception: If ticker not found
    """
    try:
        logger.debug(f"Fetching ticker {ticker_symbol} with {timeout}s timeout")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(yf.Ticker, ticker_symbol)
            stock = future.result(timeout=timeout)
        
        logger.debug(f"Ticker {ticker_symbol} fetched successfully")
        return stock
    except concurrent.futures.TimeoutError:
        logger.error(f"Timeout fetching {ticker_symbol} after {timeout}s")
        raise TimeoutError(f"Yahoo Finance timeout for {ticker_symbol} after {timeout}s")
    except Exception as e:
        logger.error(f"Error fetching ticker {ticker_symbol}: {str(e)}")
        raise Exception(f"Failed to fetch ticker {ticker_symbol}: {str(e)}")


def fetch_history_safe(
    stock: yf.Ticker,
    period: str = "1y",
    interval: str = "1d",
    timeout: int = 15
) -> Any:
    """
    Fetch historical price data with timeout protection (SYNCHRONOUS).
    
    Args:
        stock: yfinance.Ticker object
        period: Time period (e.g., "1y", "6mo", "3mo")
        interval: Data interval (e.g., "1d", "1wk")
        timeout: Timeout in seconds (default: 15)
    
    Returns:
        DataFrame with OHLCV data
    
    Raises:
        TimeoutError: If fetch exceeds timeout
    """
    try:
        logger.debug(f"Fetching history for {period} with {timeout}s timeout")
        
        def _fetch():
            return stock.history(period=period, interval=interval)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_fetch)
            hist = future.result(timeout=timeout)
        
        logger.debug(f"History fetched: {len(hist)} records")
        return hist
    except concurrent.futures.TimeoutError:
        logger.error(f"History timeout after {timeout}s")
        raise TimeoutError(f"History fetch timeout after {timeout}s")
    except Exception as e:
        logger.error(f"Error fetching history: {str(e)}")
        raise Exception(f"Failed to fetch history: {str(e)}")


def fetch_info_safe(stock: yf.Ticker, timeout: int = 10) -> dict:
    """
    Fetch company info with timeout (SYNCHRONOUS).
    
    Args:
        stock: yfinance.Ticker object
        timeout: Timeout in seconds
    
    Returns:
        Dictionary with company info
    """
    try:
        logger.debug(f"Fetching info with {timeout}s timeout")
        
        def _fetch():
            return stock.info
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_fetch)
            info = future.result(timeout=timeout)
        
        logger.debug(f"Info fetched successfully")
        return info
    except concurrent.futures.TimeoutError:
        logger.error(f"Info timeout after {timeout}s")
        raise TimeoutError(f"Info fetch timeout after {timeout}s")
    except Exception as e:
        logger.error(f"Error fetching info: {str(e)}")
        raise Exception(f"Failed to fetch info: {str(e)}")


def fetch_financials_safe(stock: yf.Ticker, timeout: int = 15) -> Any:
    """
    Fetch financial statements with timeout (SYNCHRONOUS).
    
    Args:
        stock: yfinance.Ticker object
        timeout: Timeout in seconds
    
    Returns:
        DataFrame with financial data
    """
    try:
        logger.debug(f"Fetching financials with {timeout}s timeout")
        
        def _fetch():
            return stock.financials
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_fetch)
            financials = future.result(timeout=timeout)
        
        logger.debug(f"Financials fetched successfully")
        return financials
    except concurrent.futures.TimeoutError:
        logger.error(f"Financials timeout after {timeout}s")
        raise TimeoutError(f"Financials fetch timeout after {timeout}s")
    except Exception as e:
        logger.error(f"Error fetching financials: {str(e)}")
        raise Exception(f"Failed to fetch financials: {str(e)}")


# ============================================================================
# ASYNC VERSIONS (for use in async contexts like websockets)
# ============================================================================

async def fetch_ticker_safe_async(ticker_symbol: str, timeout: int = 10) -> Optional[yf.Ticker]:
    """Async version of fetch_ticker_safe"""
    loop = asyncio.get_event_loop()
    try:
        stock = await asyncio.wait_for(
            loop.run_in_executor(None, yf.Ticker, ticker_symbol),
            timeout=timeout
        )
        return stock
    except asyncio.TimeoutError:
        raise TimeoutError(f"Yahoo Finance timeout for {ticker_symbol} after {timeout}s")
    except Exception as e:
        raise Exception(f"Failed to fetch ticker {ticker_symbol}: {str(e)}")


async def fetch_history_safe_async(
    stock: yf.Ticker,
    period: str = "1y",
    timeout: int = 15
) -> Any:
    """Async version of fetch_history_safe"""
    loop = asyncio.get_event_loop()
    try:
        hist = await asyncio.wait_for(
            loop.run_in_executor(None, stock.history, period),
            timeout=timeout
        )
        return hist
    except asyncio.TimeoutError:
        raise TimeoutError(f"History fetch timeout after {timeout}s")
    except Exception as e:
        raise Exception(f"Failed to fetch history: {str(e)}")


async def fetch_info_safe_async(stock: yf.Ticker, timeout: int = 10) -> dict:
    """Async version of fetch_info_safe"""
    loop = asyncio.get_event_loop()
    try:
        info = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: stock.info),
            timeout=timeout
        )
        return info
    except asyncio.TimeoutError:
        raise TimeoutError(f"Info fetch timeout after {timeout}s")
    except Exception as e:
        raise Exception(f"Failed to fetch info: {str(e)}")


async def fetch_financials_safe_async(stock: yf.Ticker, timeout: int = 15) -> Any:
    """Async version of fetch_financials_safe"""
    loop = asyncio.get_event_loop()
    try:
        financials = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: stock.financials),
            timeout=timeout
        )
        return financials
    except asyncio.TimeoutError:
        raise TimeoutError(f"Financials fetch timeout after {timeout}s")
    except Exception as e:
        raise Exception(f"Failed to fetch financials: {str(e)}")


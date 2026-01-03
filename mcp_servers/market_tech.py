"""
MCP SERVER 2: MARKET DATA & TECHNICAL SERVER
Purpose: Fetch price data, technical indicators, volume, and market metrics
Data Sources: Yahoo Finance, NSE, Finnhub, TA-Lib
"""

from fastmcp import FastMCP
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.utils import fetch_ticker_safe, fetch_history_safe, fetch_info_safe, fetch_financials_safe

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    print("Warning: TA-Lib not available. Technical indicators will use pandas calculations.")

# Load environment variables from .env file (required for MCP subprocess)
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Initialize FastMCP
mcp = FastMCP("MarketDataTechnicalServer")

# API Keys
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

# Constants
NSE_SUFFIX = ".NS"
BSE_SUFFIX = ".BO"

def get_stock_ticker(symbol: str, exchange: str = "NSE") -> str:
    """Convert Indian stock symbol to Yahoo Finance ticker format."""
    symbol = symbol.upper().strip()
    if exchange.upper() == "NSE":
        return f"{symbol}{NSE_SUFFIX}" if not symbol.endswith(NSE_SUFFIX) else symbol
    return symbol

def handle_error(error_type: str, symbol: str, message: str) -> Dict:
    """Standardized error response."""
    return {
        "status": "error",
        "error_type": error_type,
        "stock_symbol": symbol,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }


@mcp.tool()
def fetch_current_price_data(
    stock_symbol: str,
    include_details: bool = True
) -> Dict[str, Any]:
    """
    Get real-time or latest price with key metrics.
    
    Args:
        stock_symbol: Stock symbol (e.g., "INFY")
        include_details: Include 52-week range, volume, etc.
    
    Returns:
        Current price data with day metrics and ranges
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock =  fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        info =  fetch_info_safe(stock, timeout=10)
        hist =  fetch_history_safe(stock, period="5d")
        
        if hist.empty or not info:
            return handle_error(
                "data_unavailable",
                stock_symbol,
                "Unable to fetch current price data"
            )
        
        latest = hist.iloc[-1]
        current_price = latest['Close']
        
        result = {
            "stock_symbol": stock_symbol,
            "current_price": round(current_price, 2),
            "currency": "INR",
            "timestamp": datetime.utcnow().isoformat(),
            
            "day_data": {
                "open": round(latest['Open'], 2),
                "high": round(latest['High'], 2),
                "low": round(latest['Low'], 2),
                "close": round(latest['Close'], 2),
                "volume": int(latest['Volume']),
                "volume_value_cr": round((latest['Volume'] * latest['Close']) / 10000000, 2)
            }
        }
        
        if include_details:
            # Calculate price changes
            if len(hist) >= 2:
                prev_close = hist.iloc[-2]['Close']
                result["changes"] = {
                    "price_change_1d_percent": round(((current_price - prev_close) / prev_close) * 100, 2)
                }
            
            # 52-week high/low
            result["range_data"] = {
                "52_week_high": round(info.get("fiftyTwoWeekHigh", 0), 2),
                "52_week_low": round(info.get("fiftyTwoWeekLow", 0), 2),
                "52_week_change_percent": round(info.get("52WeekChange", 0) * 100, 2) if info.get("52WeekChange") else None
            }
            
            # Market metrics
            result["market_metrics"] = {
                "market_cap_cr": round(info.get("marketCap", 0) / 10000000, 2) if info.get("marketCap") else None,
                "avg_volume": int(info.get("averageVolume", 0))
            }
        
        result["data_source"] = "Yahoo Finance Real-time"
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching price data: {str(e)}"
        )


@mcp.tool()
def fetch_historical_price_data(
    stock_symbol: str,
    start_date: str,
    end_date: str,
    interval: str = "daily"
) -> Dict[str, Any]:
    """
    Get OHLCV (Open, High, Low, Close, Volume) data for any period.
    
    Args:
        stock_symbol: Stock symbol
        start_date: Start date "YYYY-MM-DD"
        end_date: End date "YYYY-MM-DD"
        interval: "daily", "weekly", or "monthly"
    
    Returns:
        Historical OHLCV data
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock =  fetch_ticker_safe(ticker, timeout=10)
        
        # Map interval
        interval_map = {
            "daily": "1d",
            "weekly": "1wk",
            "monthly": "1mo"
        }
        yf_interval = interval_map.get(interval, "1d")
        
        hist =  fetch_history_safe(stock, start=start_date, end=end_date, interval=yf_interval)
        
        if hist.empty:
            return handle_error(
                "data_unavailable",
                stock_symbol,
                f"No historical data available for {start_date} to {end_date}"
            )
        
        data = []
        for index, row in hist.iterrows():
            data.append({
                "date": index.strftime("%Y-%m-%d"),
                "open": round(row['Open'], 2),
                "high": round(row['High'], 2),
                "low": round(row['Low'], 2),
                "close": round(row['Close'], 2),
                "volume": int(row['Volume'])
            })
        
        return {
            "stock_symbol": stock_symbol,
            "data": data,
            "total_records": len(data),
            "period": f"{start_date} to {end_date}",
            "interval": interval,
            "data_source": "Yahoo Finance",
            "currency": "INR"
        }
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching historical data: {str(e)}"
        )


@mcp.tool()
def fetch_technical_indicators(
    stock_symbol: str,
    indicators: List[str],
    period: str = "6m"
) -> Dict[str, Any]:
    """
    Calculate and return technical analysis indicators.
    
    Args:
        stock_symbol: Stock symbol
        indicators: List of indicators ["SMA50", "SMA200", "RSI", "MACD", "BBands"]
        period: "3m", "6m", "1y", "3y"
    
    Returns:
        Technical indicators with signals
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock =  fetch_ticker_safe(ticker, timeout=10)
        
        # Map period to days
        period_map = {"3m": 90, "6m": 180, "1y": 365, "3y": 1095}
        days = period_map.get(period, 180)
        
        hist =  fetch_history_safe(stock, period=f"{days}d")
        
        if hist.empty:
            return handle_error(
                "data_unavailable",
                stock_symbol,
                "Insufficient data for technical analysis"
            )
        
        close_prices = hist['Close']
        current_price = close_prices.iloc[-1]
        
        result = {
            "stock_symbol": stock_symbol,
            "as_of_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "indicators": {}
        }
        
        # Calculate SMA
        if "SMA50" in indicators or "SMA" in indicators:
            sma50 = close_prices.rolling(window=50).mean().iloc[-1]
            sma200 = close_prices.rolling(window=200).mean().iloc[-1] if len(close_prices) >= 200 else None
            
            result["indicators"]["SMA"] = {
                "sma_50": round(sma50, 2),
                "sma_200": round(sma200, 2) if sma200 else None,
                "price_vs_sma50": round(((current_price - sma50) / sma50) * 100, 2),
                "price_vs_sma200": round(((current_price - sma200) / sma200) * 100, 2) if sma200 else None,
                "signal": "bullish" if current_price > sma50 else "bearish"
            }
        
        # Calculate RSI
        if "RSI" in indicators:
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_value = rsi.iloc[-1]
            
            result["indicators"]["RSI"] = {
                "rsi_14": round(rsi_value, 2),
                "status": "oversold" if rsi_value < 30 else "overbought" if rsi_value > 70 else "neutral",
                "signal": "buy" if rsi_value < 30 else "sell" if rsi_value > 70 else "hold"
            }
        
        # Calculate MACD
        if "MACD" in indicators:
            exp1 = close_prices.ewm(span=12, adjust=False).mean()
            exp2 = close_prices.ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal_line = macd.ewm(span=9, adjust=False).mean()
            histogram = macd - signal_line
            
            result["indicators"]["MACD"] = {
                "macd_line": round(macd.iloc[-1], 2),
                "signal_line": round(signal_line.iloc[-1], 2),
                "histogram": round(histogram.iloc[-1], 2),
                "signal": "bullish" if histogram.iloc[-1] > 0 else "bearish"
            }
        
        # Calculate Bollinger Bands
        if "BBands" in indicators or "BollingerBands" in indicators:
            sma20 = close_prices.rolling(window=20).mean()
            std20 = close_prices.rolling(window=20).std()
            upper_band = sma20 + (std20 * 2)
            lower_band = sma20 - (std20 * 2)
            
            result["indicators"]["Bollinger_Bands"] = {
                "upper_band": round(upper_band.iloc[-1], 2),
                "middle_band": round(sma20.iloc[-1], 2),
                "lower_band": round(lower_band.iloc[-1], 2),
                "price_position": "above_upper" if current_price > upper_band.iloc[-1] else 
                                 "above_middle" if current_price > sma20.iloc[-1] else
                                 "below_middle" if current_price > lower_band.iloc[-1] else "below_lower"
            }
        
        # Overall signal (aggregate)
        signals = []
        if "SMA" in result["indicators"]:
            signals.append(1 if result["indicators"]["SMA"]["signal"] == "bullish" else -1)
        if "RSI" in result["indicators"]:
            signals.append(1 if result["indicators"]["RSI"]["status"] == "oversold" else 
                          -1 if result["indicators"]["RSI"]["status"] == "overbought" else 0)
        if "MACD" in result["indicators"]:
            signals.append(1 if result["indicators"]["MACD"]["signal"] == "bullish" else -1)
        
        avg_signal = sum(signals) / len(signals) if signals else 0
        result["overall_technical_signal"] = "bullish" if avg_signal > 0.3 else "bearish" if avg_signal < -0.3 else "neutral"
        result["confidence_score"] = round(abs(avg_signal) * 10, 1)
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error calculating technical indicators: {str(e)}"
        )


@mcp.tool()
def fetch_volume_analysis(
    stock_symbol: str,
    days: int = 50
) -> Dict[str, Any]:
    """
    Analyze volume trends and institutional interest.
    
    Args:
        stock_symbol: Stock symbol
        days: Analysis period (20, 50, 200)
    
    Returns:
        Volume metrics and trends
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock =  fetch_ticker_safe(ticker, timeout=10)
        hist =  fetch_history_safe(stock, period=f"{days}d")
        
        if hist.empty:
            return handle_error(
                "data_unavailable",
                stock_symbol,
                "Volume data not available"
            )
        
        volumes = hist['Volume']
        avg_volume_20d = volumes.tail(20).mean()
        avg_volume_50d = volumes.mean()
        current_volume = volumes.iloc[-1]
        
        result = {
            "stock_symbol": stock_symbol,
            "volume_metrics": {
                "volume_20d_avg": int(avg_volume_20d),
                "volume_50d_avg": int(avg_volume_50d),
                "current_volume": int(current_volume),
                "volume_current_vs_20d": round((current_volume / avg_volume_20d), 2),
                "volume_trend": "increasing" if current_volume > avg_volume_20d else "decreasing",
                "volume_quality": "high" if current_volume > avg_volume_20d * 1.5 else "normal"
            },
            "volume_signals": {
                "high_volume_breakout": current_volume > avg_volume_20d * 2,
                "volume_cluster": "above_average" if current_volume > avg_volume_20d else "below_average",
                "signal": "bullish" if current_volume > avg_volume_20d * 1.5 else "neutral"
            },
            "data_source": "Yahoo Finance"
        }
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error analyzing volume: {str(e)}"
        )


@mcp.tool()
def fetch_volatility_metrics(
    stock_symbol: str,
    period: str = "1y"
) -> Dict[str, Any]:
    """
    Calculate volatility and risk metrics.
    
    Args:
        stock_symbol: Stock symbol
        period: "3m", "1y"
    
    Returns:
        Volatility metrics including beta, drawdown, Sharpe ratio
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock =  fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        info =  fetch_info_safe(stock, timeout=10)
        
        period_days = 365 if period == "1y" else 90
        hist =  fetch_history_safe(stock, period=f"{period_days}d")
        
        if hist.empty:
            return handle_error(
                "data_unavailable",
                stock_symbol,
                "Insufficient data for volatility analysis"
            )
        
        # Calculate daily returns
        returns = hist['Close'].pct_change().dropna()
        
        # Volatility
        daily_vol = returns.std()
        annual_vol = daily_vol * np.sqrt(252)  # Annualized
        
        # Max drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        result = {
            "stock_symbol": stock_symbol,
            "volatility": {
                "std_dev_percent": round(daily_vol * 100, 2),
                "annualized_volatility": round(annual_vol, 3),
                "volatility_classification": "low" if annual_vol < 0.15 else "moderate" if annual_vol < 0.25 else "high"
            },
            "beta": {
                "beta_vs_nifty50": round(info.get("beta", 1.0), 2),
                "beta_interpretation": "less_volatile_than_market" if info.get("beta", 1.0) < 1 else "more_volatile_than_market"
            },
            "drawdown": {
                "max_drawdown_1y_percent": round(max_drawdown * 100, 2),
                "current_drawdown": round(drawdown.iloc[-1] * 100, 2)
            },
            "sharpe_ratio": {
                "sharpe_ratio_1y": round((returns.mean() * 252) / (daily_vol * np.sqrt(252)), 2),
                "risk_adjusted_return": "excellent" if (returns.mean() * 252) / (daily_vol * np.sqrt(252)) > 2 else "good"
            },
            "data_source": "Yahoo Finance"
        }
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error calculating volatility: {str(e)}"
        )


@mcp.tool()
def fetch_comparative_performance(
    stock_symbol: str,
    compare_with: List[str],
    period: str = "1y"
) -> Dict[str, Any]:
    """
    Compare stock performance with sector and market indices.
    
    Args:
        stock_symbol: Stock symbol
        compare_with: List of symbols/indices to compare (e.g., ["^NSEI", "TCS"])
        period: "1m", "3m", "6m", "1y"
    
    Returns:
        Comparative performance metrics
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock =  fetch_ticker_safe(ticker, timeout=10)
        
        period_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
        days = period_map.get(period, 365)
        
        stock_hist =  fetch_history_safe(stock, period=f"{days}d")
        
        if stock_hist.empty:
            return handle_error(
                "data_unavailable",
                stock_symbol,
                "Performance data not available"
            )
        
        # Calculate stock return
        stock_return = ((stock_hist['Close'].iloc[-1] - stock_hist['Close'].iloc[0]) / stock_hist['Close'].iloc[0]) * 100
        
        comparisons = {}
        for compare_symbol in compare_with:
            try:
                compare_ticker = compare_symbol if compare_symbol.startswith("^") else get_stock_ticker(compare_symbol)
                compare_stock = yf.Ticker(compare_ticker)
                compare_hist = compare_stock.history(period=f"{days}d")
                
                if not compare_hist.empty:
                    compare_return = ((compare_hist['Close'].iloc[-1] - compare_hist['Close'].iloc[0]) / compare_hist['Close'].iloc[0]) * 100
                    outperformance = stock_return - compare_return
                    
                    comparisons[compare_symbol] = {
                        "stock_return": round(stock_return, 2),
                        "benchmark_return": round(compare_return, 2),
                        "outperformance": round(outperformance, 2),
                        "ranking": "above_benchmark" if outperformance > 0 else "below_benchmark"
                    }
            except:
                continue
        
        return {
            "stock_symbol": stock_symbol,
            "period": period,
            "stock_return_percent": round(stock_return, 2),
            "comparisons": comparisons,
            "data_source": "Yahoo Finance"
        }
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error comparing performance: {str(e)}"
        )


@mcp.tool()
def fetch_institutional_holding_data(
    stock_symbol: str
) -> Dict[str, Any]:
    """
    Get FII/DII and mutual fund holding information.
    
    Args:
        stock_symbol: Stock symbol
    
    Returns:
        Institutional holding data
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock =  fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        info =  fetch_info_safe(stock, timeout=10)
        
        # Yahoo Finance provides institutional holders
        institutional = stock.institutional_holders
        
        result = {
            "stock_symbol": stock_symbol,
            "institutional_holding": {
                "total_institutional_percent": round(info.get("heldPercentInstitutions", 0) * 100, 2) if info.get("heldPercentInstitutions") else None,
                "total_insider_percent": round(info.get("heldPercentInsiders", 0) * 100, 2) if info.get("heldPercentInsiders") else None,
            },
            "major_holders": [],
            "data_source": "Yahoo Finance"
        }
        
        if not institutional.empty:
            for index, row in institutional.head(10).iterrows():
                result["major_holders"].append({
                    "holder": row.get("Holder", "Unknown"),
                    "shares": int(row.get("Shares", 0)),
                    "date_reported": row.get("Date Reported", "Unknown")
                })
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching institutional data: {str(e)}"
        )


@mcp.tool()
def fetch_liquidity_metrics(
    stock_symbol: str
) -> Dict[str, Any]:
    """
    Analyze trading liquidity and execution quality.
    
    Args:
        stock_symbol: Stock symbol
    
    Returns:
        Liquidity metrics
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock =  fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        info =  fetch_info_safe(stock, timeout=10)
        hist =  fetch_history_safe(stock, period="30d")
        
        if hist.empty:
            return handle_error(
                "data_unavailable",
                stock_symbol,
                "Liquidity data not available"
            )
        
        avg_volume = hist['Volume'].mean()
        avg_value = (hist['Volume'] * hist['Close']).mean()
        
        result = {
            "stock_symbol": stock_symbol,
            "liquidity": {
                "average_volume_daily": int(avg_volume),
                "average_value_cr": round(avg_value / 10000000, 2),
                "liquidity_classification": "high" if avg_volume > 1000000 else "medium" if avg_volume > 100000 else "low",
                "bid_ask_spread": info.get("bidAskSpread", "N/A")
            },
            "trading_quality": {
                "avg_price_range": round((hist['High'] - hist['Low']).mean(), 2),
                "execution_quality": "excellent" if avg_volume > 1000000 else "good"
            },
            "data_source": "Yahoo Finance"
        }
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error analyzing liquidity: {str(e)}"
        )


@mcp.tool()
def validate_technical_data(
    stock_symbol: str,
    date_range: str = "1y"
) -> Dict[str, Any]:
    """
    Verify data quality and completeness.
    
    Args:
        stock_symbol: Stock symbol
        date_range: Date range to verify
    
    Returns:
        Data quality metrics
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock =  fetch_ticker_safe(ticker, timeout=10)
        hist =  fetch_history_safe(stock, period=date_range)
        
        if hist.empty:
            return {
                "stock_symbol": stock_symbol,
                "data_completeness": 0,
                "data_quality": "no_data",
                "message": "No data available for validation"
            }
        
        # Check for missing data
        total_days = len(hist)
        non_null_days = hist['Close'].notna().sum()
        completeness = (non_null_days / total_days) * 100
        
        return {
            "stock_symbol": stock_symbol,
            "data_completeness": round(completeness, 2),
            "last_update": hist.index[-1].strftime("%Y-%m-%d %H:%M:%S"),
            "data_quality": "excellent" if completeness > 99 else "good" if completeness > 95 else "poor",
            "total_records": total_days,
            "issues": [] if completeness > 99 else ["Some data gaps detected"],
            "note": "Data is current and reliable" if completeness > 99 else "Data quality needs attention"
        }
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error validating data: {str(e)}"
        )


if __name__ == "__main__":
    mcp.run()

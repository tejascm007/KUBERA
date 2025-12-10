"""
MCP SERVER 5: VISUALIZATION SERVER
Purpose: Generate interactive charts and visualizations for stock analysis
Data Sources: Yahoo Finance data + Plotly/Matplotlib for charting
"""

from fastmcp import FastMCP
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
import base64
from io import BytesIO
import sys
import os
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.utils import fetch_ticker_safe, fetch_history_safe, fetch_info_safe, fetch_financials_safe
import uuid
from supabase import create_client, Client

from dotenv import load_dotenv
load_dotenv() 
# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_chart_to_supabase(html_content: str, stock_symbol: str, chart_type: str) -> str:
    """
    Upload chart HTML to Supabase Storage and return public URL
    
    Args:
        html_content: Chart HTML string
        stock_symbol: Stock symbol
        chart_type: Type of chart (e.g., "price_volume")
    
    Returns:
        Public URL of uploaded chart
    """
    try:
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chart_id = str(uuid.uuid4())[:8]
        filename = f"{stock_symbol}_{chart_type}_{timestamp}_{chart_id}.html"
        
        # Upload to Supabase Storage
        response = supabase.storage.from_("charts").upload(
            path=filename,
            file=html_content.encode('utf-8'),
            file_options={
                "content-type": "text/html",
                "cache-control": "3600"
            }
        )
        
        # Get public URL
        public_url = supabase.storage.from_("charts").get_public_url(filename)
        
        return public_url
    
    except Exception as e:
        print(f"Error uploading chart: {e}")
        return None
# Try to import plotting libraries
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("Warning: Plotly not available. Charts will return data only.")

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: Matplotlib not available.")

# Initialize FastMCP
mcp = FastMCP("VisualizationServer")

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
def generate_price_volume_chart(
    stock_symbol: str,
    period: str = "6m",
    chart_type: str = "line"
) -> Dict[str, Any]:
    """
    Generate price and volume chart.
    
    Args:
        stock_symbol: Stock symbol
        period: "1m", "3m", "6m", "1y", "3y"
        chart_type: "line", "area", or "bar"
    
    Returns:
        Chart data and HTML (if Plotly available)
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10) 
        # Map period
        period_map = {"1m": "1mo", "3m": "3mo", "6m": "6mo", "1y": "1y", "3y": "3y"}
        yf_period = period_map.get(period, "6mo")
        
        hist = fetch_history_safe(stock, period=yf_period)
        
        if hist.empty:
            return handle_error(
                "data_unavailable",
                stock_symbol,
                "No data available for charting"
            )
        
        result = {
            "stock_symbol": stock_symbol,
            "chart_type": "price_volume",
            "period": period,
            "data_points": len(hist),
            "chart_data": {
                "dates": [d.strftime("%Y-%m-%d") for d in hist.index],
                "close_prices": hist['Close'].tolist(),
                "volumes": hist['Volume'].tolist()
            }
        }
        
        if PLOTLY_AVAILABLE:
            # Create subplot with 2 rows
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=(f'{stock_symbol} - Price', 'Volume'),
                row_heights=[0.7, 0.3]
            )
            
            # Price chart
            if chart_type == "line":
                fig.add_trace(
                    go.Scatter(
                        x=hist.index,
                        y=hist['Close'],
                        name='Price',
                        line=dict(color='#1f77b4', width=2)
                    ),
                    row=1, col=1
                )
            elif chart_type == "area":
                fig.add_trace(
                    go.Scatter(
                        x=hist.index,
                        y=hist['Close'],
                        name='Price',
                        fill='tozeroy',
                        line=dict(color='#1f77b4', width=2)
                    ),
                    row=1, col=1
                )
            
            # Volume chart
            colors = ['red' if row['Close'] < row['Open'] else 'green' 
                     for idx, row in hist.iterrows()]
            
            fig.add_trace(
                go.Bar(
                    x=hist.index,
                    y=hist['Volume'],
                    name='Volume',
                    marker_color=colors
                ),
                row=2, col=1
            )
            
            # Update layout
            fig.update_layout(
                title=f'{stock_symbol} - Price & Volume Chart',
                xaxis2_title='Date',
                yaxis_title='Price (₹)',
                yaxis2_title='Volume',
                hovermode='x unified',
                height=600,
                showlegend=True,
                template='plotly_white'
            )
            
            # Convert to HTML
            chart_html = fig.to_html(include_plotlyjs='cdn')
            chart_url = upload_chart_to_supabase(chart_html, stock_symbol, "price_volume")

            if chart_url:
                result["chart_url"] = chart_url
                result["chart_available"] = True
                # Optional: Keep chart_html for backward compatibility or remove it
                # result["chart_html"] = chart_html  # Remove to reduce payload
            else:
                result["chart_url"] = None
                result["chart_available"] = False
                result["error"] = "Failed to upload chart to storage"
        else:
            result["chart_html"] = None
            result["chart_available"] = False
            result["note"] = "Plotly not available. Only data returned."
        
        result["data_source"] = "Yahoo Finance"
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error generating chart: {str(e)}"
        )


@mcp.tool()
def generate_candlestick_chart(
    stock_symbol: str,
    period: str = "3m",
    interval: str = "daily"
) -> Dict[str, Any]:
    """
    Generate candlestick chart.
    
    Args:
        stock_symbol: Stock symbol
        period: "1m", "3m", "6m", "1y"
        interval: "daily", "weekly"
    
    Returns:
        Candlestick chart data and HTML
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        
        # Map period and interval
        period_map = {"1m": "1mo", "3m": "3mo", "6m": "6mo", "1y": "1y"}
        interval_map = {"daily": "1d", "weekly": "1wk"}
        
        yf_period = period_map.get(period, "3mo")
        yf_interval = interval_map.get(interval, "1d")
        
        hist = fetch_history_safe(stock, period=yf_period, interval=yf_interval)
        
        if hist.empty:
            return handle_error(
                "data_unavailable",
                stock_symbol,
                "No data available for candlestick chart"
            )
        
        result = {
            "stock_symbol": stock_symbol,
            "chart_type": "candlestick",
            "period": period,
            "interval": interval,
            "data_points": len(hist),
            "chart_data": {
                "dates": [d.strftime("%Y-%m-%d") for d in hist.index],
                "open": hist['Open'].tolist(),
                "high": hist['High'].tolist(),
                "low": hist['Low'].tolist(),
                "close": hist['Close'].tolist(),
                "volume": hist['Volume'].tolist()
            }
        }
        
        if PLOTLY_AVAILABLE:
            # Create candlestick chart
            fig = go.Figure(data=[
                go.Candlestick(
                    x=hist.index,
                    open=hist['Open'],
                    high=hist['High'],
                    low=hist['Low'],
                    close=hist['Close'],
                    name='OHLC'
                )
            ])
            
            # Add moving averages
            ma20 = hist['Close'].rolling(window=20).mean()
            ma50 = hist['Close'].rolling(window=50).mean()
            
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=ma20,
                name='MA20',
                line=dict(color='orange', width=1)
            ))
            
            if len(hist) >= 50:
                fig.add_trace(go.Scatter(
                    x=hist.index,
                    y=ma50,
                    name='MA50',
                    line=dict(color='blue', width=1)
                ))
            
            fig.update_layout(
                title=f'{stock_symbol} - Candlestick Chart',
                xaxis_title='Date',
                yaxis_title='Price (₹)',
                xaxis_rangeslider_visible=False,
                height=600,
                template='plotly_white',
                hovermode='x unified'
            )
            
            chart_html = fig.to_html(include_plotlyjs='cdn')
            chart_url = upload_chart_to_supabase(chart_html, stock_symbol, "price_volume")

            if chart_url:
                result["chart_url"] = chart_url
                result["chart_available"] = True
                # Optional: Keep chart_html for backward compatibility or remove it
                # result["chart_html"] = chart_html  # Remove to reduce payload
            else:
                result["chart_url"] = None
                result["chart_available"] = False
                result["error"] = "Failed to upload chart to storage"
        else:
            result["chart_html"] = None
            result["chart_available"] = False
        
        result["data_source"] = "Yahoo Finance"
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error generating candlestick chart: {str(e)}"
        )


@mcp.tool()
def generate_technical_indicators_chart(
    stock_symbol: str,
    indicators: List[str],
    period: str = "6m"
) -> Dict[str, Any]:
    """
    Generate chart with technical indicators.
    
    Args:
        stock_symbol: Stock symbol
        indicators: List of indicators ["RSI", "MACD", "BBands"]
        period: "3m", "6m", "1y"
    
    Returns:
        Technical indicators chart
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        
        period_map = {"3m": "3mo", "6m": "6mo", "1y": "1y"}
        yf_period = period_map.get(period, "6mo")
        
        hist = fetch_history_safe(stock, period=yf_period)
        
        if hist.empty:
            return handle_error(
                "data_unavailable",
                stock_symbol,
                "No data available for technical chart"
            )
        
        close_prices = hist['Close']
        
        # Calculate indicators
        indicator_data = {}
        
        if "RSI" in indicators:
            # RSI calculation
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            indicator_data["RSI"] = rsi.tolist()
        
        if "MACD" in indicators:
            # MACD calculation
            exp1 = close_prices.ewm(span=12, adjust=False).mean()
            exp2 = close_prices.ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            indicator_data["MACD"] = macd.tolist()
            indicator_data["MACD_Signal"] = signal.tolist()
        
        if "BBands" in indicators or "BollingerBands" in indicators:
            # Bollinger Bands
            sma20 = close_prices.rolling(window=20).mean()
            std20 = close_prices.rolling(window=20).std()
            upper_band = sma20 + (std20 * 2)
            lower_band = sma20 - (std20 * 2)
            indicator_data["BB_Upper"] = upper_band.tolist()
            indicator_data["BB_Middle"] = sma20.tolist()
            indicator_data["BB_Lower"] = lower_band.tolist()
        
        result = {
            "stock_symbol": stock_symbol,
            "chart_type": "technical_indicators",
            "period": period,
            "indicators": indicators,
            "data_points": len(hist),
            "chart_data": {
                "dates": [d.strftime("%Y-%m-%d") for d in hist.index],
                "close_prices": close_prices.tolist(),
                "indicators": indicator_data
            }
        }
        
        if PLOTLY_AVAILABLE:
            # Determine number of subplots
            n_subplots = 1 + len([i for i in indicators if i in ["RSI", "MACD"]])
            
            fig = make_subplots(
                rows=n_subplots,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                row_heights=[0.5] + [0.25] * (n_subplots - 1)
            )
            
            # Price chart with Bollinger Bands
            fig.add_trace(
                go.Scatter(x=hist.index, y=close_prices, name='Price', line=dict(color='blue')),
                row=1, col=1
            )
            
            if "BB_Upper" in indicator_data:
                fig.add_trace(
                    go.Scatter(x=hist.index, y=indicator_data["BB_Upper"], name='BB Upper',
                              line=dict(color='gray', dash='dash'), opacity=0.5),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Scatter(x=hist.index, y=indicator_data["BB_Lower"], name='BB Lower',
                              line=dict(color='gray', dash='dash'), opacity=0.5, fill='tonexty'),
                    row=1, col=1
                )
            
            current_row = 2
            
            # RSI
            if "RSI" in indicator_data:
                fig.add_trace(
                    go.Scatter(x=hist.index, y=indicator_data["RSI"], name='RSI', line=dict(color='purple')),
                    row=current_row, col=1
                )
                fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=current_row, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=current_row, col=1)
                current_row += 1
            
            # MACD
            if "MACD" in indicator_data:
                fig.add_trace(
                    go.Scatter(x=hist.index, y=indicator_data["MACD"], name='MACD', line=dict(color='blue')),
                    row=current_row, col=1
                )
                fig.add_trace(
                    go.Scatter(x=hist.index, y=indicator_data["MACD_Signal"], name='Signal', line=dict(color='red')),
                    row=current_row, col=1
                )
                current_row += 1
            
            fig.update_layout(
                title=f'{stock_symbol} - Technical Indicators',
                height=600,
                template='plotly_white',
                hovermode='x unified',
                showlegend=True
            )
            
            chart_html = fig.to_html(include_plotlyjs='cdn')
            chart_url = upload_chart_to_supabase(chart_html, stock_symbol, "price_volume")

            if chart_url:
                result["chart_url"] = chart_url
                result["chart_available"] = True
                # Optional: Keep chart_html for backward compatibility or remove it
                # result["chart_html"] = chart_html  # Remove to reduce payload
            else:
                result["chart_url"] = None
                result["chart_available"] = False
                result["error"] = "Failed to upload chart to storage"
        else:
            result["chart_html"] = None
            result["chart_available"] = False
        
        result["data_source"] = "Yahoo Finance"
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error generating technical chart: {str(e)}"
        )


@mcp.tool()
def generate_fundamental_comparison_chart(
    stock_symbols: List[str],
    metrics: List[str]
) -> Dict[str, Any]:
    """
    Generate comparison chart for fundamental metrics across stocks.
    
    Args:
        stock_symbols: List of stock symbols to compare (2-5 stocks)
        metrics: List of metrics ["PE", "PB", "ROE", "Debt_to_Equity"]
    
    Returns:
        Comparison chart data and HTML
    """
    try:
        comparison_data = {}
        
        for symbol in stock_symbols[:5]:  # Limit to 5 stocks
            ticker = get_stock_ticker(symbol)
            stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
            info = fetch_info_safe(stock, timeout=10)
            
            stock_data = {}
            
            if "PE" in metrics:
                stock_data["PE Ratio"] = info.get("trailingPE", 0)
            if "PB" in metrics:
                stock_data["PB Ratio"] = info.get("priceToBook", 0)
            if "ROE" in metrics:
                stock_data["ROE (%)"] = info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else 0
            if "Debt_to_Equity" in metrics:
                stock_data["Debt/Equity"] = info.get("debtToEquity", 0)
            if "Dividend_Yield" in metrics:
                stock_data["Div Yield (%)"] = info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0
            
            comparison_data[symbol] = stock_data
        
        result = {
            "chart_type": "fundamental_comparison",
            "stock_symbols": stock_symbols,
            "metrics": metrics,
            "comparison_data": comparison_data
        }
        
        if PLOTLY_AVAILABLE:
            # Create grouped bar chart
            df = pd.DataFrame(comparison_data).T
            
            fig = go.Figure()
            
            for metric in df.columns:
                fig.add_trace(go.Bar(
                    name=metric,
                    x=df.index,
                    y=df[metric],
                    text=df[metric].round(2),
                    textposition='auto'
                ))
            
            fig.update_layout(
                title='Fundamental Metrics Comparison',
                xaxis_title='Stock',
                yaxis_title='Value',
                barmode='group',
                height=500,
                template='plotly_white',
                showlegend=True
            )
            
            chart_html = fig.to_html(include_plotlyjs='cdn')
            chart_url = upload_chart_to_supabase(chart_html, stock_symbol, "price_volume")

            if chart_url:
                result["chart_url"] = chart_url
                result["chart_available"] = True
                # Optional: Keep chart_html for backward compatibility or remove it
                # result["chart_html"] = chart_html  # Remove to reduce payload
            else:
                result["chart_url"] = None
                result["chart_available"] = False
                result["error"] = "Failed to upload chart to storage"
        else:
            result["chart_html"] = None
            result["chart_available"] = False
        
        result["data_source"] = "Yahoo Finance"
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            ",".join(stock_symbols),
            f"Error generating comparison chart: {str(e)}"
        )


@mcp.tool()
def generate_financial_trend_chart(
    stock_symbol: str,
    metric: str,
    years: int = 5
) -> Dict[str, Any]:
    """
    Generate trend chart for financial metrics over time.
    
    Args:
        stock_symbol: Stock symbol
        metric: "Revenue", "Profit", "EPS", "Dividend"
        years: Number of years (3, 5, 10)
    
    Returns:
        Financial trend chart
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        
        result = {
            "stock_symbol": stock_symbol,
            "chart_type": "financial_trend",
            "metric": metric,
            "years": years,
            "trend_data": {}
        }
        
        if metric == "Revenue":
            financials = fetch_financials_safe(stock)
            if not financials.empty:
                revenue_data = []
                for col in financials.columns[:years]:
                    if "Total Revenue" in financials.index:
                        revenue = financials.loc["Total Revenue", col]
                        revenue_data.append({
                            "year": col.year,
                            "value": round(revenue / 10000000, 2)  # in Crores
                        })
                result["trend_data"] = revenue_data
        
        elif metric == "Profit":
            financials = fetch_financials_safe(stock)
            if not financials.empty:
                profit_data = []
                for col in financials.columns[:years]:
                    if "Net Income" in financials.index:
                        profit = financials.loc["Net Income", col]
                        profit_data.append({
                            "year": col.year,
                            "value": round(profit / 10000000, 2)  # in Crores
                        })
                result["trend_data"] = profit_data
        
        elif metric == "EPS":
            earnings = stock.earnings
            if not earnings.empty:
                eps_data = []
                for index, row in earnings.tail(years).iterrows():
                    eps_data.append({
                        "year": index,
                        "value": round(row.get("Earnings", 0), 2)
                    })
                result["trend_data"] = eps_data
        
        if PLOTLY_AVAILABLE and result["trend_data"]:
            df = pd.DataFrame(result["trend_data"])
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=df["year"],
                y=df["value"],
                mode='lines+markers',
                name=metric,
                line=dict(color='blue', width=3),
                marker=dict(size=10)
            ))
            
            fig.update_layout(
                title=f'{stock_symbol} - {metric} Trend',
                xaxis_title='Year',
                yaxis_title=f'{metric} (₹ Crores)' if metric in ["Revenue", "Profit"] else metric,
                height=500,
                template='plotly_white',
                hovermode='x unified'
            )
            
            chart_html = fig.to_html(include_plotlyjs='cdn')
            chart_url = upload_chart_to_supabase(chart_html, stock_symbol, "price_volume")

            if chart_url:
                result["chart_url"] = chart_url
                result["chart_available"] = True
                # Optional: Keep chart_html for backward compatibility or remove it
                # result["chart_html"] = chart_html  # Remove to reduce payload
            else:
                result["chart_url"] = None
                result["chart_available"] = False
                result["error"] = "Failed to upload chart to storage"
        else:
            result["chart_html"] = None
            result["chart_available"] = False
        
        result["data_source"] = "Yahoo Finance"
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error generating trend chart: {str(e)}"
        )


@mcp.tool()
def generate_performance_vs_benchmark_chart(
    stock_symbol: str,
    benchmark: str = "^NSEI",
    period: str = "1y"
) -> Dict[str, Any]:
    """
    Generate performance comparison chart vs benchmark.
    
    Args:
        stock_symbol: Stock symbol
        benchmark: Benchmark symbol (default: NIFTY50 = "^NSEI")
        period: "6m", "1y", "3y", "5y"
    
    Returns:
        Performance comparison chart
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        benchmark_ticker = yf.Ticker(benchmark)
        
        period_map = {"6m": "6mo", "1y": "1y", "3y": "3y", "5y": "5y"}
        yf_period = period_map.get(period, "1y")
        
        stock_hist = fetch_history_safe(stock, period=yf_period)
        benchmark_hist = benchmark_ticker.history(period=yf_period)
        
        if stock_hist.empty or benchmark_hist.empty:
            return handle_error(
                "data_unavailable",
                stock_symbol,
                "Insufficient data for comparison"
            )
        
        # Normalize to 100 (percentage change from start)
        stock_normalized = (stock_hist['Close'] / stock_hist['Close'].iloc[0]) * 100
        benchmark_normalized = (benchmark_hist['Close'] / benchmark_hist['Close'].iloc[0]) * 100
        
        result = {
            "stock_symbol": stock_symbol,
            "benchmark": benchmark,
            "chart_type": "performance_comparison",
            "period": period,
            "chart_data": {
                "dates": [d.strftime("%Y-%m-%d") for d in stock_hist.index],
                "stock_performance": stock_normalized.tolist(),
                "benchmark_performance": benchmark_normalized.tolist()
            },
            "performance_summary": {
                "stock_return": round(stock_normalized.iloc[-1] - 100, 2),
                "benchmark_return": round(benchmark_normalized.iloc[-1] - 100, 2),
                "outperformance": round((stock_normalized.iloc[-1] - 100) - (benchmark_normalized.iloc[-1] - 100), 2)
            }
        }
        
        if PLOTLY_AVAILABLE:
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=stock_hist.index,
                y=stock_normalized,
                name=stock_symbol,
                line=dict(color='blue', width=2)
            ))
            
            fig.add_trace(go.Scatter(
                x=benchmark_hist.index,
                y=benchmark_normalized,
                name='NIFTY 50' if benchmark == "^NSEI" else benchmark,
                line=dict(color='red', width=2, dash='dash')
            ))
            
            fig.update_layout(
                title=f'{stock_symbol} vs Benchmark Performance (Indexed to 100)',
                xaxis_title='Date',
                yaxis_title='Performance (Base = 100)',
                height=500,
                template='plotly_white',
                hovermode='x unified',
                showlegend=True
            )
            
            chart_html = fig.to_html(include_plotlyjs='cdn')
            chart_url = upload_chart_to_supabase(chart_html, stock_symbol, "price_volume")

            if chart_url:
                result["chart_url"] = chart_url
                result["chart_available"] = True
                # Optional: Keep chart_html for backward compatibility or remove it
                # result["chart_html"] = chart_html  # Remove to reduce payload
            else:
                result["chart_url"] = None
                result["chart_available"] = False
                result["error"] = "Failed to upload chart to storage"
        else:
            result["chart_html"] = None
            result["chart_available"] = False
        
        result["data_source"] = "Yahoo Finance"
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error generating comparison chart: {str(e)}"
        )


@mcp.tool()
def generate_valuation_heatmap(
    stock_symbols: List[str]
) -> Dict[str, Any]:
    """
    Generate valuation heatmap for multiple stocks.
    
    Args:
        stock_symbols: List of stock symbols (5-20 stocks)
    
    Returns:
        Valuation heatmap chart
    """
    try:
        valuation_data = []
        
        for symbol in stock_symbols[:20]:  # Limit to 20 stocks
            ticker = get_stock_ticker(symbol)
            stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
            info = fetch_info_safe(stock, timeout=10)
            
            valuation_data.append({
                "Stock": symbol,
                "PE": info.get("trailingPE", 0),
                "PB": info.get("priceToBook", 0),
                "PS": info.get("priceToSalesTrailing12Months", 0),
                "Div Yield": info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0
            })
        
        df = pd.DataFrame(valuation_data).set_index("Stock")
        
        result = {
            "chart_type": "valuation_heatmap",
            "stock_symbols": stock_symbols,
            "valuation_data": df.to_dict('index')
        }
        
        if PLOTLY_AVAILABLE:
            fig = go.Figure(data=go.Heatmap(
                z=df.values.T,
                x=df.index,
                y=df.columns,
                colorscale='RdYlGn_r',
                text=df.values.T,
                texttemplate='%{text:.2f}',
                textfont={"size": 10}
            ))
            
            fig.update_layout(
                title='Valuation Metrics Heatmap',
                xaxis_title='Stock',
                yaxis_title='Metric',
                height=400,
                template='plotly_white'
            )
            
            chart_html = fig.to_html(include_plotlyjs='cdn')
            chart_url = upload_chart_to_supabase(chart_html, stock_symbol, "price_volume")

            if chart_url:
                result["chart_url"] = chart_url
                result["chart_available"] = True
                # Optional: Keep chart_html for backward compatibility or remove it
                # result["chart_html"] = chart_html  # Remove to reduce payload
            else:
                result["chart_url"] = None
                result["chart_available"] = False
                result["error"] = "Failed to upload chart to storage"
        else:
            result["chart_html"] = None
            result["chart_available"] = False
        
        result["data_source"] = "Yahoo Finance"
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            ",".join(stock_symbols),
            f"Error generating heatmap: {str(e)}"
        )


@mcp.tool()
def generate_portfolio_composition_chart(
    portfolio: List[Dict[str, Any]],
    chart_type: str = "pie"
) -> Dict[str, Any]:
    """
    Generate portfolio composition chart.
    
    Args:
        portfolio: List of portfolio items with {"symbol": "INFY", "value": 100000, ...}
        chart_type: "pie" or "treemap"
    
    Returns:
        Portfolio composition chart
    """
    try:
        if not portfolio:
            return handle_error(
                "invalid_input",
                "portfolio",
                "Empty portfolio provided"
            )
        
        result = {
            "chart_type": f"portfolio_composition_{chart_type}",
            "total_value": sum(item.get("value", 0) for item in portfolio),
            "stock_count": len(portfolio),
            "composition_data": portfolio
        }
        
        if PLOTLY_AVAILABLE:
            symbols = [item["symbol"] for item in portfolio]
            values = [item.get("value", 0) for item in portfolio]
            
            if chart_type == "pie":
                fig = go.Figure(data=[go.Pie(
                    labels=symbols,
                    values=values,
                    hole=0.3,
                    textinfo='label+percent',
                    textposition='auto'
                )])
                
                fig.update_layout(
                    title='Portfolio Composition',
                    height=500,
                    template='plotly_white'
                )
            
            elif chart_type == "treemap":
                fig = go.Figure(go.Treemap(
                    labels=symbols,
                    parents=["Portfolio"] * len(symbols),
                    values=values,
                    textinfo='label+value+percent parent',
                    marker=dict(colorscale='Viridis')
                ))
                
                fig.update_layout(
                    title='Portfolio Composition (Treemap)',
                    height=500
                )
            
            chart_html = fig.to_html(include_plotlyjs='cdn')
            chart_url = upload_chart_to_supabase(chart_html, stock_symbol, "price_volume")

            if chart_url:
                result["chart_url"] = chart_url
                result["chart_available"] = True
                # Optional: Keep chart_html for backward compatibility or remove it
                # result["chart_html"] = chart_html  # Remove to reduce payload
            else:
                result["chart_url"] = None
                result["chart_available"] = False
                result["error"] = "Failed to upload chart to storage"
        else:
            result["chart_html"] = None
            result["chart_available"] = False
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            "portfolio",
            f"Error generating portfolio chart: {str(e)}"
        )


@mcp.tool()
def generate_dividend_timeline_chart(
    stock_symbol: str,
    years: int = 5
) -> Dict[str, Any]:
    """
    Generate dividend payment timeline chart.
    
    Args:
        stock_symbol: Stock symbol
        years: Number of years
    
    Returns:
        Dividend timeline chart
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        
        dividends = stock.dividends
        
        if dividends.empty:
            return {
                "stock_symbol": stock_symbol,
                "message": "No dividend history available",
                "chart_available": False
            }
        
        cutoff_date = datetime.now() - timedelta(days=years*365)
        recent_dividends = dividends[dividends.index >= cutoff_date]
        
        result = {
            "stock_symbol": stock_symbol,
            "chart_type": "dividend_timeline",
            "years": years,
            "dividend_data": {
                "dates": [d.strftime("%Y-%m-%d") for d in recent_dividends.index],
                "amounts": recent_dividends.tolist()
            }
        }
        
        if PLOTLY_AVAILABLE:
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=recent_dividends.index,
                y=recent_dividends.values,
                name='Dividend',
                marker_color='green'
            ))
            
            fig.update_layout(
                title=f'{stock_symbol} - Dividend History',
                xaxis_title='Date',
                yaxis_title='Dividend per Share (₹)',
                height=500,
                template='plotly_white',
                showlegend=False
            )
            
            chart_html = fig.to_html(include_plotlyjs='cdn')
            chart_url = upload_chart_to_supabase(chart_html, stock_symbol, "price_volume")

            if chart_url:
                result["chart_url"] = chart_url
                result["chart_available"] = True
                # Optional: Keep chart_html for backward compatibility or remove it
                # result["chart_html"] = chart_html  # Remove to reduce payload
            else:
                result["chart_url"] = None
                result["chart_available"] = False
                result["error"] = "Failed to upload chart to storage"
        else:
            result["chart_html"] = None
            result["chart_available"] = False
        
        result["data_source"] = "Yahoo Finance"
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error generating dividend chart: {str(e)}"
        )


@mcp.tool()
def generate_risk_return_scatter(
    stock_symbols: List[str],
    period: str = "1y"
) -> Dict[str, Any]:
    """
    Generate risk-return scatter plot.
    
    Args:
        stock_symbols: List of stock symbols
        period: "1y", "3y", "5y"
    
    Returns:
        Risk-return scatter plot
    """
    try:
        scatter_data = []
        
        period_map = {"1y": "1y", "3y": "3y", "5y": "5y"}
        yf_period = period_map.get(period, "1y")
        
        for symbol in stock_symbols[:20]:  # Limit to 20 stocks
            try:
                ticker = get_stock_ticker(symbol)
                stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
                info = fetch_info_safe(stock, timeout=10)
                hist = fetch_history_safe(stock, period=yf_period)
                
                if not hist.empty:
                    returns = hist['Close'].pct_change().dropna()
                    
                    annual_return = ((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100
                    annual_volatility = returns.std() * np.sqrt(252) * 100  # Annualized volatility
                    
                    scatter_data.append({
                        "symbol": symbol,
                        "return": round(annual_return, 2),
                        "risk": round(annual_volatility, 2)
                    })
            except:
                continue
        
        result = {
            "chart_type": "risk_return_scatter",
            "period": period,
            "stock_count": len(scatter_data),
            "scatter_data": scatter_data
        }
        
        if PLOTLY_AVAILABLE and scatter_data:
            df = pd.DataFrame(scatter_data)
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=df["risk"],
                y=df["return"],
                mode='markers+text',
                text=df["symbol"],
                textposition="top center",
                marker=dict(
                    size=12,
                    color=df["return"],
                    colorscale='RdYlGn',
                    showscale=True,
                    colorbar=dict(title="Return (%)")
                )
            ))
            
            fig.update_layout(
                title='Risk-Return Analysis',
                xaxis_title='Risk (Volatility %)',
                yaxis_title='Return (%)',
                height=600,
                template='plotly_white',
                hovermode='closest'
            )
            
            chart_html = fig.to_html(include_plotlyjs='cdn')
            chart_url = upload_chart_to_supabase(chart_html, stock_symbol, "price_volume")

            if chart_url:
                result["chart_url"] = chart_url
                result["chart_available"] = True
                # Optional: Keep chart_html for backward compatibility or remove it
                # result["chart_html"] = chart_html  # Remove to reduce payload
            else:
                result["chart_url"] = None
                result["chart_available"] = False
                result["error"] = "Failed to upload chart to storage"
        else:
            result["chart_html"] = None
            result["chart_available"] = False
        
        result["data_source"] = "Yahoo Finance"
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            ",".join(stock_symbols),
            f"Error generating scatter plot: {str(e)}"
        )


@mcp.tool()
def validate_chart_data(
    stock_symbol: str,
    data_type: str = "price"
) -> Dict[str, Any]:
    """
    Validate data availability for charting.
    
    Args:
        stock_symbol: Stock symbol
        data_type: "price", "volume", "fundamentals"
    
    Returns:
        Data validation result
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)        
        result = {
            "stock_symbol": stock_symbol,
            "data_type": data_type,
            "validation_status": "valid",
            "available_periods": [],
            "data_quality": "good"
        }
        
        if data_type == "price":
            hist = fetch_history_safe(stock, period="1y")
            if not hist.empty:
                result["available_periods"] = ["1m", "3m", "6m", "1y", "3y", "5y"]
                result["data_points"] = len(hist)
                result["last_update"] = hist.index[-1].strftime("%Y-%m-%d")
            else:
                result["validation_status"] = "no_data"
                result["data_quality"] = "unavailable"
        
        elif data_type == "fundamentals":
            info = fetch_info_safe(stock)
            if info and 'symbol' in info:
                result["available_data"] = list(info.keys())[:20]
            else:
                result["validation_status"] = "limited_data"
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error validating data: {str(e)}"
        )


if __name__ == "__main__":
    mcp.run()

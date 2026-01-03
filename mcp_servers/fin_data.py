"""
MCP SERVER 1: FINANCIAL DATA SERVER
Purpose: Fetch fundamental financial metrics for Indian stocks (NSE/BSE)
Data Sources: Yahoo Finance, NSE, BSE, Finnhub, Alpha Vantage
"""

from fastmcp import FastMCP
import yfinance as yf
import requests
from datetime import datetime, timedelta
import json
from typing import Optional, List, Dict, Any
import sys
import os
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.utils import fetch_ticker_safe, fetch_history_safe, fetch_info_safe, fetch_financials_safe

# Load environment variables from .env file (required for MCP subprocess)
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Initialize FastMCP
mcp = FastMCP("FinancialDataServer")

# API Keys (store in environment variables)
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")

# Constants
NSE_SUFFIX = ".NS"
BSE_SUFFIX = ".BO"

def get_stock_ticker(symbol: str, exchange: str = "NSE") -> str:
    """Convert Indian stock symbol to Yahoo Finance ticker format."""
    symbol = symbol.upper().strip()
    if exchange.upper() == "NSE":
        return f"{symbol}{NSE_SUFFIX}" if not symbol.endswith(NSE_SUFFIX) else symbol
    elif exchange.upper() == "BSE":
        return f"{symbol}{BSE_SUFFIX}" if not symbol.endswith(BSE_SUFFIX) else symbol
    return symbol

def format_inr(amount: float) -> str:
    """Format amount in INR with proper notation."""
    if amount >= 10000000:  # 1 Crore
        return f"₹{amount/10000000:.2f} Cr"
    elif amount >= 100000:  # 1 Lakh
        return f"₹{amount/100000:.2f} L"
    else:
        return f"₹{amount:,.2f}"

def handle_error(error_type: str, symbol: str, message: str, suggestions: List[str] = None) -> Dict:
    """Standardized error response."""
    return {
        "status": "error",
        "error_type": error_type,
        "stock_symbol": symbol,
        "message": message,
        "suggestions": suggestions or [],
        "timestamp": datetime.utcnow().isoformat()
    }


@mcp.tool()
def fetch_company_fundamentals(
    stock_symbol: str,
    metrics: Optional[List[str]] = None,
    period: str = "latest"
) -> Dict[str, Any]:
    """
    Get core fundamental metrics for an Indian stock.
    
    Args:
        stock_symbol: Stock symbol (e.g., "INFY", "TCS", "RELIANCE")
        metrics: Optional list of specific metrics to fetch (if empty, returns all)
        period: "latest", "quarterly", or "annual" (default: "latest")
    
    Returns:
        Dict containing valuation, profitability, leverage, growth, and cash flow metrics
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        info = fetch_info_safe(stock, timeout=10)
        
        if not info or 'symbol' not in info:
            return handle_error(
                "stock_not_found",
                stock_symbol,
                f"Stock {stock_symbol} not found in NSE/BSE",
                ["Check symbol spelling", "Verify it's an Indian stock", "Try BSE code"]
            )
        
        # Extract fundamental data
        result = {
            "stock_symbol": stock_symbol,
            "company_name": info.get("longName", "N/A"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap_cr": round(info.get("marketCap", 0) / 10000000, 2) if info.get("marketCap") else None,
            
            "valuation": {
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "peg_ratio": info.get("pegRatio"),
                "pb_ratio": info.get("priceToBook"),
                "price_to_sales": info.get("priceToSalesTrailing12Months"),
                "ev_to_ebitda": info.get("enterpriseToEbitda"),
                "dividend_yield": info.get("dividendYield", 0) * 100 if info.get("dividendYield") else None
            },
            
            "profitability": {
                "roe": info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else None,
                "roa": info.get("returnOnAssets", 0) * 100 if info.get("returnOnAssets") else None,
                "operating_margin": info.get("operatingMargins", 0) * 100 if info.get("operatingMargins") else None,
                "net_profit_margin": info.get("profitMargins", 0) * 100 if info.get("profitMargins") else None,
                "gross_margin": info.get("grossMargins", 0) * 100 if info.get("grossMargins") else None
            },
            
            "leverage": {
                "debt_to_equity": info.get("debtToEquity"),
                "current_ratio": info.get("currentRatio"),
                "quick_ratio": info.get("quickRatio"),
                "total_debt_cr": round(info.get("totalDebt", 0) / 10000000, 2) if info.get("totalDebt") else None,
                "total_cash_cr": round(info.get("totalCash", 0) / 10000000, 2) if info.get("totalCash") else None
            },
            
            "growth": {
                "revenue_growth_yoy": info.get("revenueGrowth", 0) * 100 if info.get("revenueGrowth") else None,
                "earnings_growth_yoy": info.get("earningsGrowth", 0) * 100 if info.get("earningsGrowth") else None,
                "earnings_quarterly_growth": info.get("earningsQuarterlyGrowth", 0) * 100 if info.get("earningsQuarterlyGrowth") else None
            },
            
            "cash_flow": {
                "operating_cash_flow_cr": round(info.get("operatingCashflow", 0) / 10000000, 2) if info.get("operatingCashflow") else None,
                "free_cash_flow_cr": round(info.get("freeCashflow", 0) / 10000000, 2) if info.get("freeCashflow") else None,
                "fcf_yield": None  # Calculate if needed
            },
            
            "data_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "data_source": "Yahoo Finance API",
            "currency": "INR"
        }
        
        # Filter by requested metrics if specified
        if metrics and len(metrics) > 0:
            filtered_result = {"stock_symbol": stock_symbol, "company_name": result["company_name"]}
            for metric in metrics:
                if metric in result:
                    filtered_result[metric] = result[metric]
            return filtered_result
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching fundamentals: {str(e)}",
            ["Check internet connection", "Verify API access", "Try again later"]
        )


@mcp.tool()
def fetch_historical_financials(
    stock_symbol: str,
    years: int = 5,
    metric_category: str = "revenue"
) -> Dict[str, Any]:
    """
    Get historical financial data for trend analysis.
    
    Args:
        stock_symbol: Stock symbol
        years: Number of years (1, 3, 5, or 10)
        metric_category: "revenue", "profit", "cashflow", or "all"
    
    Returns:
        Historical financial data with CAGR and trends
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)
        
        # Get financial statements
        financials = fetch_financials_safe(stock)
        
        if financials.empty:
            return handle_error(
                "data_unavailable",
                stock_symbol,
                "Historical financial data not available",
                ["Check if stock is newly listed", "Try a different period"]
            )
        
        # Extract yearly data (limit to requested years)
        data = []
        for col in financials.columns[:years]:
            year_data = {
                "fiscal_year": col.year,
                "fy_end_date": col.strftime("%Y-%m-%d")
            }
            
            if metric_category in ["revenue", "all"]:
                revenue = financials.loc["Total Revenue", col] if "Total Revenue" in financials.index else None
                year_data["revenue_cr"] = round(revenue / 10000000, 2) if revenue else None
            
            if metric_category in ["profit", "all"]:
                profit = financials.loc["Net Income", col] if "Net Income" in financials.index else None
                year_data["net_profit_cr"] = round(profit / 10000000, 2) if profit else None
            
            data.append(year_data)
        
        # Calculate CAGR if we have enough data
        cagr = None
        if len(data) >= 2 and metric_category == "revenue" and data[0].get("revenue_cr") and data[-1].get("revenue_cr"):
            start_value = data[-1]["revenue_cr"]
            end_value = data[0]["revenue_cr"]
            num_years = len(data) - 1
            cagr = round(((end_value / start_value) ** (1 / num_years) - 1) * 100, 2)
        
        return {
            "stock_symbol": stock_symbol,
            "metric_category": metric_category,
            "years": years,
            "data": data,
            "cagr": cagr,
            "trend": "upward" if cagr and cagr > 0 else "downward" if cagr else "insufficient_data",
            "data_source": "Yahoo Finance / Company Filings",
            "currency": "INR"
        }
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching historical financials: {str(e)}"
        )


@mcp.tool()
def fetch_balance_sheet_data(
    stock_symbol: str,
    quarters: int = 1,
    date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get detailed balance sheet components.
    
    Args:
        stock_symbol: Stock symbol
        quarters: Number of quarters (1, 2, 4, 8)
        date: Optional specific date "YYYY-MM-DD"
    
    Returns:
        Balance sheet data with assets, liabilities, equity
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)
        
        balance_sheet = stock.balance_sheet
        
        if balance_sheet.empty:
            return handle_error(
                "data_unavailable",
                stock_symbol,
                "Balance sheet data not available"
            )
        
        # Get latest balance sheet
        latest = balance_sheet.columns[0]
        bs = balance_sheet[latest]
        
        result = {
            "stock_symbol": stock_symbol,
            "report_date": latest.strftime("%Y-%m-%d"),
            
            "assets": {
                "total_assets_cr": round(bs.get("Total Assets", 0) / 10000000, 2),
                "current_assets_cr": round(bs.get("Current Assets", 0) / 10000000, 2),
                "cash_cr": round(bs.get("Cash", 0) / 10000000, 2),
                "receivables_cr": round(bs.get("Receivables", 0) / 10000000, 2),
                "inventory_cr": round(bs.get("Inventory", 0) / 10000000, 2),
                "non_current_assets_cr": round(bs.get("Total Non Current Assets", 0) / 10000000, 2)
            },
            
            "liabilities": {
                "total_liabilities_cr": round(bs.get("Total Liabilities Net Minority Interest", 0) / 10000000, 2),
                "current_liabilities_cr": round(bs.get("Current Liabilities", 0) / 10000000, 2),
                "total_debt_cr": round(bs.get("Total Debt", 0) / 10000000, 2),
                "accounts_payable_cr": round(bs.get("Accounts Payable", 0) / 10000000, 2)
            },
            
            "equity": {
                "total_equity_cr": round(bs.get("Stockholders Equity", 0) / 10000000, 2),
                "retained_earnings_cr": round(bs.get("Retained Earnings", 0) / 10000000, 2)
            },
            
            "working_capital": {
                "working_capital_cr": round((bs.get("Current Assets", 0) - bs.get("Current Liabilities", 0)) / 10000000, 2)
            },
            
            "data_source": "Yahoo Finance",
            "currency": "INR"
        }
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching balance sheet: {str(e)}"
        )


@mcp.tool()
def fetch_cash_flow_data(
    stock_symbol: str,
    periods: int = 1
) -> Dict[str, Any]:
    """
    Get cash flow statement details.
    
    Args:
        stock_symbol: Stock symbol
        periods: Number of periods (quarters/years)
    
    Returns:
        Cash flow data with OCF, ICF, FCF
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)
        
        cashflow = stock.cashflow
        
        if cashflow.empty:
            return handle_error(
                "data_unavailable",
                stock_symbol,
                "Cash flow data not available"
            )
        
        latest = cashflow.columns[0]
        cf = cashflow[latest]
        
        operating_cf = cf.get("Operating Cash Flow", 0)
        capex = abs(cf.get("Capital Expenditure", 0))
        free_cash_flow = operating_cf - capex
        
        result = {
            "stock_symbol": stock_symbol,
            "report_date": latest.strftime("%Y-%m-%d"),
            
            "operating_cash_flow": {
                "ocf_cr": round(operating_cf / 10000000, 2),
                "depreciation_cr": round(cf.get("Depreciation", 0) / 10000000, 2)
            },
            
            "investing_cash_flow": {
                "capex_cr": round(capex / 10000000, 2),
                "icf_cr": round(cf.get("Investing Cash Flow", 0) / 10000000, 2)
            },
            
            "financing_cash_flow": {
                "fcf_cr": round(cf.get("Financing Cash Flow", 0) / 10000000, 2),
                "dividends_paid_cr": round(abs(cf.get("Cash Dividends Paid", 0)) / 10000000, 2)
            },
            
            "free_cash_flow": {
                "fcf_cr": round(free_cash_flow / 10000000, 2),
                "fcf_quality": "high" if free_cash_flow > 0 else "negative"
            },
            
            "data_source": "Yahoo Finance",
            "currency": "INR"
        }
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching cash flow: {str(e)}"
        )


@mcp.tool()
def fetch_dividend_history(
    stock_symbol: str,
    years: int = 5
) -> Dict[str, Any]:
    """
    Get historical dividend data and sustainability metrics.
    
    Args:
        stock_symbol: Stock symbol
        years: Historical years to fetch (1-10)
    
    Returns:
        Dividend history with yield, payout ratio, CAGR
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)
        
        dividends = stock.dividends
        info = fetch_info_safe(stock)

        
        if dividends.empty:
            return {
                "stock_symbol": stock_symbol,
                "message": "No dividend history available",
                "current_yield": 0,
                "dividend_status": "non_dividend_paying"
            }
        
        # Get dividends for requested years
        cutoff_date = datetime.now() - timedelta(days=years*365)
        recent_dividends = dividends[dividends.index >= cutoff_date]
        
        dividend_data = []
        for date, amount in recent_dividends.items():
            dividend_data.append({
                "payment_date": date.strftime("%Y-%m-%d"),
                "dividend_per_share": round(amount, 2)
            })
        
        result = {
            "stock_symbol": stock_symbol,
            "dividend_data": dividend_data[-10:],  # Last 10 payments
            "current_yield": round(info.get("dividendYield", 0) * 100, 2) if info.get("dividendYield") else 0,
            "payout_ratio": round(info.get("payoutRatio", 0) * 100, 2) if info.get("payoutRatio") else None,
            "dividend_sustainability": "high" if info.get("payoutRatio", 0) < 0.6 else "moderate",
            "total_dividends_in_period": len(dividend_data),
            "data_source": "Yahoo Finance",
            "currency": "INR"
        }
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching dividend history: {str(e)}"
        )


@mcp.tool()
def fetch_eps_analysis(
    stock_symbol: str,
    years: int = 5
) -> Dict[str, Any]:
    """
    Get Earnings Per Share data and trends.
    
    Args:
        stock_symbol: Stock symbol
        years: Historical years
    
    Returns:
        EPS data with growth rates and consistency
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        info = fetch_info_safe(stock, timeout=10)
        
        # Get historical EPS from financials
        earnings = stock.earnings
        
        if earnings.empty:
            return handle_error(
                "data_unavailable",
                stock_symbol,
                "EPS data not available"
            )
        
        eps_data = []
        for index, row in earnings.iterrows():
            eps_data.append({
                "fiscal_year": index,
                "eps": round(row.get("Earnings", 0), 2)
            })
        
        # Calculate growth if we have enough data
        eps_growth_3y = None
        if len(eps_data) >= 3:
            start_eps = eps_data[-3]["eps"]
            end_eps = eps_data[-1]["eps"]
            if start_eps > 0:
                eps_growth_3y = round(((end_eps / start_eps) ** (1/2) - 1) * 100, 2)
        
        result = {
            "stock_symbol": stock_symbol,
            "eps_data": eps_data[-years:],
            "current_eps": round(info.get("trailingEps", 0), 2),
            "forward_eps": round(info.get("forwardEps", 0), 2),
            "eps_growth_3y": eps_growth_3y,
            "eps_consistency_score": 8.5 if eps_growth_3y and eps_growth_3y > 0 else 5.0,
            "data_source": "Yahoo Finance",
            "currency": "INR"
        }
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching EPS analysis: {str(e)}"
        )


@mcp.tool()
def validate_stock_symbol(
    stock_symbol: str,
    exchange: str = "NSE"
) -> Dict[str, Any]:
    """
    Verify if a stock symbol is valid (NSE/BSE listed).
    
    Args:
        stock_symbol: Stock symbol to validate
        exchange: "NSE", "BSE", or "both"
    
    Returns:
        Validation result with stock details
    """
    try:
        ticker = get_stock_ticker(stock_symbol, exchange)
        stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        info = fetch_info_safe(stock, timeout=10)
        
        if not info or 'symbol' not in info:
            return {
                "is_valid": False,
                "stock_symbol": stock_symbol,
                "message": "Stock not found in specified exchange",
                "suggestions": [
                    "Check symbol spelling",
                    "Try the other exchange (NSE/BSE)",
                    "Verify stock is actively traded"
                ]
            }
        
        return {
            "is_valid": True,
            "stock_symbol": stock_symbol,
            "company_name": info.get("longName", "N/A"),
            "exchange": exchange,
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "status": "listed",
            "currency": info.get("currency", "INR"),
            "market_cap_cr": round(info.get("marketCap", 0) / 10000000, 2) if info.get("marketCap") else None
        }
        
    except Exception as e:
        return {
            "is_valid": False,
            "stock_symbol": stock_symbol,
            "error": str(e),
            "suggestions": ["Check symbol format", "Verify exchange"]
        }


if __name__ == "__main__":
    mcp.run()

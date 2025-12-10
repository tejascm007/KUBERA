"""
MCP SERVER 3: GOVERNANCE & COMPLIANCE SERVER
Purpose: Fetch corporate governance, compliance, and company quality indicators
Data Sources: Yahoo Finance, NSE/BSE Filings, Company Reports
"""

from fastmcp import FastMCP
import yfinance as yf
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import sys
import os
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.utils import fetch_ticker_safe, fetch_history_safe, fetch_info_safe, fetch_financials_safe

# Initialize FastMCP
mcp = FastMCP("GovernanceComplianceServer")

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
def fetch_promoter_holding_data(
    stock_symbol: str
) -> Dict[str, Any]:
    """
    Get promoter shareholding and pledging information.
    
    Args:
        stock_symbol: Stock symbol
    
    Returns:
        Promoter holding data with pledging details
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        info = fetch_info_safe(stock, timeout=10)
        
        # Get major holders data
        major_holders = stock.major_holders
        
        result = {
            "stock_symbol": stock_symbol,
            "promoter_data": {
                "total_promoter_holding_percent": None,
                "promoter_holding_classification": "unknown"
            },
            "pledged_data": {
                "pledged_shares_percent": 0,
                "pledged_classification": "safe",
                "risk_assessment": "low"
            },
            "holding_changes": {
                "trend": "stable",
                "insider_confidence": "neutral"
            },
            "data_source": "Yahoo Finance / Stock Exchange Filings",
            "note": "Detailed promoter data requires stock exchange filings"
        }
        
        # Parse major holders if available
        if not major_holders.empty and len(major_holders) >= 2:
            try:
                # Row 0 is typically insiders/promoters
                insider_percent = float(major_holders.iloc[0, 0].strip('%'))
                result["promoter_data"]["total_promoter_holding_percent"] = round(insider_percent, 2)
                
                # Classify holding
                if insider_percent < 15:
                    result["promoter_data"]["promoter_holding_classification"] = "low"
                elif insider_percent < 35:
                    result["promoter_data"]["promoter_holding_classification"] = "medium"
                else:
                    result["promoter_data"]["promoter_holding_classification"] = "high"
            except:
                pass
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching promoter data: {str(e)}"
        )


@mcp.tool()
def fetch_board_composition(
    stock_symbol: str
) -> Dict[str, Any]:
    """
    Get board structure and independent director information.
    
    Args:
        stock_symbol: Stock symbol
    
    Returns:
        Board composition data
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        info = fetch_info_safe(stock, timeout=10)
        
        # Get company officers (board members)
        officers = info.get("companyOfficers", [])
        
        result = {
            "stock_symbol": stock_symbol,
            "board_data": {
                "total_board_strength": len(officers),
                "key_executives_count": len([o for o in officers if o.get("title")]),
            },
            "board_composition": {
                "ceo": None,
                "cfo": None,
                "board_members": []
            },
            "board_quality": {
                "leadership_strength": "good" if len(officers) >= 5 else "limited",
                "board_effectiveness": "moderate"
            },
            "data_source": "Yahoo Finance / Company Filings",
            "note": "Detailed board composition requires annual report analysis"
        }
        
        # Extract key executives
        for officer in officers[:10]:
            title = officer.get("title", "")
            name = officer.get("name", "Unknown")
            age = officer.get("age")
            
            officer_data = {
                "name": name,
                "title": title,
                "age": age
            }
            
            if "CEO" in title.upper() or "CHIEF EXECUTIVE" in title.upper():
                result["board_composition"]["ceo"] = officer_data
            elif "CFO" in title.upper() or "CHIEF FINANCIAL" in title.upper():
                result["board_composition"]["cfo"] = officer_data
            else:
                result["board_composition"]["board_members"].append(officer_data)
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching board composition: {str(e)}"
        )


@mcp.tool()
def fetch_audit_quality(
    stock_symbol: str
) -> Dict[str, Any]:
    """
    Get auditor information and audit quality metrics.
    
    Args:
        stock_symbol: Stock symbol
    
    Returns:
        Audit quality data
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        info = fetch_info_safe(stock, timeout=10)
        
        result = {
            "stock_symbol": stock_symbol,
            "statutory_auditor": {
                "auditor_name": info.get("auditRisk", "Unknown"),
                "auditor_type": "unknown",
                "auditor_quality": "standard"
            },
            "audit_metrics": {
                "qualified_opinion": False,
                "audit_opinion": "unqualified",
                "audit_risk": info.get("auditRisk", 5),  # 1-10 scale
                "board_risk": info.get("boardRisk", 5),
                "compensation_risk": info.get("compensationRisk", 5),
                "shareholder_rights_risk": info.get("shareHolderRightsRisk", 5),
                "overall_risk": info.get("overallRisk", 5)
            },
            "audit_quality_score": 10 - info.get("overallRisk", 5) if info.get("overallRisk") else 7.5,
            "audit_risk_classification": "low" if info.get("overallRisk", 5) <= 3 else "medium" if info.get("overallRisk", 5) <= 6 else "high",
            "data_source": "Yahoo Finance Risk Metrics",
            "note": "Detailed audit information requires annual report analysis"
        }
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching audit quality: {str(e)}"
        )


@mcp.tool()
def fetch_regulatory_compliance(
    stock_symbol: str,
    lookback_years: int = 3
) -> Dict[str, Any]:
    """
    Get regulatory violations and compliance status.
    
    Args:
        stock_symbol: Stock symbol
        lookback_years: Years to look back (default: 3)
    
    Returns:
        Regulatory compliance data
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        info = fetch_info_safe(stock, timeout=10)

        
        result = {
            "stock_symbol": stock_symbol,
            "lookback_period": f"{lookback_years} years",
            "regulatory_violations": [],
            "sebi_penalties": [],
            "exchange_warnings": [],
            "compliance_status": {
                "sebi_compliance": "compliant",
                "stock_exchange_compliance": "compliant",
                "corporate_governance_code_compliance": "full",
                "insider_trading_policy": "standard"
            },
            "governance_risks": {
                "audit_risk": info.get("auditRisk", 5),
                "board_risk": info.get("boardRisk", 5),
                "compensation_risk": info.get("compensationRisk", 5),
                "shareholder_rights_risk": info.get("shareHolderRightsRisk", 5),
                "overall_risk": info.get("overallRisk", 5)
            },
            "compliance_score": 10 - info.get("overallRisk", 5) if info.get("overallRisk") else 8.0,
            "red_flags": [],
            "data_source": "Yahoo Finance / Stock Exchange Disclosures",
            "note": "Real-time violations require SEBI website monitoring"
        }
        
        # Add red flags based on risk scores
        if info.get("overallRisk", 5) > 7:
            result["red_flags"].append("High overall governance risk")
        if info.get("auditRisk", 5) > 7:
            result["red_flags"].append("High audit risk detected")
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching compliance data: {str(e)}"
        )


@mcp.tool()
def fetch_shareholding_pattern(
    stock_symbol: str,
    date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get complete shareholding pattern breakdown.
    
    Args:
        stock_symbol: Stock symbol
        date: Optional specific date "YYYY-MM-DD"
    
    Returns:
        Shareholding pattern data
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        info = fetch_info_safe(stock, timeout=10)
        major_holders = stock.major_holders
        
        result = {
            "stock_symbol": stock_symbol,
            "as_of_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "shareholding_breakdown": {
                "institutional_percent": round(info.get("heldPercentInstitutions", 0) * 100, 2) if info.get("heldPercentInstitutions") else None,
                "insiders_percent": round(info.get("heldPercentInsiders", 0) * 100, 2) if info.get("heldPercentInsiders") else None,
                "float_percent": round(info.get("floatShares", 0) / info.get("sharesOutstanding", 1) * 100, 2) if info.get("floatShares") and info.get("sharesOutstanding") else None
            },
            "detailed_breakdown": [],
            "concentration_metrics": {
                "ownership_concentration": "moderate",
                "float_available": "good" if info.get("floatShares", 0) / info.get("sharesOutstanding", 1) > 0.25 else "low"
            },
            "volatility_risk": "low",
            "data_source": "Yahoo Finance"
        }
        
        # Parse major holders
        if not major_holders.empty:
            for index, row in major_holders.iterrows():
                result["detailed_breakdown"].append({
                    "category": row[1],
                    "percent": float(row[0].strip('%')) if isinstance(row[0], str) else row[0]
                })
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching shareholding pattern: {str(e)}"
        )


@mcp.tool()
def fetch_related_party_transactions(
    stock_symbol: str,
    year: Optional[int] = None
) -> Dict[str, Any]:
    """
    Identify and analyze related party transactions.
    
    Args:
        stock_symbol: Stock symbol
        year: Optional specific year
    
    Returns:
        Related party transaction data
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        sstock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        info = fetch_info_safe(stock, timeout=10)
        
        result = {
            "stock_symbol": stock_symbol,
            "fiscal_year": year or datetime.utcnow().year,
            "related_party_transactions": [],
            "total_rpt_amount_cr": 0,
            "total_rpt_percent_of_revenue": 0,
            "rpt_risk_assessment": "low",
            "conflict_of_interest_flags": [],
            "disclosure_quality": "standard",
            "data_source": "Company Annual Reports",
            "note": "Detailed RPT data requires annual report analysis"
        }
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching RPT data: {str(e)}"
        )


@mcp.tool()
def fetch_governance_score(
    stock_symbol: str
) -> Dict[str, Any]:
    """
    Calculate overall governance quality score.
    
    Args:
        stock_symbol: Stock symbol
    
    Returns:
        Comprehensive governance score
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        info = fetch_info_safe(stock, timeout=10)
        
        # Calculate component scores
        audit_risk = info.get("auditRisk", 5)
        board_risk = info.get("boardRisk", 5)
        compensation_risk = info.get("compensationRisk", 5)
        shareholder_risk = info.get("shareHolderRightsRisk", 5)
        overall_risk = info.get("overallRisk", 5)
        
        # Convert risks to scores (10 - risk = score)
        audit_score = 10 - audit_risk
        board_score = 10 - board_risk
        compensation_score = 10 - compensation_risk
        shareholder_score = 10 - shareholder_risk
        
        # Calculate weighted overall score
        overall_score = (audit_score * 0.3 + board_score * 0.3 + 
                        compensation_score * 0.2 + shareholder_score * 0.2)
        
        result = {
            "stock_symbol": stock_symbol,
            "overall_governance_score": round(overall_score, 2),
            "component_scores": {
                "audit_quality": round(audit_score, 1),
                "board_quality": round(board_score, 1),
                "compensation_fairness": round(compensation_score, 1),
                "shareholder_rights": round(shareholder_score, 1)
            },
            "governance_classification": (
                "excellent" if overall_score >= 8.5 else
                "good" if overall_score >= 7.5 else
                "average" if overall_score >= 6.5 else
                "poor"
            ),
            "governance_highlights": [],
            "governance_concerns": [],
            "governance_trend": "stable",
            "data_source": "Yahoo Finance ESG Scores"
        }
        
        # Add highlights and concerns
        if audit_score >= 8:
            result["governance_highlights"].append("Strong audit quality")
        if board_score >= 8:
            result["governance_highlights"].append("Well-structured board")
        
        if audit_risk >= 7:
            result["governance_concerns"].append("High audit risk")
        if board_risk >= 7:
            result["governance_concerns"].append("Board structure concerns")
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error calculating governance score: {str(e)}"
        )


@mcp.tool()
def fetch_insider_transactions(
    stock_symbol: str,
    months: int = 6
) -> Dict[str, Any]:
    """
    Get insider trading patterns (directors/promoters buying/selling).
    
    Args:
        stock_symbol: Stock symbol
        months: Last N months (default: 6)
    
    Returns:
        Insider transaction data
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = yf.Ticker(ticker)
        
        # Get insider transactions
        insider_transactions = stock.insider_transactions
        
        result = {
            "stock_symbol": stock_symbol,
            "period": f"last_{months}_months",
            "insider_transactions": [],
            "insider_sentiment": "neutral",
            "net_insider_position": "neutral",
            "insider_confidence": "moderate",
            "data_source": "Yahoo Finance Insider Transactions"
        }
        
        if not insider_transactions.empty:
            cutoff_date = datetime.now() - timedelta(days=months*30)
            
            buy_count = 0
            sell_count = 0
            
            for index, row in insider_transactions.iterrows():
                transaction_date = row.get("Start Date")
                
                if pd.notna(transaction_date) and transaction_date >= cutoff_date:
                    transaction_type = "purchase" if row.get("Transaction") == "Buy" else "sale"
                    
                    if transaction_type == "purchase":
                        buy_count += 1
                    else:
                        sell_count += 1
                    
                    result["insider_transactions"].append({
                        "insider_name": row.get("Insider", "Unknown"),
                        "transaction_type": transaction_type,
                        "transaction_date": transaction_date.strftime("%Y-%m-%d"),
                        "shares": int(row.get("Shares", 0)),
                        "value": row.get("Value"),
                        "signal": "bullish" if transaction_type == "purchase" else "neutral"
                    })
            
            # Determine sentiment
            if buy_count > sell_count * 2:
                result["insider_sentiment"] = "bullish"
                result["net_insider_position"] = "strong_buying"
                result["insider_confidence"] = "high"
            elif sell_count > buy_count * 2:
                result["insider_sentiment"] = "bearish"
                result["net_insider_position"] = "strong_selling"
                result["insider_confidence"] = "low"
            else:
                result["insider_sentiment"] = "mixed"
                result["net_insider_position"] = "balanced"
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching insider transactions: {str(e)}"
        )


if __name__ == "__main__":
    mcp.run()

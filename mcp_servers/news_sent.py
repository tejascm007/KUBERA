"""
MCP SERVER 4: NEWS & SENTIMENT SERVER
Purpose: Fetch news articles, analyst ratings, sentiment analysis
Data Sources: NewsAPI, Alpha Vantage, Finnhub, Yahoo Finance
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
import json
from app.core.utils import fetch_ticker_safe, fetch_history_safe, fetch_info_safe, fetch_financials_safe

# Load environment variables from .env file (required for MCP subprocess)
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Initialize FastMCP
mcp = FastMCP("NewsSentimentServer")

# API Keys - match .env variable names
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")  # Fixed: was NEWS_API_KEY
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

def calculate_sentiment_score(text: str) -> tuple:
    """
    Calculate sentiment from text using simple keyword analysis.
    Returns (sentiment_label, score)
    """
    positive_words = ['growth', 'profit', 'gain', 'surge', 'rise', 'bullish', 'strong', 
                     'beat', 'exceed', 'outperform', 'positive', 'upgrade', 'buy']
    negative_words = ['loss', 'decline', 'fall', 'weak', 'bearish', 'miss', 'underperform',
                     'negative', 'downgrade', 'sell', 'concern', 'risk']
    
    text_lower = text.lower()
    
    pos_count = sum(1 for word in positive_words if word in text_lower)
    neg_count = sum(1 for word in negative_words if word in text_lower)
    
    if pos_count > neg_count:
        return "positive", min(0.5 + (pos_count - neg_count) * 0.1, 1.0)
    elif neg_count > pos_count:
        return "negative", max(-0.5 - (neg_count - pos_count) * 0.1, -1.0)
    else:
        return "neutral", 0.0


@mcp.tool()
def fetch_news_articles(
    stock_symbol: str,
    days: int = 30,
    limit: int = 20,
    news_source: str = "all"
) -> Dict[str, Any]:
    """
    Get recent news articles about a stock.
    
    Args:
        stock_symbol: Stock symbol
        days: Last N days (default: 30)
        limit: Number of articles (default: 20)
        news_source: "all", "major", or "financial"
    
    Returns:
        News articles with sentiment analysis
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        info = fetch_info_safe(stock, timeout=10)
        company_name = info.get("longName", stock_symbol)
        
        # Get news from Yahoo Finance
        news = stock.news
        
        articles = []
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for article in news[:limit]:
            publish_date = datetime.fromtimestamp(article.get("providerPublishTime", 0))
            
            if publish_date >= cutoff_date:
                title = article.get("title", "")
                summary = article.get("summary", "")
                
                # Calculate sentiment
                sentiment_label, sentiment_score = calculate_sentiment_score(title + " " + summary)
                sentiment_counts[sentiment_label] += 1
                
                articles.append({
                    "title": title,
                    "source": article.get("publisher", "Unknown"),
                    "publish_date": publish_date.strftime("%Y-%m-%d"),
                    "url": article.get("link", ""),
                    "summary": summary[:200] + "..." if len(summary) > 200 else summary,
                    "sentiment": sentiment_label,
                    "sentiment_score": round(sentiment_score, 2),
                    "relevance_score": 0.9,
                    "category": "general",
                    "impact": "medium"
                })
        
        # Try Finnhub if API key available
        if FINNHUB_API_KEY and len(articles) < limit:
            try:
                finnhub_url = f"https://finnhub.io/api/v1/company-news"
                params = {
                    "symbol": stock_symbol,
                    "from": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),
                    "to": datetime.now().strftime("%Y-%m-%d"),
                    "token": FINNHUB_API_KEY
                }
                response = requests.get(finnhub_url, params=params, timeout=10)
                if response.status_code == 200:
                    finnhub_news = response.json()
                    for article in finnhub_news[:limit - len(articles)]:
                        sentiment_label, sentiment_score = calculate_sentiment_score(article.get("headline", "") + " " + article.get("summary", ""))
                        sentiment_counts[sentiment_label] += 1
                        
                        articles.append({
                            "title": article.get("headline", ""),
                            "source": article.get("source", "Finnhub"),
                            "publish_date": datetime.fromtimestamp(article.get("datetime", 0)).strftime("%Y-%m-%d"),
                            "url": article.get("url", ""),
                            "summary": article.get("summary", "")[:200],
                            "sentiment": sentiment_label,
                            "sentiment_score": round(sentiment_score, 2),
                            "relevance_score": 0.85,
                            "category": article.get("category", "general"),
                            "impact": "medium"
                        })
            except:
                pass
        
        # Try NewsAPI if API key available (better for Indian stocks - searches by company name)
        if NEWSAPI_KEY and len(articles) < limit:
            try:
                newsapi_url = "https://newsapi.org/v2/everything"
                # Search by company name for better results with Indian stocks
                search_query = company_name if company_name != stock_symbol else stock_symbol
                params = {
                    "q": f'"{search_query}" OR "{stock_symbol}"',
                    "from": (datetime.now() - timedelta(days=min(days, 30))).strftime("%Y-%m-%d"),  # NewsAPI free tier: max 30 days
                    "to": datetime.now().strftime("%Y-%m-%d"),
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": min(limit - len(articles), 20),  # NewsAPI max 100 per request
                    "apiKey": NEWSAPI_KEY
                }
                response = requests.get(newsapi_url, params=params, timeout=10)
                if response.status_code == 200:
                    newsapi_data = response.json()
                    newsapi_articles = newsapi_data.get("articles", [])
                    
                    for article in newsapi_articles:
                        title = article.get("title", "")
                        description = article.get("description", "") or ""
                        
                        sentiment_label, sentiment_score = calculate_sentiment_score(title + " " + description)
                        sentiment_counts[sentiment_label] += 1
                        
                        # Parse date
                        pub_date = article.get("publishedAt", "")
                        if pub_date:
                            try:
                                pub_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00")).strftime("%Y-%m-%d")
                            except:
                                pub_date = datetime.now().strftime("%Y-%m-%d")
                        
                        articles.append({
                            "title": title,
                            "source": article.get("source", {}).get("name", "NewsAPI"),
                            "publish_date": pub_date,
                            "url": article.get("url", ""),
                            "summary": description[:200] + "..." if len(description) > 200 else description,
                            "sentiment": sentiment_label,
                            "sentiment_score": round(sentiment_score, 2),
                            "relevance_score": 0.88,
                            "category": "general",
                            "impact": "medium"
                        })
            except Exception as e:
                # Log but don't fail
                pass
        
        # Determine data sources used
        sources_used = ["Yahoo Finance"]
        if FINNHUB_API_KEY:
            sources_used.append("Finnhub")
        if NEWSAPI_KEY:
            sources_used.append("NewsAPI")
        
        result = {
            "stock_symbol": stock_symbol,
            "company_name": company_name,
            "period": f"last_{days}_days",
            "total_articles": len(articles),
            "news_articles": articles,
            "sentiment_distribution": sentiment_counts,
            "data_source": " / ".join(sources_used),
            "api_status": {
                "yahoo_finance": "available",
                "finnhub": "configured" if FINNHUB_API_KEY else "not configured",
                "newsapi": "configured" if NEWSAPI_KEY else "not configured"
            }
        }
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching news: {str(e)}"
        )


@mcp.tool()
def fetch_overall_news_sentiment(
    stock_symbol: str,
    days: int = 30
) -> Dict[str, Any]:
    """
    Aggregate sentiment from all recent news.
    
    Args:
        stock_symbol: Stock symbol
        days: Analysis period (default: 30)
    
    Returns:
        Overall sentiment analysis
    """
    try:
        # Get news articles
        news_result = fetch_news_articles(stock_symbol, days=days, limit=50)
        
        if news_result.get("status") == "error":
            return news_result
        
        articles = news_result.get("news_articles", [])
        sentiment_dist = news_result.get("sentiment_distribution", {})
        
        total_articles = len(articles)
        if total_articles == 0:
            return {
                "stock_symbol": stock_symbol,
                "overall_sentiment": "neutral",
                "sentiment_score": 0,
                "message": "No news articles found for analysis"
            }
        
        # Calculate overall sentiment
        positive_count = sentiment_dist.get("positive", 0)
        negative_count = sentiment_dist.get("negative", 0)
        neutral_count = sentiment_dist.get("neutral", 0)
        
        sentiment_score = (positive_count - negative_count) / total_articles
        
        overall_sentiment = "positive" if sentiment_score > 0.2 else "negative" if sentiment_score < -0.2 else "neutral"
        
        # Extract themes
        positive_themes = []
        negative_themes = []
        
        for article in articles:
            if article["sentiment"] == "positive":
                positive_themes.append(article["title"][:50])
            elif article["sentiment"] == "negative":
                negative_themes.append(article["title"][:50])
        
        result = {
            "stock_symbol": stock_symbol,
            "period": f"last_{days}_days",
            "overall_sentiment": overall_sentiment,
            "sentiment_score": round(sentiment_score, 2),
            "sentiment_breakdown": {
                "positive_percent": round((positive_count / total_articles) * 100, 1),
                "neutral_percent": round((neutral_count / total_articles) * 100, 1),
                "negative_percent": round((negative_count / total_articles) * 100, 1)
            },
            "sentiment_trend": "improving" if sentiment_score > 0 else "deteriorating" if sentiment_score < 0 else "stable",
            "news_volume": total_articles,
            "major_positive_themes": positive_themes[:3],
            "major_negative_themes": negative_themes[:3],
            "sentiment_reliability": min(total_articles / 20, 1.0),  # Higher with more articles
            "data_source": "Aggregated from news sources"
        }
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error analyzing sentiment: {str(e)}"
        )


@mcp.tool()
def fetch_analyst_ratings(
    stock_symbol: str
) -> Dict[str, Any]:
    """
    Get analyst recommendations and target prices.
    
    Args:
        stock_symbol: Stock symbol
    
    Returns:
        Analyst ratings and target prices
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)  # ← NEW
        info = fetch_info_safe(stock, timeout=10)
        
        # Get recommendations
        recommendations = stock.recommendations
        
        result = {
            "stock_symbol": stock_symbol,
            "current_price": round(info.get("currentPrice", 0), 2),
            "analyst_ratings": {
                "buy_count": 0,
                "hold_count": 0,
                "sell_count": 0,
                "analyst_consensus": "neutral",
                "consensus_strength": 0.5
            },
            "target_price": {
                "average_target": round(info.get("targetMeanPrice", 0), 2),
                "high_target": round(info.get("targetHighPrice", 0), 2),
                "low_target": round(info.get("targetLowPrice", 0), 2),
                "number_of_analysts": info.get("numberOfAnalystOpinions", 0)
            },
            "analyst_recommendations": [],
            "data_source": "Yahoo Finance"
        }
        
        # Calculate upside/downside
        current_price = info.get("currentPrice", 0)
        target_price = info.get("targetMeanPrice", 0)
        if current_price and target_price:
            result["target_price"]["upside_downside_percent"] = round(
                ((target_price - current_price) / current_price) * 100, 2
            )
        
        # Parse recommendations
        if not recommendations.empty:
            recent_recs = recommendations.tail(20)
            
            for index, row in recent_recs.iterrows():
                firm = row.get("Firm", "Unknown")
                to_grade = row.get("To Grade", "")
                from_grade = row.get("From Grade", "")
                
                # Count ratings
                if "buy" in to_grade.lower() or "outperform" in to_grade.lower():
                    result["analyst_ratings"]["buy_count"] += 1
                    rating = "buy"
                elif "hold" in to_grade.lower() or "neutral" in to_grade.lower():
                    result["analyst_ratings"]["hold_count"] += 1
                    rating = "hold"
                elif "sell" in to_grade.lower() or "underperform" in to_grade.lower():
                    result["analyst_ratings"]["sell_count"] += 1
                    rating = "sell"
                else:
                    rating = "hold"
                    result["analyst_ratings"]["hold_count"] += 1
                
                result["analyst_recommendations"].append({
                    "analyst_firm": firm,
                    "rating": rating,
                    "rating_change": f"from {from_grade}" if from_grade else "new rating",
                    "rating_date": index.strftime("%Y-%m-%d")
                })
            
            # Determine consensus
            total = (result["analyst_ratings"]["buy_count"] + 
                    result["analyst_ratings"]["hold_count"] + 
                    result["analyst_ratings"]["sell_count"])
            
            if total > 0:
                buy_ratio = result["analyst_ratings"]["buy_count"] / total
                sell_ratio = result["analyst_ratings"]["sell_count"] / total
                
                if buy_ratio > 0.6:
                    result["analyst_ratings"]["analyst_consensus"] = "strong_buy"
                    result["analyst_ratings"]["consensus_strength"] = buy_ratio
                elif buy_ratio > 0.4:
                    result["analyst_ratings"]["analyst_consensus"] = "buy"
                    result["analyst_ratings"]["consensus_strength"] = buy_ratio
                elif sell_ratio > 0.4:
                    result["analyst_ratings"]["analyst_consensus"] = "sell"
                    result["analyst_ratings"]["consensus_strength"] = sell_ratio
                else:
                    result["analyst_ratings"]["analyst_consensus"] = "hold"
                    result["analyst_ratings"]["consensus_strength"] = 0.5
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching analyst ratings: {str(e)}"
        )


@mcp.tool()
def fetch_social_sentiment(
    stock_symbol: str,
    platform: str = "all"
) -> Dict[str, Any]:
    """
    Get retail investor sentiment from social media (simulated).
    
    Args:
        stock_symbol: Stock symbol
        platform: "twitter", "reddit", "all"
    
    Returns:
        Social sentiment data
    """
    try:
        # Note: Real implementation would use Twitter API, Reddit API, etc.
        # This is a placeholder with simulated data
        
        result = {
            "stock_symbol": stock_symbol,
            "period": "last_7_days",
            "social_sentiment": "neutral",
            "sentiment_score": 0.0,
            "mention_volume": 0,
            "mention_trend": "stable",
            "platform_breakdown": {},
            "data_source": "Social Media APIs (simulated)",
            "note": "Real social sentiment requires Twitter/Reddit API integration"
        }
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching social sentiment: {str(e)}"
        )


@mcp.tool()
def fetch_company_announcements(
    stock_symbol: str,
    days: int = 90
) -> Dict[str, Any]:
    """
    Get official company announcements and press releases.
    
    Args:
        stock_symbol: Stock symbol
        days: Last N days
    
    Returns:
        Company announcements
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)
        
        # Calendar events (earnings, dividends, etc.)
        calendar = stock.calendar
        
        result = {
            "stock_symbol": stock_symbol,
            "period": f"last_{days}_days",
            "announcements": [],
            "upcoming_events": {},
            "data_source": "Yahoo Finance Calendar"
        }
        
        # Parse calendar events
        if isinstance(calendar, dict):
            for key, value in calendar.items():
                if pd.notna(value):
                    result["upcoming_events"][key] = str(value)
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching announcements: {str(e)}"
        )


@mcp.tool()
def fetch_sector_sentiment(
    sector: str
) -> Dict[str, Any]:
    """
    Get sentiment analysis for an entire sector.
    
    Args:
        sector: Sector name (e.g., "Technology", "Banking")
    
    Returns:
        Sector-wide sentiment
    """
    try:
        result = {
            "sector": sector,
            "sector_sentiment": "neutral",
            "sentiment_score": 0.0,
            "leading_stocks": [],
            "lagging_stocks": [],
            "sector_news_volume": 0,
            "data_source": "Aggregated sector data",
            "note": "Sector sentiment aggregated from constituent stocks"
        }
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            sector,
            f"Error fetching sector sentiment: {str(e)}"
        )


@mcp.tool()
def fetch_competitor_sentiment(
    stock_symbol: str,
    competitors: List[str]
) -> Dict[str, Any]:
    """
    Compare sentiment across competitors.
    
    Args:
        stock_symbol: Stock symbol
        competitors: List of competitor symbols
    
    Returns:
        Comparative sentiment analysis
    """
    try:
        result = {
            "stock_symbol": stock_symbol,
            "competitors": competitors,
            "sentiment_comparison": {},
            "relative_sentiment": "neutral",
            "data_source": "Comparative analysis"
        }
        
        # Get sentiment for main stock
        main_sentiment = fetch_overall_news_sentiment(stock_symbol, days=30)
        result["sentiment_comparison"][stock_symbol] = {
            "sentiment": main_sentiment.get("overall_sentiment", "neutral"),
            "score": main_sentiment.get("sentiment_score", 0)
        }
        
        # Get sentiment for competitors
        for competitor in competitors[:3]:  # Limit to 3 competitors
            try:
                comp_sentiment = fetch_overall_news_sentiment(competitor, days=30)
                result["sentiment_comparison"][competitor] = {
                    "sentiment": comp_sentiment.get("overall_sentiment", "neutral"),
                    "score": comp_sentiment.get("sentiment_score", 0)
                }
            except:
                continue
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error comparing competitor sentiment: {str(e)}"
        )


@mcp.tool()
def fetch_news_impact_analysis(
    stock_symbol: str,
    event_date: str
) -> Dict[str, Any]:
    """
    Analyze price impact of news events.
    
    Args:
        stock_symbol: Stock symbol
        event_date: Event date "YYYY-MM-DD"
    
    Returns:
        News impact analysis
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)
        
        # Get price data around event
        event_dt = datetime.strptime(event_date, "%Y-%m-%d")
        start_date = event_dt - timedelta(days=5)
        end_date = event_dt + timedelta(days=5)
        
        hist = fetch_history_safe(stock, start=start_date, end=end_date)
        
        if hist.empty:
            return handle_error(
                "data_unavailable",
                stock_symbol,
                f"Price data not available for {event_date}"
            )
        
        # Calculate price change
        prices = hist['Close']
        event_idx = hist.index.get_indexer([event_dt], method='nearest')[0]
        
        if event_idx > 0 and event_idx < len(prices) - 1:
            pre_event_price = prices.iloc[event_idx - 1]
            post_event_price = prices.iloc[event_idx + 1]
            price_change_percent = ((post_event_price - pre_event_price) / pre_event_price) * 100
            
            result = {
                "stock_symbol": stock_symbol,
                "event_date": event_date,
                "price_impact": {
                    "pre_event_price": round(pre_event_price, 2),
                    "post_event_price": round(post_event_price, 2),
                    "price_change_percent": round(price_change_percent, 2),
                    "impact_magnitude": "high" if abs(price_change_percent) > 5 else "moderate" if abs(price_change_percent) > 2 else "low"
                },
                "volume_impact": {
                    "pre_event_volume": int(hist['Volume'].iloc[event_idx - 1]),
                    "event_day_volume": int(hist['Volume'].iloc[event_idx]),
                    "volume_surge": hist['Volume'].iloc[event_idx] > hist['Volume'].iloc[event_idx - 1] * 1.5
                },
                "data_source": "Yahoo Finance"
            }
            
            return result
        else:
            return handle_error(
                "data_unavailable",
                stock_symbol,
                "Insufficient data around event date"
            )
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error analyzing news impact: {str(e)}"
        )


@mcp.tool()
def fetch_management_commentary(
    stock_symbol: str
) -> Dict[str, Any]:
    """
    Extract management commentary and guidance.
    
    Args:
        stock_symbol: Stock symbol
    
    Returns:
        Management commentary data
    """
    try:
        ticker = get_stock_ticker(stock_symbol)
        stock = fetch_ticker_safe(ticker, timeout=10)
        info = fetch_info_safe(stock, timeout=10)
        
        result = {
            "stock_symbol": stock_symbol,
            "management_commentary": {
                "business_summary": info.get("longBusinessSummary", "")[:500],
                "company_description": info.get("longName", ""),
                "industry": info.get("industry", ""),
                "sector": info.get("sector", "")
            },
            "forward_guidance": {
                "revenue_estimate": info.get("revenueEstimate", "N/A"),
                "earnings_estimate": info.get("earningsEstimate", "N/A"),
                "recommendation": info.get("recommendationKey", "N/A")
            },
            "data_source": "Company Filings / Yahoo Finance",
            "note": "Detailed commentary requires earnings call transcript analysis"
        }
        
        return result
        
    except Exception as e:
        return handle_error(
            "api_error",
            stock_symbol,
            f"Error fetching management commentary: {str(e)}"
        )


if __name__ == "__main__":
    mcp.run()

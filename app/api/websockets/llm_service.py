"""
LLMService for WebSocket Chat
Wraps the existing LLMMCPOrchestrator for real-time streaming
"""

import logging
from typing import AsyncGenerator, Dict, Any, List
from asyncpg import Record 
from app.mcp.llm_integration import process_user_message_streaming
from app.mcp.client import kubera_mcp_client
from app.exceptions.custom_exceptions import MCPException

logger = logging.getLogger(__name__)


class LLMService:
    """
    Service for LLM API calls via WebSocket
    Uses the existing LLMMCPOrchestrator from llm_integration.py
    
    Features:
    - Groq LLM integration
    - MCP tool orchestration
    - Real-time streaming
    - Portfolio context injection
    - Error handling
    """
    
    def __init__(self, db_pool=None):
        """Initialize LLM Service with optional database pool for portfolio access"""
        self.mcp_client = kubera_mcp_client
        self.db_pool = db_pool
        logger.info("LLMService initialized (using LLMMCPOrchestrator)")
    
    async def _fetch_portfolio_context(self, user_id: str) -> str:
        """
        Fetch user's portfolio and format it as context for LLM
        
        Args:
            user_id: User's UUID
            
        Returns:
            Formatted portfolio context string, or empty string if no portfolio
        """
        if not self.db_pool:
            logger.warning("No database pool available for portfolio fetch")
            return ""
        
        try:
            from app.db.repositories.portfolio_repository import PortfolioRepository
            
            portfolio_repo = PortfolioRepository(self.db_pool)
            portfolio_entries = await portfolio_repo.get_user_portfolio(user_id)
            
            if not portfolio_entries:
                return ""
            
            # Format portfolio data for LLM
            portfolio_lines = []
            total_investment = 0
            
            for entry in portfolio_entries:
                symbol = entry.get('stock_symbol', 'Unknown')
                exchange = entry.get('exchange', 'NSE')
                quantity = entry.get('quantity', 0)
                buy_price = entry.get('buy_price', 0)
                investment = quantity * buy_price
                total_investment += investment
                
                portfolio_lines.append(
                    f"- {symbol} ({exchange}): {quantity} shares @ ₹{buy_price:.2f} = ₹{investment:,.2f}"
                )
            
            portfolio_context = f"""
## User's Current Portfolio Holdings
The user has the following stocks in their portfolio (total investment: ₹{total_investment:,.2f}):

{chr(10).join(portfolio_lines)}

You can reference this portfolio data when answering questions about the user's holdings.
"""
            logger.info(f"Portfolio context prepared with {len(portfolio_entries)} entries")
            return portfolio_context
            
        except Exception as e:
            logger.error(f"Error fetching portfolio context: {e}")
            return ""
    
    
    async def stream_response(
        self,
        user_message: str,
        chat_id: str,
        user_id: str,
        chat_history: List[Dict[str, str]] = None
    ) -> AsyncGenerator:
        """
        Stream LLM response with MCP tool integration
        
        Uses the existing LLMMCPOrchestrator from llm_integration.py
        
        Args:
            user_message: User's input message
            chat_id: Chat session ID (for context/logging)
            user_id: User ID (for personalization)
            chat_history: Previous messages for context
        
        Yields:
            Chunks with different types:
            - text_chunk: Text streaming from LLM
            - tool_executing: Tool execution started
            - tool_result: Tool executed successfully
            - tool_error: Tool execution failed
            - message_complete: Entire response completed with metadata
            - error: Processing error
        """
        
        try:
            logger.info(f"Starting LLM stream for user {user_id}, chat {chat_id}")
            logger.info(f"User message: {user_message[:100]}...")
            
            # ========================================================================
            # STEP 1: ENSURE MCP CLIENT IS INITIALIZED
            # ========================================================================
            
            if not self.mcp_client.is_initialized():
                logger.warning(" MCP Client not initialized, attempting to initialize...")
                try:
                    await self.mcp_client.initialize()
                    logger.info(" MCP Client initialized successfully")
                    
                    # Log available tools
                    health = self.mcp_client.get_health_status()
                    logger.info(f" MCP Status: {health['total_servers']} servers, {health['total_tools']} tools available")
                
                except Exception as e:
                    logger.error(f" Failed to initialize MCP Client: {str(e)}", exc_info=True)
                    yield {
                        "type": "error",
                        "error": f"MCP Client initialization failed: {str(e)}"
                    }
                    return
            else:
                logger.info(" MCP Client already initialized")
            
            # ========================================================================
            # STEP 2: STREAM RESPONSE FROM ORCHESTRATOR
            # ========================================================================
            
            #  Transform chat_history to OpenAI format
            normalized_history = []
            if chat_history:
                for msg in chat_history:
                    # If it's an asyncpg Record, convert to dict first
                    if isinstance(msg, Record):
                        msg = dict(msg)
                    
                    # Database returns user_message and assistant_response per row
                    # Add user message first
                    user_msg = msg.get("user_message")
                    if user_msg:
                        normalized_history.append({
                            "role": "user",
                            "content": user_msg
                        })
                    
                    # Add assistant response
                    assistant_msg = msg.get("assistant_response")
                    if assistant_msg:
                        normalized_history.append({
                            "role": "assistant",
                            "content": assistant_msg
                        })

            # ========================================================================
            # STEP 3: INJECT PORTFOLIO CONTEXT
            # ========================================================================
            
            # Fetch user's portfolio and inject as context
            portfolio_context = await self._fetch_portfolio_context(user_id)
            
            # If portfolio context exists, inject it as a system-like user message
            # This gives the LLM knowledge of the user's holdings
            enhanced_message = user_message
            if portfolio_context:
                enhanced_message = f"{user_message}\n\n[SYSTEM CONTEXT - User's Portfolio Data]\n{portfolio_context}"
                logger.info(f"Portfolio context injected into message for user {user_id}")

            async for chunk in process_user_message_streaming(
                user_message=enhanced_message,
                conversation_history=normalized_history
            ):

                logger.debug(f" Streaming chunk: {chunk.get('type')}")
                
                #  CONVERT ORCHESTRATOR EVENTS TO WEBSOCKET EVENTS
                if chunk["type"] == "text_chunk":
                    # Stream text content to client
                    yield {
                        "type": "text_chunk",
                        "content": chunk["content"]
                    }
                
                elif chunk["type"] == "tool_call_start":
                    # Notify client that tool is executing
                    logger.info(f" Tool executing: {chunk['tool_name']}")
                    yield {
                        "type": "tool_executing",
                        "tool_name": chunk["tool_name"],
                        "tool_id": chunk["tool_id"]
                    }
                
                elif chunk["type"] == "tool_complete":
                    # Tool completed successfully
                    logger.info(f" Tool completed: {chunk['tool_name']}")
                    yield {
                        "type": "tool_result",
                        "tool_name": chunk["tool_name"],
                        "tool_id": chunk["tool_id"],
                        "success": True
                    }
                
                elif chunk["type"] == "tool_error":
                    # Tool execution failed
                    logger.error(f" Tool error: {chunk.get('tool_name')} - {chunk.get('error')}")
                    yield {
                        "type": "tool_error",
                        "tool_name": chunk.get("tool_name", "unknown"),
                        "tool_id": chunk.get("tool_id", ""),
                        "error": chunk.get("error", "Unknown error")
                    }
                
                elif chunk["type"] == "complete":
                    # Response completed with metadata
                    logger.info(f" Response complete. Tokens: {chunk.get('tokens_used')}, Tools: {chunk.get('tools_used')}")
                    
                    # Include chart_url and chart_html if visualization tool was used
                    chart_url = chunk.get("chart_url")
                    chart_html = chunk.get("chart_html")
                    if chart_url:
                        logger.info(f" Chart URL available: {chart_url[:50]}...")
                    if chart_html:
                        logger.info(f" Chart HTML available: {len(chart_html)} bytes")
                    
                    yield {
                        "type": "message_complete",
                        "metadata": {
                            "tokens_used": chunk.get("tokens_used", 0),
                            "tools_used": chunk.get("tools_used", []),
                            "iterations": chunk.get("iterations", 1),
                            "chart_url": chart_url,
                            "chart_html": chart_html  # Send HTML to frontend
                        }
                    }
                
                elif chunk["type"] == "error":
                    # Processing error occurred
                    logger.error(f" Processing error: {chunk.get('error')}")
                    yield {
                        "type": "error",
                        "error": chunk.get("error", "Unknown error")
                    }
                
                elif chunk["type"] == "max_iterations":
                    # Max iterations reached
                    logger.warning(f" Max iterations reached: {chunk.get('message')}")
                    yield {
                        "type": "error",
                        "error": chunk.get("message", "Maximum iterations reached")
                    }
            
            logger.info(f" LLM stream completed for chat {chat_id}")
        
        except MCPException as e:
            logger.error(f" MCP error: {str(e)}")
            yield {
                "type": "error",
                "error": f"MCP error: {str(e)}"
            }
        
        except Exception as e:
            logger.error(f" Error in LLM streaming: {str(e)}", exc_info=True)
            yield {
                "type": "error",
                "error": f"LLM processing error: {str(e)}"
            }

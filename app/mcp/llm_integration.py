"""
LLM + MCP Integration
Orchestrates LLM (Groq) with MCP tools
"""

import json
import logging
from typing import Dict, Any, List, AsyncGenerator
from datetime import datetime
from asyncpg import Record
from groq import AsyncGroq
from groq.types.chat import ChatCompletionMessageToolCall

from app.core.config import settings
from app.mcp.client import kubera_mcp_client
from app.mcp.tool_handler import mcp_tool_handler
from app.exceptions.custom_exceptions import MCPException

logger = logging.getLogger(__name__)



def _to_serializable(obj):
    # asyncpg Record → dict
    if isinstance(obj, Record):
        return dict(obj)
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serializable(v) for v in obj]
    return obj


class LLMMCPOrchestrator:
    """
    Orchestrates LLM (Groq) with MCP tools
    Handles the agentic loop: LLM -> Tools -> LLM -> Response
    """
    
    def __init__(self):
        self.mcp_client = kubera_mcp_client
        self.tool_handler = mcp_tool_handler
        self.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    
    # ========================================================================
    # SYSTEM PROMPT
    # ========================================================================
    
    def get_system_prompt(self) -> str:
        """Get system prompt for Groq LLM"""
        return """You are KUBERA, an expert AI assistant specializing in Indian stock market analysis.

You have access to comprehensive tools across 5 MCP servers:

**1. Financial Data Tools:**
- get_stock_info, get_company_profile, get_fundamentals
- get_financial_ratios, get_valuation_metrics, get_dividend_info

**2. Technical Analysis Tools:**
- get_technical_indicators, get_chart_patterns, get_support_resistance
- get_moving_averages, get_rsi, get_macd, get_bollinger_bands

**3. Governance & Compliance Tools:**
- get_corporate_actions, get_shareholding_pattern, get_promoter_holdings
- get_board_of_directors, get_quarterly_results

**4. News & Sentiment Tools:**
- get_stock_news, get_market_news, get_sentiment_analysis
- get_analyst_ratings, get_trending_stocks, get_market_movers

**5. Visualization Tools:**
- create_price_chart, create_candlestick_chart, create_technical_chart
- create_portfolio_pie_chart, create_comparison_chart

**Guidelines:**
1. For Indian stocks, use .NS suffix for NSE (e.g., INFY.NS, RELIANCE.NS)
2. Always gather multiple data points before providing analysis
3. Use tools strategically - don't call unnecessary tools
4. When creating charts, always describe what the chart shows
5. Provide actionable insights with proper context
6. Cite data sources when presenting numbers

## Your Responsibilities
1. Always use the most relevant tool for each query
2. Combine multiple tools when needed for comprehensive analysis
3. Provide clear, data-driven insights
4. Cite your sources when using web search
5. Explain your reasoning and analysis methodology

## Response Style
- Be professional yet conversational
- Use bullet points for clarity
- Include relevant metrics and data points
- Provide actionable insights, not just information

Be concise, accurate, and helpful."""
    
    # ========================================================================
    # STREAMING ORCHESTRATION
    # ========================================================================
    
    async def process_with_streaming(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]] = None,
        max_iterations: int = 2
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process user message with streaming responses
        
        This is the main agentic loop:
        1. Send prompt to Groq
        2. Groq decides which tools to call
        3. Execute tools via MCP
        4. Send results back to Groq
        5. Groq processes and responds
        6. Stream response to client
        
        Args:
            user_message: User's question
            conversation_history: Previous messages
            max_iterations: Maximum tool call iterations
        
        Yields:
            Streaming chunks with type indicators
        """
        if not self.mcp_client.is_initialized():
            raise MCPException("MCP Client not initialized")
        
        # Build messages (OpenAI format)
        messages = [
            {"role": "system", "content": self.get_system_prompt()}
        ]
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Get tools in OpenAI format (Groq uses same format)
        tools = self.tool_handler.get_tools_for_openai()
        
        iteration = 0
        total_tokens = 0
        tools_used = []
        
        while iteration < max_iterations:
            iteration += 1
            
            try:

                messages = _to_serializable(messages)   
                tools = _to_serializable(tools)
                # Call Groq with streaming
                stream = await self.groq_client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    max_tokens=settings.MAX_TOKENS,
                    temperature=settings.TEMPERATURE,
                    stream=True
                )
                
                current_text = ""
                tool_calls = []
                current_tool_call = None
                
                async for chunk in stream:
                    delta = chunk.choices[0].delta
                    
                    # Text content
                    if delta.content:
                        content = delta.content
                        current_text += content
                        
                        yield {
                            "type": "text_chunk",
                            "content": content
                        }
                    
                    # Tool calls
                    if delta.tool_calls:
                        for tool_call_delta in delta.tool_calls:
                            # New tool call
                            if tool_call_delta.id:
                                if current_tool_call:
                                    tool_calls.append(current_tool_call)
                                
                                current_tool_call = {
                                    "id": tool_call_delta.id,
                                    "type": "function",
                                    "function": {
                                        "name": tool_call_delta.function.name,
                                        "arguments": ""
                                    }
                                }
                                
                                yield {
                                    "type": "tool_call_start",
                                    "tool_name": tool_call_delta.function.name,
                                    "tool_id": tool_call_delta.id
                                }
                            
                            # Accumulate arguments
                            if tool_call_delta.function.arguments:
                                current_tool_call["function"]["arguments"] += tool_call_delta.function.arguments
                
                # Add last tool call if exists
                if current_tool_call:
                    tool_calls.append(current_tool_call)
                
                # Update token count (approximate for streaming)
                total_tokens += len(current_text.split()) * 1.3  # Rough estimate
                
                # No tool calls - we're done
                if not tool_calls:
                    yield {
                        "type": "complete",
                        "content": current_text,
                        "iterations": iteration,
                        "tokens_used": int(total_tokens),
                        "tools_used": tools_used
                    }
                    break
                
                # Parse tool call arguments
                parsed_tool_calls = []
                for tc in tool_calls:
                    try:
                        arguments = json.loads(tc["function"]["arguments"])
                        parsed_tool_calls.append({
                            "id": tc["id"],
                            "name": tc["function"]["name"],
                            "arguments": arguments
                        })
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse tool arguments: {e}")
                        yield {
                            "type": "tool_error",
                            "tool_name": tc["function"]["name"],
                            "tool_id": tc["id"],
                            "error": f"Invalid JSON arguments: {str(e)}"
                        }
                        continue
                
                # Execute tools
                tool_results = await self.tool_handler.execute_tools_batch(parsed_tool_calls)
                
                # Yield tool execution events
                for result in tool_results:
                    if result["success"]:
                        tools_used.append(result["tool_name"])
                        
                        yield {
                            "type": "tool_complete",
                            "tool_name": result["tool_name"],
                            "tool_id": result["tool_call_id"],
                            "success": True
                        }
                    else:
                        yield {
                            "type": "tool_error",
                            "tool_name": result["tool_name"],
                            "tool_id": result["tool_call_id"],
                            "error": result["error"]
                        }
                
                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": current_text if current_text else None,
                    "tool_calls": tool_calls
                })
                
                # Add tool results as tool messages
                for result in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": result["tool_call_id"],
                        "content": self.tool_handler.format_tool_result_for_llm(result)
                    })
                
                # Continue loop for next iteration
            
            except Exception as e:
                logger.error(f"Error in LLM orchestration: {e}")
                logger.exception("Full traceback:")
                yield {
                    "type": "error",
                    "error": str(e)
                }
                break
        
        if iteration >= max_iterations:
            yield {
                "type": "max_iterations",
                "message": "Maximum iterations reached"
            }
    
    # ========================================================================
    # NON-STREAMING (FOR BACKGROUND JOBS)
    # ========================================================================
    
    async def process_without_streaming(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Non-streaming version for background processing
        
        Returns:
            Complete response with metadata
        """
        start_time = datetime.now()
        
        full_response = ""
        tools_used = []
        total_tokens = 0
        
        async for chunk in self.process_with_streaming(user_message, conversation_history):
            if chunk["type"] == "text_chunk":
                full_response += chunk["content"]
            
            elif chunk["type"] == "tool_complete":
                if chunk["tool_name"] not in tools_used:
                    tools_used.append(chunk["tool_name"])
            
            elif chunk["type"] == "complete":
                total_tokens = chunk.get("tokens_used", 0)
        
        end_time = datetime.now()
        processing_time = int((end_time - start_time).total_seconds() * 1000)
        
        return {
            "response": full_response,
            "tokens_used": total_tokens,
            "tools_used": tools_used,
            "processing_time_ms": processing_time
        }


# ========================================================================
# GLOBAL INSTANCE
# ========================================================================

llm_mcp_orchestrator = LLMMCPOrchestrator()


# ========================================================================
# CONVENIENCE FUNCTIONS
# ========================================================================

async def process_user_message(
    user_message: str,
    conversation_history: List[Dict[str, str]] = None,
    streaming: bool = True
):
    """
    Process user message with LLM + MCP tools
    
    Args:
        user_message: User's question/prompt
        conversation_history: Previous conversation messages
        streaming: Whether to stream responses (default: True)
    
    Returns:
        If streaming=True: AsyncGenerator of response chunks
        If streaming=False: Complete response dict
    """
    if streaming:
        return llm_mcp_orchestrator.process_with_streaming(
            user_message=user_message,
            conversation_history=conversation_history
        )
    else:
        return await llm_mcp_orchestrator.process_without_streaming(
            user_message=user_message,
            conversation_history=conversation_history
        )


async def process_user_message_streaming(
    user_message: str,
    conversation_history: List[Dict[str, str]] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Process user message with streaming (explicit)
    
    Args:
        user_message: User's question
        conversation_history: Previous messages
    
    Yields:
        Response chunks
    """
    async for chunk in llm_mcp_orchestrator.process_with_streaming(
        user_message=user_message,
        conversation_history=conversation_history
    ):
        yield chunk


async def process_user_message_complete(
    user_message: str,
    conversation_history: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Process user message and return complete response (non-streaming)
    
    Args:
        user_message: User's question
        conversation_history: Previous messages
    
    Returns:
        Complete response with metadata
    """
    return await llm_mcp_orchestrator.process_without_streaming(
        user_message=user_message,
        conversation_history=conversation_history
    )

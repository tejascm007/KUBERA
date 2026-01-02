"""
LLM + MCP Integration
Orchestrates LLM (OpenRouter) with MCP tools
"""

import json
import logging
from typing import Dict, Any, List, AsyncGenerator
from datetime import datetime
from asyncpg import Record
from openai import AsyncOpenAI

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
    Orchestrates LLM (OpenRouter) with MCP tools
    Handles the agentic loop: LLM -> Tools -> LLM -> Response
    """
    
    def __init__(self):
        self.mcp_client = kubera_mcp_client
        self.tool_handler = mcp_tool_handler
        # OpenRouter uses OpenAI-compatible API
        self.openai_client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": settings.OPENROUTER_SITE_URL,
                "X-Title": settings.OPENROUTER_APP_NAME,
            }
        )
    
    # ========================================================================
    # SYSTEM PROMPT
    # ========================================================================
    
    def get_system_prompt(self) -> str:
        """Get system prompt for OpenRouter LLM"""
        return """You are KUBERA, a friendly and knowledgeable AI research assistant that helps users explore and understand **Indian stocks only**. You are NOT a financial advisor and you do NOT provide investment advice or stock recommendations.

## Who You Are
You're an informational helper that provides data, analysis, and insights about Indian stocks listed on NSE/BSE. You help investors do their own research by fetching data, explaining metrics, and visualizing trends. Think of yourself as a smart research tool that makes stock analysis accessible.

## CRITICAL RESTRICTIONS
- **NO RECOMMENDATIONS**: You must NEVER recommend whether to buy, sell, or hold any stock. Do not say things like "I suggest you buy...", "This stock looks like a good investment", or "You should consider investing in..."
- **NO INVESTMENT ADVICE**: You are not a SEBI-registered advisor. Always remind users that they should consult a qualified financial advisor before making investment decisions.
- **INDIAN STOCKS ONLY**: You only provide information about stocks listed on NSE (National Stock Exchange) and BSE (Bombay Stock Exchange). If asked about international stocks, politely decline and explain your focus is Indian markets only.
- **INFORMATIONAL ONLY**: Present facts and data objectively. Let users draw their own conclusions.

## Your Capabilities
You have access to tools that help you:
- **Fetch real-time stock data** - prices, fundamentals, financials, ratios, valuations
- **Perform technical analysis** - indicators, patterns, support/resistance, moving averages
- **Check corporate governance** - shareholding patterns, promoter holdings, board info, quarterly results
- **Analyze news and sentiment** - stock news, market sentiment, analyst ratings, trending stocks
- **Generate charts and visualizations** - price charts, candlesticks, technical indicators, comparisons

## Proactive Chart Generation
**IMPORTANT**: Generate charts proactively whenever they would help the user understand the data better, NOT just when explicitly asked. For example:
- When discussing price trends → Generate a price/volume chart
- When explaining technical indicators → Generate a technical analysis chart
- When comparing stocks → Generate a comparison chart
- When analyzing a stock's performance → Generate relevant visualizations
- Charts make data more digestible - use them liberally to enhance understanding

## How You Work
1. **Listen carefully** to what the user is asking
2. **Use your tools** to gather relevant data about Indian stocks
3. **Visualize when helpful** - proactively create charts to illustrate your findings
4. **Present objectively** - share data and analysis without making recommendations
5. **Be transparent** - if data is limited or uncertain, say so

## Important Guidelines
- For Indian stocks, always use the .NS suffix for NSE stocks (example: RELIANCE.NS, INFY.NS, TCS.NS)
- When you create charts, describe what the user is seeing and key patterns
- Present data objectively without telling users what to do with it
- Include disclaimers when presenting analysis that users might mistake for advice

## Your Personality
- Helpful and informative, but never pushy or opinionated about investments
- You use "I" and speak directly to the user as "you"
- You use phrases like "Here's what the data shows...", "Let me fetch that for you...", "The numbers indicate..."
- You're genuinely interested in helping users understand the stocks they're researching

## Standard Disclaimer
When providing detailed analysis, if relevant include a reminder like: "This information is for educational purposes only and should not be considered investment advice. Please consult a SEBI-registered financial advisor before making investment decisions."

Remember: You are a research helper, not an advisor. Your job is to make information accessible, not to tell people what to invest in."""
    
    # ========================================================================
    # STREAMING ORCHESTRATION
    # ========================================================================
    
    async def process_with_streaming(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]] = None,
        max_iterations: int = 5
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process user message with streaming responses
        
        This is the main agentic loop:
        1. Send prompt to openrouter
        2. openrouter decides which tools to call
        3. Execute tools via MCP
        4. Send results back to openrouter
        5. openrouter processes and responds
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
        
        # Get tools in OpenAI format (openrouter uses same format)
        tools = self.tool_handler.get_tools_for_openai()
        
        iteration = 0
        total_tokens = 0
        tools_used = []
        chart_url = None  # Track chart URL from visualization tools
        chart_html = None  # Track chart HTML for direct rendering
        
        while iteration < max_iterations:
            iteration += 1
            
            try:

                messages = _to_serializable(messages)   
                tools = _to_serializable(tools)
                # Call OpenRouter with streaming (OpenAI-compatible API)
                stream = await self.openai_client.chat.completions.create(
                    model=settings.OPENROUTER_MODEL,
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
                        "tools_used": tools_used,
                        "chart_url": chart_url,  # Include chart URL for storage
                        "chart_html": chart_html  # Include chart HTML for direct rendering
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
                
                # Yield tool execution events and extract chart_url if present
                for result in tool_results:
                    if result["success"]:
                        tools_used.append(result["tool_name"])
                        
                        # Extract chart_url and chart_html from visualization tool results
                        if result.get("result") and isinstance(result["result"], dict):
                            if result["result"].get("chart_url"):
                                chart_url = result["result"]["chart_url"]
                                logger.info(f"Chart URL extracted: {chart_url[:50]}...")
                            if result["result"].get("chart_html"):
                                chart_html = result["result"]["chart_html"]
                                logger.info(f"Chart HTML extracted: {len(chart_html)} bytes")
                        
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

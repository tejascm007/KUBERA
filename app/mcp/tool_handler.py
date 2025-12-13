"""
MCP Tool Handler
Handles tool invocation, result processing, and error handling
"""

import json
import logging
from typing import Dict, Any, List, Optional

from app.mcp.client import kubera_mcp_client
from app.exceptions.custom_exceptions import MCPException

logger = logging.getLogger(__name__)


class MCPToolHandler:
    """Handler for MCP tool operations"""
    
    def __init__(self):
        self.client = kubera_mcp_client
    
    # ========================================================================
    # TOOL INVOCATION
    # ========================================================================
    
    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        tool_call_id: Optional[str] = None,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        Execute a single tool
        
        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            tool_call_id: Tool call ID (for tracking)
            timeout: Timeout in seconds (default: 60)
        
        Returns:
            Formatted result with metadata
        """
        try:
            # Invoke tool via MCP client with timeout
            result = await self.client.invoke_tool(tool_name, arguments, timeout=timeout)
            
            # Handle timeout result (success=False with error)
            if not result.get("success", True):
                return {
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "success": False,
                    "result": None,
                    "error": result.get("error", "Unknown error")
                }
            
            # Get the raw result
            raw_result = result["result"]
            
            # Debug: Log the result type and structure
            logger.info(f"Tool {tool_name} raw result type: {type(raw_result)}")
            if isinstance(raw_result, str):
                logger.info(f"Tool {tool_name} raw result (string, first 200 chars): {raw_result[:200]}")
                # Try to parse JSON string to dict
                try:
                    raw_result = json.loads(raw_result)
                    logger.info(f"Tool {tool_name} result parsed from JSON: keys={list(raw_result.keys()) if isinstance(raw_result, dict) else 'not dict'}")
                except (json.JSONDecodeError, TypeError):
                    logger.info(f"Tool {tool_name} result is not JSON parseable")
            elif isinstance(raw_result, dict):
                logger.info(f"Tool {tool_name} result is dict with keys: {list(raw_result.keys())}")
                if "chart_url" in raw_result:
                    logger.info(f"Tool {tool_name} has chart_url: {raw_result['chart_url'][:50] if raw_result['chart_url'] else 'None'}...")
            
            return {
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "success": True,
                "result": raw_result,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Tool execution error [{tool_name}]: {e}")
            
            return {
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "success": False,
                "result": None,
                "error": str(e)
            }
    
    async def execute_tools_batch(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple tools in batch
        
        Args:
            tool_calls: List of tool calls with format:
                [{
                    "id": "tool_call_id",
                    "name": "tool_name",
                    "arguments": {...}
                }]
        
        Returns:
            List of results
        """
        results = []
        
        for call in tool_calls:
            result = await self.execute_tool(
                tool_name=call["name"],
                arguments=call.get("arguments", {}),
                tool_call_id=call.get("id")
            )
            results.append(result)
        
        return results
    
    # ========================================================================
    # RESULT FORMATTING
    # ========================================================================
    
    def format_tool_result_for_llm(
        self,
        tool_result: Dict[str, Any]
    ) -> str:
        """
        Format tool result for LLM consumption
        
        Args:
            tool_result: Tool execution result
        
        Returns:
            Formatted string for LLM
        """
        if tool_result["success"]:
            # Success - return result as JSON string
            return json.dumps(tool_result["result"], indent=2)
        else:
            # Error - return error message
            return json.dumps({
                "error": tool_result["error"],
                "tool": tool_result["tool_name"]
            })
    
    def format_tool_results_for_llm(
        self,
        tool_results: List[Dict[str, Any]]
    ) -> List[str]:
        """Format multiple tool results for LLM"""
        return [
            self.format_tool_result_for_llm(result)
            for result in tool_results
        ]
    
    # ========================================================================
    # TOOL METADATA
    # ========================================================================
    
    def get_tool_metadata(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a tool
        
        Args:
            tool_name: Name of the tool
        
        Returns:
            Tool metadata including description, parameters
        """
        tool = self.client.get_tool_by_name(tool_name)
        
        if not tool:
            return None
        
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": getattr(tool, "args_schema", None)
        }
    
    def get_tools_for_claude(self) -> List[Dict[str, Any]]:
        """
        Get tools formatted for Claude's API
        
        Returns:
            List of tools in Claude format
        """
        tools = self.client.get_all_tools()
        
        claude_tools = []
        for tool in tools:
            claude_tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.args_schema.schema() if hasattr(tool, "args_schema") else {}
            })
        
        return claude_tools
    
    # ========================================================================
    # TOOL VALIDATION
    # ========================================================================
    
    def validate_tool_arguments(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate tool arguments against schema
        
        Args:
            tool_name: Name of the tool
            arguments: Tool arguments to validate
        
        Returns:
            (is_valid, error_message)
        """
        tool = self.client.get_tool_by_name(tool_name)
        
        if not tool:
            return False, f"Tool not found: {tool_name}"
        
        try:
            # Tools with Pydantic schema have validation built-in
            if hasattr(tool, "args_schema"):
                tool.args_schema(**arguments)
            
            return True, None
            
        except Exception as e:
            return False, f"Invalid arguments: {str(e)}"
    
    # ========================================================================
    # TOOL CATEGORIZATION
    # ========================================================================
    
    def get_tools_by_category(self) -> Dict[str, List[str]]:
        """
        Categorize tools by server/functionality
        
        Returns:
            Dict mapping categories to tool lists
        """
        from app.mcp.config import MCPServerConfig
        
        categories = {}
        
        for server_name, config in MCPServerConfig.SERVERS.items():
            categories[server_name] = config.get("tools", [])
        
        return categories
    
    def get_recommended_tools(self, query: str) -> List[str]:
        """
        Get recommended tools based on user query
        
        Args:
            query: User's question
        
        Returns:
            List of recommended tool names
        """
        query_lower = query.lower()
        recommended = []
        
        # Simple keyword-based recommendation
        keywords_map = {
            "price": ["get_stock_info", "create_price_chart"],
            "fundamental": ["get_fundamentals", "get_financial_ratios", "get_valuation_metrics"],
            "technical": ["get_technical_indicators", "get_rsi", "get_macd"],
            "news": ["get_stock_news", "get_market_news", "get_sentiment_analysis"],
            "chart": ["create_candlestick_chart", "create_technical_chart"],
            "dividend": ["get_dividend_info"],
            "volume": ["get_volume_analysis", "create_volume_chart"],
            "comparison": ["create_comparison_chart"],
            "shareholding": ["get_shareholding_pattern", "get_promoter_holdings"]
        }
        
        for keyword, tools in keywords_map.items():
            if keyword in query_lower:
                recommended.extend(tools)
        
        return list(set(recommended))  # Remove duplicates


    def get_tools_for_openai(self) -> List[Dict[str, Any]]:
        """
        Convert MCP tools to OpenAI function calling format
        (openrouter uses the same format)
        
        Returns:
            List of tool definitions in OpenAI format
        """
        openai_tools = []
        
        for tool in self.client.get_all_tools():
            # Get the args schema
            args_schema = {}
            
            if hasattr(tool, 'args_schema'):
                schema = tool.args_schema
                
                #  FIX: args_schema can be either a Pydantic model or a dict
                if hasattr(schema, 'schema'):
                    # It's a Pydantic model
                    args_schema = schema.schema()
                elif isinstance(schema, dict):
                    # It's already a dict
                    args_schema = schema
                else:
                    # Try to convert to dict
                    try:
                        args_schema = schema.model_json_schema() if hasattr(schema, 'model_json_schema') else {}
                    except:
                        args_schema = {}
            
            # Convert to OpenAI format
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "No description available",
                    "parameters": args_schema
                }
            })
        
        return openai_tools





# ========================================================================
# GLOBAL INSTANCE
# ========================================================================

mcp_tool_handler = MCPToolHandler()

"""
MCP Client - MultiServerMCPClient wrapper
Manages connections to all 5 MCP servers
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.mcp.config import MCPServerConfig
from app.exceptions.custom_exceptions import (
    MCPException,
    MCPServerUnavailableException,
    MCPInitializationException
)

logger = logging.getLogger(__name__)


class KuberaMCPClient:
    """
    Wrapper around MultiServerMCPClient for KUBERA
    Manages connections to 5 MCP servers
    """
    
    def __init__(self):
        self.client: Optional[MultiServerMCPClient] = None
        self.tools: List[Any] = []
        self.named_tools: Dict[str, Any] = {}
        self.initialized = False
        self._lock = asyncio.Lock()
        self.server_status: Dict[str, bool] = {}  # Track server health
    
    # ========================================================================
    # INITIALIZATION
    # ========================================================================
    
    async def initialize(self) -> None:
        """
        Initialize MCP client and connect to all servers
        
        Raises:
            MCPInitializationException: If initialization fails
        """
        if self.initialized:
            logger.info("MCP Client already initialized")
            return
        
        async with self._lock:
            if self.initialized:
                return
            
            try:
                logger.info("Initializing KUBERA MCP Client...")
                
                # Get server configurations
                servers = MCPServerConfig.get_all_servers()
                
                logger.info(f"Connecting to {len(servers)} MCP servers...")
                
                # Create MultiServerMCPClient
                self.client = MultiServerMCPClient(servers)
                
                # Get all tools from all servers
                logger.info("Fetching tools from all servers...")
                self.tools = await self.client.get_tools()
                logger.info(f"Total tools available: {len(self.tools)}")
                # Create named tools dictionary
                self.named_tools = {}
                for tool in self.tools:
                    self.named_tools[tool.name] = tool
                
                self.initialized = True
                
                logger.info(f"MCP Client initialized successfully")
                logger.info(f"Total tools available: {len(self.tools)}")
                logger.info(f"Tools: {list(self.named_tools.keys())}")
                
            except Exception as e:
                logger.error(f"Failed to initialize MCP Client: {e}")
                raise MCPInitializationException(f"MCP initialization failed: {str(e)}")
    
    async def shutdown(self) -> None:
        """Shutdown MCP client and close all server connections"""
        if not self.initialized:
            return
        
        async with self._lock:
            try:
                logger.info("Shutting down MCP Client...")
                
                if self.client:
                    # MultiServerMCPClient handles cleanup internally
                    del self.client
                    self.client = None
                
                self.tools = []
                self.named_tools = {}
                self.server_status = {}
                self.initialized = False
                
                logger.info("MCP Client shutdown complete")
                
            except Exception as e:
                logger.error(f"Error during MCP shutdown: {e}")
    
    async def refresh_tools(self) -> int:
        """
        Refresh tools from all servers
        
        Returns:
            Number of tools loaded
        """
        if not self.initialized or not self.client:
            raise MCPException("MCP Client not initialized")
        
        try:
            logger.info("Refreshing tools from all servers...")
            
            self.tools = await self.client.get_tools()
            self.named_tools = {tool.name: tool for tool in self.tools}
            
            logger.info(f"Tools refreshed: {len(self.tools)} available")
            return len(self.tools)
            
        except Exception as e:
            logger.error(f"Error refreshing tools: {e}")
            raise MCPException(f"Failed to refresh tools: {str(e)}")
    
    # ========================================================================
    # TOOL OPERATIONS
    # ========================================================================
    
    def get_all_tools(self) -> List[Any]:
        """
        Get all available tools
        
        Returns:
            List of Langchain tools
        
        Raises:
            MCPException: If client not initialized
        """
        if not self.initialized:
            raise MCPException("MCP Client not initialized")
        
        return self.tools
    
    def get_tool_by_name(self, tool_name: str) -> Optional[Any]:
        """
        Get a specific tool by name
        
        Args:
            tool_name: Name of the tool
        
        Returns:
            Tool object or None
        """
        if not self.initialized:
            raise MCPException("MCP Client not initialized")
        
        return self.named_tools.get(tool_name)
    
    def get_tool_names(self) -> List[str]:
        """Get list of all tool names"""
        if not self.initialized:
            raise MCPException("MCP Client not initialized")
        
        return list(self.named_tools.keys())
    
    def get_tools_by_server(self, server_name: str) -> List[str]:
        """Get tool names for a specific server"""
        return MCPServerConfig.get_server_tools(server_name)
    
    # ========================================================================
    # TOOL INVOCATION
    # ========================================================================
    
    async def invoke_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        Invoke a tool with arguments and timeout
        
        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            timeout: Timeout in seconds (default: 60)
        
        Returns:
            Tool execution result
        
        Raises:
            MCPException: If tool not found, invocation fails, or timeout
        """
        if not self.initialized:
            raise MCPException("MCP Client not initialized")
        
        # Get tool
        tool = self.named_tools.get(tool_name)
        
        if not tool:
            raise MCPException(f"Tool not found: {tool_name}")
        
        try:
            logger.info(f"Invoking tool: {tool_name} with args: {arguments} (timeout: {timeout}s)")
            
            # Invoke tool with timeout
            result = await asyncio.wait_for(
                tool.ainvoke(arguments),
                timeout=timeout
            )
            
            logger.info(f"Tool {tool_name} executed successfully")
            
            return {
                "success": True,
                "tool": tool_name,
                "result": result
            }
        
        except asyncio.TimeoutError:
            logger.error(f"Tool {tool_name} timed out after {timeout}s")
            return {
                "success": False,
                "tool": tool_name,
                "error": f"Tool execution timed out after {timeout} seconds"
            }
            
        except Exception as e:
            logger.error(f"Error invoking tool {tool_name}: {e}")
            raise MCPException(f"Tool invocation failed: {str(e)}")
    
    async def invoke_multiple_tools(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Invoke multiple tools in parallel
        
        Args:
            tool_calls: List of {tool_name, arguments} dicts
        
        Returns:
            List of results
        """
        if not self.initialized:
            raise MCPException("MCP Client not initialized")
        
        tasks = []
        for call in tool_calls:
            tool_name = call.get("tool_name")
            arguments = call.get("arguments", {})
            
            task = self.invoke_tool(tool_name, arguments)
            tasks.append(task)
        
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "tool": tool_calls[i]["tool_name"],
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    # ========================================================================
    # HEALTH CHECK
    # ========================================================================
    
    def is_initialized(self) -> bool:
        """Check if client is initialized"""
        return self.initialized
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of MCP client"""
        return {
            "initialized": self.initialized,
            "total_tools": len(self.tools),
            "total_servers": len(MCPServerConfig.SERVERS),
            "tools_available": list(self.named_tools.keys()) if self.initialized else [],
            "server_status": self.server_status
        }
    
    async def health_check_servers(self) -> Dict[str, bool]:
        """
        Check health of all MCP servers
        
        Returns:
            Dict mapping server name to health status (True = healthy)
        """
        if not self.initialized:
            return {name: False for name in MCPServerConfig.SERVERS.keys()}
        
        status = {}
        
        for server_name in MCPServerConfig.SERVERS.keys():
            try:
                # Server is considered healthy if it contributed tools
                # Check if any tool name matches server prefix
                server_tools = [t for t in self.named_tools.keys() 
                               if server_name.replace('-', '_') in t.lower() or 
                               any(s in t.lower() for s in server_name.split('-'))]
                
                # If no tools from this server, mark as potentially unhealthy
                status[server_name] = len(server_tools) > 0 or len(self.tools) > 0
                
            except Exception as e:
                logger.warning(f"Health check failed for {server_name}: {e}")
                status[server_name] = False
        
        self.server_status = status
        
        # Log unhealthy servers
        unhealthy = [s for s, healthy in status.items() if not healthy]
        if unhealthy:
            logger.warning(f"Unhealthy MCP servers: {unhealthy}")
        
        return status


# ========================================================================
# GLOBAL INSTANCE
# ========================================================================

# Singleton instance
kubera_mcp_client = KuberaMCPClient()

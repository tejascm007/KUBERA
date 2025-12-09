"""
MCP Server Configurations
Defines all 5 MCP servers with their connection parameters
"""

import os
from typing import Dict, Any
from app.core.config import settings


class MCPServerConfig:
    """MCP Server Configuration"""
    
    # Base path for MCP servers
    MCP_SERVERS_PATH = os.path.join(os.getcwd(), "mcp_servers")
    
    # Python executable path
    PYTHON_EXECUTABLE = settings.PYTHON_EXECUTABLE or "python"
    
    # Server configurations
    SERVERS: Dict[str, Dict[str, Any]] = {
        # ====================================================================
        # SERVER 1: FINANCIAL DATA SERVER
        # ====================================================================
        "financial-data": {
            "transport": "stdio",
            "command": "uv",
            "args": ["run",
            "fastmcp",
            "run",os.path.join(MCP_SERVERS_PATH, "fin_data.py")],
            "env": None
        },
        
        # ====================================================================
        # SERVER 2: MARKET & TECHNICAL ANALYSIS SERVER
        # ====================================================================
        "market-technical": {
            "transport": "stdio",
            "command": "uv",
            "args": ["run",
            "fastmcp",
            "run",os.path.join(MCP_SERVERS_PATH, "market_tech.py")],
            "env": None
        },
        
        # ====================================================================
        # SERVER 3: GOVERNANCE & COMPLIANCE SERVER
        # ====================================================================
        "governance-compliance": {
            "transport": "stdio",
            "command": "uv",
            "args": ["run",
            "fastmcp",
            "run",os.path.join(MCP_SERVERS_PATH, "gov_compliance.py")],
            "env": None
        },
        
        # ====================================================================
        # SERVER 4: NEWS & SENTIMENT SERVER
        # ====================================================================
        "news-sentiment": {
            "transport": "stdio",
            "command": "uv",
            "args": ["run",
            "fastmcp",
            "run",os.path.join(MCP_SERVERS_PATH, "news_sent.py")],
            "env": None
        },
        
        # ====================================================================
        # SERVER 5: VISUALIZATION & CHARTING SERVER
        # ====================================================================
        "visualization": {
            "transport": "stdio",
            "command": "uv",
            "args": ["run",
            "fastmcp",
            "run",os.path.join(MCP_SERVERS_PATH, "visualization.py")],
            "env": None      
        }
    }
    
    @classmethod
    def get_server_config(cls, server_name: str) -> Dict[str, Any]:
        """Get configuration for a specific server"""
        return cls.SERVERS.get(server_name)
    
    @classmethod
    def get_all_servers(cls) -> Dict[str, Dict[str, Any]]:
        """Get all server configurations"""
        return cls.SERVERS
    
    @classmethod
    def get_server_tools(cls, server_name: str) -> list:
        """Get list of tools for a server"""
        server = cls.SERVERS.get(server_name)
        return server.get("tools", []) if server else []
    
    @classmethod
    def get_all_tool_names(cls) -> list:
        """Get all tool names across all servers"""
        all_tools = []
        for server in cls.SERVERS.values():
            all_tools.extend(server.get("tools", []))
        return all_tools

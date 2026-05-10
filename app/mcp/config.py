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
    
    @staticmethod
    def get_env() -> Dict[str, str]:
        """Get current environment variables to pass to MCP subprocesses"""
        return {key: value for key, value in os.environ.items()}
    
    # Server configurations
    SERVERS: Dict[str, Dict[str, Any]] = {
        "financial-data": {
            "transport": "stdio",
            "command": "uv",
            "args": ["run", "fastmcp", "run", os.path.join(MCP_SERVERS_PATH, "fin_data.py")],
            "env": None
        },
        "market-technical": {
            "transport": "stdio",
            "command": "uv",
            "args": ["run", "fastmcp", "run", os.path.join(MCP_SERVERS_PATH, "market_tech.py")],
            "env": None
        },
        "governance-compliance": {
            "transport": "stdio",
            "command": "uv",
            "args": ["run", "fastmcp", "run", os.path.join(MCP_SERVERS_PATH, "gov_compliance.py")],
            "env": None
        },
        "news-sentiment": {
            "transport": "stdio",
            "command": "uv",
            "args": ["run", "fastmcp", "run", os.path.join(MCP_SERVERS_PATH, "news_sent.py")],
            "env": None
        },
        "visualization": {
            "transport": "stdio",
            "command": "uv",
            "args": ["run", "fastmcp", "run", os.path.join(MCP_SERVERS_PATH, "visualization.py")],
            "env": None
        }
    }
    
    @classmethod
    def get_all_servers(cls) -> Dict[str, Dict[str, Any]]:
        """Get all server configurations with current env vars injected"""
        env = cls.get_env()
        servers = {}
        for name, config in cls.SERVERS.items():
            servers[name] = {**config, "env": env}
        return servers

    @classmethod
    def get_server_config(cls, server_name: str) -> Dict[str, Any]:
        """Get configuration for a specific server with env vars injected"""
        server = cls.SERVERS.get(server_name)
        if server:
            return {**server, "env": cls.get_env()}
        return None
    
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
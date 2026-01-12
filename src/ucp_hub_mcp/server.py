
from mcp.server.fastmcp import FastMCP
from ucp_hub_mcp.client import UCPClient
from ucp_hub_mcp.registry import ToolRegistry
from ucp_hub_mcp.tools.search import ToolSearchTool
from ucp_hub_mcp.tools.code_execution import CodeExecutionTool

# Initialize FastMCP Server
mcp = FastMCP("UCP-to-MCP Hub")

# Global State
registry = ToolRegistry()
search_tool = ToolSearchTool(registry)
code_tool = CodeExecutionTool(registry)

@mcp.tool(name="tool_search")
async def search_tools(regex: str) -> list[dict]:
    """
    Search for tools by name using regular expressions. 
    Returns a list of matching tool definitions.
    """
    return await search_tool.execute({"regex": regex})

@mcp.tool()
async def refresh_ucp_discovery(url: str = "http://localhost:8182") -> str:
    """
    Triggers a fresh discovery against the UCP Merchant URL.
    This populates the internal registry with deferred tools.
    """
    client = UCPClient()
    try:
        profile = client.discover_services(url)
        registry.register_from_profile(profile)
        count = len(registry._deferred_tools)
        return f"Successfully discovered {count} capabilities from {url}. They are now available via tool search."
    except Exception as e:
        return f"Discovery failed: {e}"

@mcp.tool(name="execute_python")
async def execute_python(code: str) -> str:
    """
    Executes a Python script to orchestrate UCP capabilities.
    The script has access to a 'ucp' object with methods like 
    await ucp.discover(url) and await ucp.call(tool_name, **kwargs).
    """
    return await code_tool.execute({"code": code})

def main():
    """Entry point for the MCP Server."""
    mcp.run()

if __name__ == "__main__":
    main()

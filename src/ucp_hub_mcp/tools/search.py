

from typing import Any
from mcp.types import Tool
from ..registry import ToolRegistry

class ToolSearchTool:
    """
    Implements the 'tool_search_tool_regex_20251119' standard.
    Allows the agent to search for deferred tools using regex.
    """
    
    TOOL_NAME = "tool_search"
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    @property
    def definition(self) -> Tool:
        return Tool(
            name=self.TOOL_NAME,
            description="Search for tools by name using regular expressions. Returns a list of matching tool definitions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "regex": {
                        "type": "string",
                        "description": "Regular expression to match tool names"
                    }
                },
                "required": ["regex"]
            }
        )

    async def execute(self, arguments: dict) -> list[Any]:
        regex = arguments.get("regex")
        if not regex:
            return []
            
        matches = self.registry.search_tools(regex)
        return matches

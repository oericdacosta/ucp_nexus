
from typing import Any
from mcp.types import Tool
from ..sandbox import Sandbox
from ..registry import ToolRegistry

class CodeExecutionTool:
    """
    Implements the 'execute_python' tool for programmatic orchestration.
    """
    
    TOOL_NAME = "execute_python"
    
    def __init__(self, registry: ToolRegistry):
        self.sandbox = Sandbox(registry)

    @property
    def definition(self) -> Tool:
        return Tool(
            name=self.TOOL_NAME,
            description="Executes a Python script to orchestrate UCP capabilities. " 
                        "The script has access to a 'ucp' object with methods like "
                        "await ucp.discover(url) and await ucp.call(tool_name, **kwargs).",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute. Must be valid Python syntax."
                    }
                },
                "required": ["code"]
            }
        )

    async def execute(self, arguments: dict) -> str:
        code = arguments.get("code")
        if not code:
            return "Error: No code provided."
            
        result = await self.sandbox.run(code)
        return result

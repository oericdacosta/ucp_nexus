
import asyncio
import sys
from typing import Any, Dict, Optional
from ucp_hub_mcp.client import UCPClient
from ucp_hub_mcp.registry import ToolRegistry

class UCPProxy:
    """
    A safe proxy object injected into the Sandbox.
    Allows the agent to interact with UCP without accessing internal Hub state.
    """
    def __init__(self, registry: ToolRegistry):
        self._client = UCPClient()
        self._registry = registry

    async def discover(self, url: str) -> list[dict]:
        """
        Discovers services at the given URL and returns a list of capability descriptors.
        Also registers them in the Hub's registry (Deferred Loading).
        """
        profile = self._client.discover_services(url)
        self._registry.register_from_profile(profile)
        
        # Return a simplified list of what was found for the agent's logic
        results = []
        if profile.ucp and profile.ucp.capabilities:
            for cap in profile.ucp.capabilities:
                results.append({
                    "name": cap.name,
                    "spec": str(cap.spec) if cap.spec else None,
                    "version": cap.version
                })
        return results

    async def call(self, tool_name: str, **kwargs) -> Any:
        """
        Executes a UCP capability (Tool).
        In a real implementation, this would translate the Python call to an HTTP/MCP request 
        against the merchant server. For Phase 3 Verification, we might mock this or 
        implement rudimentary logic if needed.
        """
        print(f"[UCPProxy] Calling tool: {tool_name} with args: {kwargs}")
        
        # Check if tool exists in registry
        tool_def = self._registry.get_tool(tool_name)
        if not tool_def:
            raise ValueError(f"Tool '{tool_name}' not found. Did you run discover()?")
            
        return {"status": "executed", "tool": tool_name, "result": "mock_result_phase_3"}

class Sandbox:
    """
    An asyncio-aware sandbox for executing untrusted Python code.
    """
    def __init__(self, registry: ToolRegistry):
        self.proxy = UCPProxy(registry)

    async def run(self, code: str) -> str:
        """
        Executes the provided Python code string in a restricted environment.
        """
        
        # Capture stdout to return it to the LLM
        from io import StringIO
        import contextlib
        
        output_buffer = StringIO()
        
        # Restricted Globals
        # We inject 'ucp' as the main entry point
        # We also support 'print' to capture output
        safe_globals = {
            "ucp": self.proxy,
            "print": print,
            "__builtins__": {
                "print": print,
                "len": len,
                "range": range,
                "min": min,
                "max": max,
                "list": list,
                "dict": dict,
                "set": set,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                # Add others as needed, but keep 'import' and 'open' out!
            }
        }
        
        # Wrap user code in an async function to allow 'await'
        # Indent code by 4 spaces
        indented_code = "\n".join("    " + line for line in code.splitlines())
        wrapped_code = f"async def _agent_script():\n{indented_code}"
        
        try:
            with contextlib.redirect_stdout(output_buffer):
                # 1. Compile and Execution Definition
                exec(wrapped_code, safe_globals)
                
                # 2. Execute the function
                _agent_script = safe_globals["_agent_script"]
                await _agent_script()
                
            return output_buffer.getvalue()
            
        except Exception as e:
            return f"Runtime Error: {e}"

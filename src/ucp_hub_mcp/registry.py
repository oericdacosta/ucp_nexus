
from typing import Dict, List, Optional
from ucp_sdk.models.discovery.profile_schema import UcpDiscoveryProfile
from ucp_sdk.models._internal import Discovery

class ToolRegistry:
    """
    Manages UCP capabilities with a Deferred Loading strategy.
    
    Stores tool definitions in memory but only exposes them when explicitly 
    searched for or requested, implementing the Anthropic "Progressive Disclosure" pattern.
    """
    
    def __init__(self):
        self._deferred_tools: Dict[str, Discovery] = {}
        self._loaded_tools: Dict[str, Discovery] = {}

    def register_from_profile(self, profile: UcpDiscoveryProfile):
        """
        Ingests a UCP Discovery Profile and registers all capabilities as deferred.
        """
        if profile.ucp and profile.ucp.capabilities:
            for cap in profile.ucp.capabilities:
                # Store by name (e.g., 'dev.ucp.shopping.checkout')
                self._deferred_tools[cap.name] = cap

    def search_tools(self, query_regex: str) -> List[dict]:
        """
        Searches deferred tools by name using regex match.
        Returns a list of simplified tool definitions (JSON schemas).
        """
        import re
        results = []
        pattern = re.compile(query_regex, re.IGNORECASE)
        
        for name, cap in self._deferred_tools.items():
            if pattern.search(name):
                # We return the tool definition.
                # Since 'cap' is a Pydantic model (Capabilities), we dump it to dict.
                
                tool_def = {
                    "name": cap.name,
                    "description": f"UCP Capability: {cap.name} (Spec: {cap.spec})",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "payload": {"type": "object"}
                        }
                    }
                }
                results.append(tool_def)
                
        return results

    def get_tool(self, name: str) -> Optional[dict]:
        """
        Retrieves a specific tool definition by name, marking it as loaded.
        """
        cap = self._deferred_tools.get(name)
        if not cap:
            return None
            
        # Move to loaded (conceptually, though for search we keep it available)
        self._loaded_tools[name] = cap
        
        return {
            "name": cap.name,
            "description": f"UCP Capability: {cap.name}",
            "input_schema": {
                "type": "object",
                "properties": {"payload": {"type": "object"}}
            }
        }

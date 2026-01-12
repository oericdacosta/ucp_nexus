
from typing import Any
from ucp_hub_mcp.client import UCPClient
from ucp_hub_mcp.registry import ToolRegistry
from ucp_hub_mcp.security import AP2Security, KeyManager
from .config import settings

class UCPProxy:
    """
    A safe proxy object injected into the Sandbox.
    Allows the agent to interact with UCP without accessing internal Hub state.
    """
    def __init__(self, registry: ToolRegistry):
        self._client = UCPClient()
        self._registry = registry
        self._security = AP2Security()
        self._key_manager = KeyManager()
        self._discovered_payment_handlers = []
        self._last_discovery_url = settings.ucp_server_url

    async def discover(self, url: str) -> list[dict]:
        """
        Discovers services at the given URL and returns a list of capability descriptors.
        Also registers them in the Hub's registry (Deferred Loading).
        """
        profile = self._client.discover_services(url)
        self._last_discovery_url = url.rstrip("/")
        self._registry.register_from_profile(profile)
        
        # Store payment handlers from Phase 4
        if profile.payment and profile.payment.handlers:
            self._discovered_payment_handlers = profile.payment.handlers
        
        # Return a simplified list of what was found for the agent's logic
        results = []
        if profile.ucp and profile.ucp.capabilities:
            for cap in profile.ucp.capabilities:
                results.append({
                    "name": cap.name,
                    "spec": str(cap.spec) if cap.spec else None,
                    "version": str(cap.version)
                })
        return results

    async def select_payment_method(self, method_name: str, amount: float = 0.0, currency: str = "BRL") -> dict:
        """
        Selects a payment method and generates an AP2 security mandate.
        Returns a payment token to be used in checkout.
        """
        import uuid
        
        # Generate Security Mandate (JWT)
        mandate_jwt = self._security.create_mandate(amount, currency, beneficiary="merchant-id")
        
        print(f"[UCPProxy] Generated AP2 Mandate for {amount} {currency} via {method_name}")
        
        return {
            "token": f"pay_{uuid.uuid4().hex[:24]}", # Unique Payment Provider Token
            "mandate": mandate_jwt,
            "method": method_name
        }

    def _resolve_endpoint(self, tool_name: str) -> str:
        """Resolves the UCP endpoint path for a given tool name."""
        return settings.endpoint_map.get(tool_name)

    def _get_conformance_headers(self, payload_str: str = "") -> dict:
        """Generates standard UCP Conformance headers with Ed25519 signature."""
        import uuid
        import time
        
        # Security Headers
        request_id = str(uuid.uuid4())
        idempotency_key = str(uuid.uuid4())
        timestamp = str(int(time.time()))
        nonce = uuid.uuid4().hex[:16]
        
        # Signing Input: Timestamp + Nonce + Payload (prevent replay & tampering)
        signing_input = f"{timestamp}.{nonce}.{payload_str}"
        signature = self._key_manager.sign(signing_input)
        
        return {
            "request-id": request_id,
            "idempotency-key": idempotency_key,
            "ucp-timestamp": timestamp,
            "ucp-nonce": nonce,
            "request-signature": signature,
            "ucp-key-id": self._key_manager.key_id
        }

    async def call(self, tool_name: str, **kwargs) -> Any:
        """
        Executes a UCP capability (Tool) using real HTTP transport against the discovered URL.
        Orchestrates resolution, headers, and request dispatch.
        """
        print(f"[UCPProxy] Calling tool: {tool_name}")
        if not self._last_discovery_url:
            raise RuntimeError("You must call 'await ucp.discover(url)' before calling capabilities.")

        endpoint_path = self._resolve_endpoint(tool_name)
        if not endpoint_path:
             raise ValueError(f"Tool '{tool_name}' is not currently mapped to a supported endpoint.")

        base_url = self._last_discovery_url
        full_url = f"{base_url}{endpoint_path}"
        
        # Dispatch request logic
        return self._dispatch_request(full_url, kwargs)

    def _dispatch_request(self, url: str, kwargs: dict) -> dict:
        """Handles the HTTP request logic based on the operation type."""
        import json
        
        checkout_id = kwargs.get("id")
        action = kwargs.pop("_action", None)
        client = self._client.client
        
        # Prepare payload and headers
        payload = kwargs
        if action == "complete":
             payload = kwargs.get("payment", kwargs)
        
        # Canonical serialization for signing
        # sort_keys=True ensures deterministic hashing/signing
        payload_str = json.dumps(payload, sort_keys=True)
        headers = self._get_conformance_headers(payload_str)

        try:
            if not checkout_id:
                # CREATE
                print(f"[UCPProxy] Transport: POST {url}")
                # We use content=payload_str to ensure byte-level match with signature
                resp = client.post(url, content=payload_str, headers=headers)
            elif action == "complete":
                # COMPLETE
                complete_url = f"{url}/{checkout_id}/complete"
                print(f"[UCPProxy] Transport: POST {complete_url}")
                resp = client.post(complete_url, content=payload_str, headers=headers)
            else:
                # UPDATE
                update_url = f"{url}/{checkout_id}"
                print(f"[UCPProxy] Transport: PUT {update_url}")
                resp = client.put(update_url, content=payload_str, headers=headers)
            
            resp.raise_for_status()
            return {"result": resp.json()}

        except Exception as e:
            self._handle_http_error(e)
            
    def _handle_http_error(self, e: Exception) -> None:
        """Formats and re-raises HTTP errors with detail."""
        print(f"[UCPProxy] HTTP Error: {e}")
        error_msg = str(e)
        if hasattr(e, "response") and e.response:
             detail = e.response.text
             print(f"Server Response: {detail}")
             error_msg += f" | Details: {detail}"
        raise Exception(error_msg) from e


class Sandbox:
    """
    An asyncio-aware sandbox for executing untrusted Python code.
    Allows for configuration of allowed globals (Open/Closed Principle).
    """
    def __init__(self, registry: ToolRegistry, additional_globals: dict = None):
        self.proxy = UCPProxy(registry)
        self.safe_globals = self._build_safe_globals(additional_globals)

    def _build_safe_globals(self, additional_globals: dict = None) -> dict:
        """Constructs the restricted global environment."""
        import importlib
        
        base_globals = {
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
                "next": next,
            }
        }
        
        # Dynamic import of allowed modules from config
        for module_name in settings.sandbox_globals:
             try:
                 mod = importlib.import_module(module_name)
                 base_globals[module_name] = mod
             except ImportError:
                 print(f"Warning: Configured sandbox module '{module_name}' could not be imported.")

        if additional_globals:
            # Securely merge allowed globals.
            # We explicitly prevent overriding __builtins__ via the top-level dictionary
            # to ensure the sandbox restrictions remain intact.
            safe_additions = additional_globals.copy()
            if "__builtins__" in safe_additions:
                # If extending builtins is required, it must be done explicitly here
                # For production safety, we simply ignore external __builtins__ overrides
                del safe_additions["__builtins__"]
            
            base_globals.update(safe_additions)
            
        return base_globals

    async def run(self, code: str) -> str:
        """
        Executes the provided Python code string in a restricted environment.
        """
        from io import StringIO
        import contextlib
        
        output_buffer = StringIO()
        
        # Wrap user code in an async function to allow 'await'
        # Indent code by 4 spaces
        indented_code = "\n".join("    " + line for line in code.splitlines())
        wrapped_code = f"async def _agent_script():\n{indented_code}"
        
        try:
            with contextlib.redirect_stdout(output_buffer):
                # 1. Compile and Execution Definition
                exec(wrapped_code, self.safe_globals)
                
                # 2. Execute the function
                _agent_script = self.safe_globals["_agent_script"]
                await _agent_script()
                
            return output_buffer.getvalue()
            
        except Exception as e:
            return f"{output_buffer.getvalue()}\nRuntime Error: {e}"

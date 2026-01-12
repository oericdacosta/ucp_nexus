
import httpx
from pydantic import ValidationError
from ucp_sdk.models.discovery.profile_schema import UcpDiscoveryProfile
from .exceptions import UCPDiscoveryError, UCPConformanceError


from .config import settings


class UCPClient:
    """Client for interacting with UCP Servers."""

    def __init__(self, timeout: float = None, agent_profile: str = "default-hub-profile"):
        if timeout is None:
            timeout = settings.http_timeout
        self.headers = {"UCP-Agent": f"profile={agent_profile}"}
        self.client = httpx.Client(timeout=timeout, headers=self.headers)

    def discover_services(self, url: str) -> UcpDiscoveryProfile:
        """
        Discovers capabilities from a UCP server.

        Args:
            url: The base URL of the merchant server (e.g. http://localhost:8182).

        Returns:
            UcpDiscoveryProfile: The validated discovery response from the server.

        Raises:
            UCPDiscoveryError: If the server cannot be reached or returns an error.
            UCPConformanceError: If the server response does not match UCP specs.
        """
        # Strip trailing slash to ensure clean path concatenation for the specific discovery endpoint.
        base_url = url.rstrip("/")
        discovery_url = f"{base_url}/.well-known/ucp"

        try:
            response = self.client.get(discovery_url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise UCPDiscoveryError(f"Failed to fetch discovery info from {discovery_url}: {e}") from e

        try:
            # Validate against the official SDK model
            payload = response.json()
            model = UcpDiscoveryProfile(**payload)

            return model

        except ValidationError as e:
            raise UCPConformanceError(f"Server response violated UCP Schema: {e}") from e
        except Exception as e:
            raise UCPDiscoveryError(f"Unexpected error parsing discovery response: {e}") from e

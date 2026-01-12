
import base64
import json
import time
from typing import Dict, Any

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from .config import settings

class KeyManager:
    """
    Manages cryptographic keys for the Hub using Ed25519 (RFC 8032).
    """
    def __init__(self):
        # Generate Ed25519 private key
        self._private_key = ed25519.Ed25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()
        
        # Generate a stable ID for this key
        public_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        self.key_id = f"hub-key-{base64.urlsafe_b64encode(public_bytes[:8]).decode().rstrip('=')}"

    def sign(self, payload: str) -> str:
        """
        Signs the payload bytes using Ed25519.
        """
        signature = self._private_key.sign(payload.encode("utf-8"))
        return base64.urlsafe_b64encode(signature).decode().rstrip("=")
        
    def get_public_jwk(self) -> Dict[str, Any]:
        """
        Returns the public key in JWK format according to RFC 8037.
        """
        public_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        x_coord = base64.urlsafe_b64encode(public_bytes).decode().rstrip("=")
        
        return {
            "kty": "OKP",
            "crv": "Ed25519",
            "x": x_coord,
            "kid": self.key_id
        }

class AP2Security:
    """
    Handles AP2 (Autonomous Payment Protocol) security mandates.
    """
    def __init__(self):
        self.key_manager = KeyManager()

    def create_mandate(self, amount: float, currency: str, beneficiary: str) -> str:
        """
        Creates a signed JWT mandate authorizing a specific transaction.
        """
        header = {
            "alg": "EdDSA",
            "typ": "JWT",
            "kid": self.key_manager.key_id
        }
        
        payload = {
            "iss": "ucp-hub-mcp",
            "sub": "agent-autonomous-action",
            "aud": beneficiary,
            "exp": int(time.time()) + settings.jwt_expiry_seconds,

            "scope": "ucp:payment",
            "mandate": {
                "max_amount": amount,
                "currency": currency
            }
        }
        
        # Base64url encoding without padding
        b64_header = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        b64_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        
        # Sign header.payload
        signing_input = f"{b64_header}.{b64_payload}"
        signature = self.key_manager.sign(signing_input)
        
        return f"{signing_input}.{signature}"

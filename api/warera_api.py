"""
WarEra API compatibility wrapper.
Delegates to the unified WarEraClient.
"""

from warera_client import WarEraClient, get_warera_client

class WarEraAPI(WarEraClient):
    """Backwards-compatible subclass of WarEraClient."""
    pass

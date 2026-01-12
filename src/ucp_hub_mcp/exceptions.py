
class UCPError(Exception):
    """Base exception for UCP Hub."""
    pass


class UCPDiscoveryError(UCPError):
    """Raised when discovery of UCP services fails."""
    pass


class UCPConformanceError(UCPError):
    """Raised when UCP response does not conform to expected schema."""
    pass

"""Official Python SDK for the Resimi SMM panel API v2 (https://resimismm.com)."""

from ._version import __version__
from .client import ResimiClient
from .exceptions import ResimiAPIError, ResimiAuthError, ResimiError

__author__ = "Resimi"

__all__ = [
    "ResimiClient",
    "ResimiError",
    "ResimiAPIError",
    "ResimiAuthError",
    "__version__",
]

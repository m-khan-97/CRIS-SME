# Provider adapter exports for normalizing cloud-specific posture into CRIS-SME core models.
from .aws_adapter import AwsProfileAdapter
from .base import ProviderProfileAdapter
from .gcp_adapter import GcpProfileAdapter
from .registry import get_profile_adapter

__all__ = [
    "AwsProfileAdapter",
    "GcpProfileAdapter",
    "ProviderProfileAdapter",
    "get_profile_adapter",
]

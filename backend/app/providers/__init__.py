from .base import BaseCloudConnector
from .aws.connector import AWSConnector
from .azure.connector import AzureConnector
from .gcp.connector import GCPConnector

_CONNECTORS: dict[str, BaseCloudConnector] = {
    "AWS": AWSConnector(),
    "AZURE": AzureConnector(),
    "GCP": GCPConnector(),
}

def get_cloud_connector(provider: str) -> BaseCloudConnector:
    """
    Factory returning the connector adapter for the specified cloud provider.
    """
    clean_provider = provider.upper().strip()
    if clean_provider not in _CONNECTORS:
        raise ValueError(f"Unsupported cloud provider '{provider}'. Supported providers: AWS, AZURE, GCP.")
    return _CONNECTORS[clean_provider]

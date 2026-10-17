from abc import ABC, abstractmethod
from typing import Any

class BaseCloudConnector(ABC):
    """
    Abstract base class for enterprise multi-cloud connectors.
    Provides structural credential validation, credential masking,
    and normalized billing data synchronization.
    """
    provider_name: str

    @abstractmethod
    def validate_credentials(
        self, credentials: dict[str, Any], auth_type: str = "DEFAULT"
    ) -> tuple[bool, str | None, dict[str, Any]]:
        """
        Validates the structure, format, and identifiers of provider credentials.
        Returns (is_valid, error_message, masked_credentials).
        """
        ...

    @abstractmethod
    def generate_sync_records(
        self,
        account_id: str,
        account_identifier: str,
        region: str,
        days: int = 30,
        organization_id: str = "org-default",
    ) -> list[dict[str, Any]]:
        """
        Generates or ingests normalized CostRecord payloads.
        Returns list of dicts with:
        provider, service, region, amount, recorded_at, resource_id, currency.
        """
        ...

    def mask_value(self, val: str | None, visible_chars: int = 4) -> str:
        if not val or not isinstance(val, str):
            return "****"
        if len(val) <= visible_chars * 2:
            return "****" + val[-visible_chars:]
        return val[:visible_chars] + "****" + val[-visible_chars:]

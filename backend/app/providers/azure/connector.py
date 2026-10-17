import re
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Any
from ..base import BaseCloudConnector

AZURE_VALID_REGIONS = {
    "eastus", "eastus2", "westus", "westus2", "centralus",
    "westeurope", "northeurope", "uksouth", "ukwest",
    "southeastasia", "eastasia", "australiaeast", "japaneast"
}

def is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError, TypeError):
        return False

class AzureConnector(BaseCloudConnector):
    provider_name = "Azure"

    def validate_credentials(
        self, credentials: dict[str, Any], auth_type: str = "SERVICE_PRINCIPAL"
    ) -> tuple[bool, str | None, dict[str, Any]]:
        clean_auth = (auth_type or "SERVICE_PRINCIPAL").upper()
        if clean_auth != "SERVICE_PRINCIPAL":
            return False, f"Unsupported Azure auth type '{auth_type}'. Allowed: 'SERVICE_PRINCIPAL'.", {}

        tenant_id = str(credentials.get("tenant_id", "")).strip()
        client_id = str(credentials.get("client_id", "")).strip()
        subscription_id = str(credentials.get("subscription_id", "")).strip()
        client_secret = str(credentials.get("client_secret", "")).strip()

        if not tenant_id:
            return False, "Azure Tenant ID is required.", {}
        if not is_valid_uuid(tenant_id):
            return False, "Invalid Azure Tenant ID format. Must be a valid UUID.", {}

        if not client_id:
            return False, "Azure Client ID (App ID) is required.", {}
        if not is_valid_uuid(client_id):
            return False, "Invalid Azure Client ID format. Must be a valid UUID.", {}

        if not subscription_id:
            return False, "Azure Subscription ID is required.", {}
        if not is_valid_uuid(subscription_id):
            return False, "Invalid Azure Subscription ID format. Must be a valid UUID.", {}

        if not client_secret or len(client_secret) < 8:
            return False, "Azure Client Secret is required (minimum 8 characters).", {}

        masked = {
            "auth_type": "SERVICE_PRINCIPAL",
            "tenant_id": self.mask_value(tenant_id, visible_chars=8),
            "client_id": self.mask_value(client_id, visible_chars=8),
            "subscription_id": self.mask_value(subscription_id, visible_chars=8),
            "client_secret": "****************",
        }
        return True, None, masked

    def generate_sync_records(
        self,
        account_id: str,
        account_identifier: str,
        region: str,
        days: int = 30,
        organization_id: str = "org-default",
    ) -> list[dict[str, Any]]:
        services = ["Virtual Machines", "Storage Accounts", "SQL Database", "App Service", "Virtual Network"]
        records: list[dict[str, Any]] = []
        now = datetime.utcnow()

        seed_base = int(hashlib.md5(f"{account_identifier}-{region}".encode()).hexdigest(), 16) % 1000

        for d in range(days):
            record_date = now - timedelta(days=days - 1 - d)
            for idx, service in enumerate(services):
                factor = ((seed_base + idx * 43 + d * 17) % 100) / 100.0
                base_amt = 12.0 + (idx * 20.0) + (factor * 25.0)
                amount = round(base_amt, 2)
                res_id = f"az-{service.lower().replace(' ', '-')[:8]}-{account_identifier[-4:] if len(account_identifier)>=4 else '001'}-{idx+1:02}"

                records.append({
                    "organization_id": organization_id,
                    "account_id": account_id,
                    "provider": "AZURE",
                    "service": service,
                    "region": region if region in AZURE_VALID_REGIONS else "eastus",
                    "amount": amount,
                    "currency": "USD",
                    "resource_id": res_id,
                    "recorded_at": record_date,
                    "source": "CONNECTOR_SYNC_SIMULATED",
                })
        return records

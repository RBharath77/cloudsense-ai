import re
import hashlib
from datetime import datetime, timedelta
from typing import Any
from ..base import BaseCloudConnector

GCP_VALID_REGIONS = {
    "us-central1", "us-east1", "us-east4", "us-west1", "us-west2",
    "europe-west1", "europe-west3", "europe-west4",
    "asia-east1", "asia-northeast1", "asia-southeast1", "australia-southeast1"
}

GCP_PROJECT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
GCP_SA_EMAIL_PATTERN = re.compile(r"^[\w.-]+@[\w.-]+\.iam\.gserviceaccount\.com$")

class GCPConnector(BaseCloudConnector):
    provider_name = "GCP"

    def validate_credentials(
        self, credentials: dict[str, Any], auth_type: str = "SERVICE_ACCOUNT"
    ) -> tuple[bool, str | None, dict[str, Any]]:
        clean_auth = (auth_type or "SERVICE_ACCOUNT").upper()
        if clean_auth != "SERVICE_ACCOUNT":
            return False, f"Unsupported GCP auth type '{auth_type}'. Allowed: 'SERVICE_ACCOUNT'.", {}

        project_id = str(credentials.get("project_id", "")).strip()
        client_email = str(credentials.get("client_email", "")).strip()
        private_key = str(credentials.get("private_key", "")).strip()

        if not project_id:
            return False, "Google Cloud Project ID is required.", {}
        if not GCP_PROJECT_ID_PATTERN.match(project_id):
            return False, "Invalid GCP Project ID format. Must be 6-30 lowercase characters and hyphens, starting with a letter.", {}

        if not client_email:
            return False, "Google Service Account email is required.", {}
        if not GCP_SA_EMAIL_PATTERN.match(client_email):
            return False, "Invalid Google Service Account email. Must follow '<account-name>@<project-id>.iam.gserviceaccount.com'.", {}

        if not private_key or len(private_key) < 20:
            return False, "Google Cloud Service Account Private Key is required.", {}

        masked = {
            "auth_type": "SERVICE_ACCOUNT",
            "project_id": project_id,
            "client_email": self.mask_value(client_email, visible_chars=8),
            "private_key": "-----BEGIN PRIVATE KEY-----\n****************\n-----END PRIVATE KEY-----",
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
        services = ["Compute Engine", "Cloud Storage", "BigQuery", "GKE", "Cloud Run"]
        records: list[dict[str, Any]] = []
        now = datetime.utcnow()

        seed_base = int(hashlib.md5(f"{account_identifier}-{region}".encode()).hexdigest(), 16) % 1000

        for d in range(days):
            record_date = now - timedelta(days=days - 1 - d)
            for idx, service in enumerate(services):
                factor = ((seed_base + idx * 29 + d * 19) % 100) / 100.0
                base_amt = 10.0 + (idx * 22.0) + (factor * 28.0)
                amount = round(base_amt, 2)
                res_id = f"gcp-{service.lower().replace(' ', '-')[:8]}-{account_identifier[-4:] if len(account_identifier)>=4 else '001'}-{idx+1:02}"

                records.append({
                    "organization_id": organization_id,
                    "account_id": account_id,
                    "provider": "GCP",
                    "service": service,
                    "region": region if region in GCP_VALID_REGIONS else "us-central1",
                    "amount": amount,
                    "currency": "USD",
                    "resource_id": res_id,
                    "recorded_at": record_date,
                    "source": "CONNECTOR_SYNC_SIMULATED",
                })
        return records

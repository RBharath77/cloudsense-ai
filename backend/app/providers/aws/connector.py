import re
import hashlib
from datetime import datetime, timedelta
from typing import Any
from ..base import BaseCloudConnector

AWS_VALID_REGIONS = {
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "ca-central-1", "eu-west-1", "eu-central-1", "eu-west-2",
    "ap-southeast-1", "ap-southeast-2", "ap-northeast-1", "ap-south-1",
    "sa-east-1"
}

AWS_ROLE_ARN_PATTERN = re.compile(r"^arn:aws:iam::\d{12}:role/[\w+=,.@-]{1,64}$")
AWS_ACCESS_KEY_PATTERN = re.compile(r"^AKIA[0-9A-Z]{16}$")

class AWSConnector(BaseCloudConnector):
    provider_name = "AWS"

    def validate_credentials(
        self, credentials: dict[str, Any], auth_type: str = "ROLE_ARN"
    ) -> tuple[bool, str | None, dict[str, Any]]:
        clean_auth = (auth_type or "ROLE_ARN").upper()
        masked: dict[str, Any] = {"auth_type": clean_auth}

        if clean_auth == "ROLE_ARN":
            role_arn = credentials.get("role_arn", "").strip()
            external_id = credentials.get("external_id", "").strip()

            if not role_arn:
                return False, "AWS IAM Role ARN is required.", {}
            if not AWS_ROLE_ARN_PATTERN.match(role_arn):
                return False, "Invalid AWS IAM Role ARN format. Must follow 'arn:aws:iam::<12-digit-account-id>:role/<role-name>'.", {}
            if not external_id:
                return False, "AWS External ID is required for secure multi-tenant role assumption.", {}
            if len(external_id) < 2 or len(external_id) > 64:
                return False, "AWS External ID must be between 2 and 64 characters.", {}

            masked["role_arn"] = self.mask_value(role_arn, visible_chars=12)
            masked["external_id"] = self.mask_value(external_id, visible_chars=3)
            return True, None, masked

        elif clean_auth == "ACCESS_KEY":
            access_key_id = credentials.get("access_key_id", "").strip()
            secret_key = credentials.get("secret_access_key", "").strip()

            if not access_key_id:
                return False, "AWS Access Key ID is required.", {}
            if not AWS_ACCESS_KEY_PATTERN.match(access_key_id):
                return False, "Invalid AWS Access Key ID. Must start with 'AKIA' followed by 16 alphanumeric characters.", {}
            if not secret_key or len(secret_key) < 20:
                return False, "Invalid AWS Secret Access Key. Must be at least 20 characters.", {}

            masked["access_key_id"] = self.mask_value(access_key_id, visible_chars=6)
            masked["secret_access_key"] = "****************"
            return True, None, masked

        else:
            return False, f"Unsupported AWS auth type '{auth_type}'. Allowed: 'ROLE_ARN' or 'ACCESS_KEY'.", {}

    def generate_sync_records(
        self,
        account_id: str,
        account_identifier: str,
        region: str,
        days: int = 30,
        organization_id: str = "org-default",
    ) -> list[dict[str, Any]]:
        services = ["EC2", "S3", "RDS", "Lambda", "CloudFront"]
        records: list[dict[str, Any]] = []
        now = datetime.utcnow()

        seed_base = int(hashlib.md5(f"{account_identifier}-{region}".encode()).hexdigest(), 16) % 1000

        for d in range(days):
            record_date = now - timedelta(days=days - 1 - d)
            for idx, service in enumerate(services):
                factor = ((seed_base + idx * 37 + d * 13) % 100) / 100.0
                base_amt = 15.0 + (idx * 25.0) + (factor * 30.0)
                amount = round(base_amt, 2)
                res_id = f"aws-{service.lower()}-{account_identifier[-4:] if len(account_identifier)>=4 else '001'}-{idx+1:02}"

                records.append({
                    "organization_id": organization_id,
                    "account_id": account_id,
                    "provider": "AWS",
                    "service": service,
                    "region": region if region in AWS_VALID_REGIONS else "us-east-1",
                    "amount": amount,
                    "currency": "USD",
                    "resource_id": res_id,
                    "recorded_at": record_date,
                    "source": "CONNECTOR_SYNC_SIMULATED",
                })
        return records

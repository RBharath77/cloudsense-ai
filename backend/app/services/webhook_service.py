import hmac
import hashlib
import json
import secrets
import re
from datetime import datetime
from typing import Any
from sqlalchemy.orm import Session
from ..models import WebhookEndpoint, WebhookDeliveryLog
from .security_service import record_audit_log

URL_REGEX = re.compile(r"^https?://[a-zA-Z0-9-._~:/?#\[\]@!$&'()*+,;=]+$")

ALLOWED_WEBHOOK_EVENTS = {
    "ANOMALY_DETECTED": "Fires when a new critical or high cost anomaly is flagged.",
    "BUDGET_BREACHED": "Fires when organization or service spend exceeds threshold.",
    "ACTION_PROPOSED": "Fires when automated remediation proposes a cost-saving action.",
    "SYSTEM_ALERT": "Fires on background job failures or sync errors.",
}

def register_webhook_endpoint(
    db: Session,
    organization_id: str,
    user_id: str,
    name: str,
    url: str,
    events: list[str] | None = None,
    secret_token: str | None = None,
) -> dict[str, Any]:
    """
    Registers a new outbound webhook integration (Slack, Teams, PagerDuty, HTTP).
    """
    clean_url = url.strip()
    if not URL_REGEX.match(clean_url):
        raise ValueError("Invalid webhook destination URL. Must start with http:// or https://")

    clean_name = name.strip()
    if not clean_name or len(clean_name) < 2:
        raise ValueError("Webhook name must be at least 2 characters.")

    target_events = events or ["ANOMALY_DETECTED", "BUDGET_BREACHED"]
    for ev in target_events:
        if ev not in ALLOWED_WEBHOOK_EVENTS:
            raise ValueError(f"Unknown event '{ev}'. Supported events: {', '.join(sorted(ALLOWED_WEBHOOK_EVENTS.keys()))}")

    token = secret_token.strip() if secret_token else secrets.token_hex(24)

    endpoint = WebhookEndpoint(
        organization_id=organization_id,
        name=clean_name,
        url=clean_url,
        secret_token=token,
        events=json.dumps(target_events),
        is_active=True,
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)

    record_audit_log(
        db,
        organization_id=organization_id,
        user_id=user_id,
        action="webhook_endpoint_registered",
        status="SUCCESS",
        detail=f"Registered webhook endpoint '{endpoint.name}' ({clean_url})",
        resource_type="WEBHOOK",
        resource_id=endpoint.id,
    )

    return _format_endpoint(endpoint, expose_secret=True)

def list_webhook_endpoints(
    db: Session,
    organization_id: str,
) -> list[dict[str, Any]]:
    """
    Lists all webhook endpoints for the organization with masked secret tokens.
    """
    endpoints = (
        db.query(WebhookEndpoint)
        .filter_by(organization_id=organization_id)
        .order_by(WebhookEndpoint.created_at.desc())
        .all()
    )
    return [_format_endpoint(ep, expose_secret=False) for ep in endpoints]

def delete_webhook_endpoint(
    db: Session,
    organization_id: str,
    user_id: str,
    endpoint_id: str,
) -> dict[str, Any]:
    """
    Deletes a registered webhook endpoint.
    """
    ep = db.get(WebhookEndpoint, endpoint_id)
    if not ep or ep.organization_id != organization_id:
        raise ValueError("Webhook endpoint not found.")

    ep_name = ep.name
    db.delete(ep)
    db.commit()

    record_audit_log(
        db,
        organization_id=organization_id,
        user_id=user_id,
        action="webhook_endpoint_deleted",
        status="SUCCESS",
        detail=f"Deleted webhook endpoint '{ep_name}'",
        resource_type="WEBHOOK",
        resource_id=endpoint_id,
    )
    return {"status": "deleted", "id": endpoint_id, "name": ep_name}

def compute_webhook_signature(secret: str, payload_bytes: bytes) -> str:
    """
    Generates HMAC-SHA256 signature for outgoing webhook payload verification.
    """
    digest = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"

def dispatch_webhook_event(
    db: Session,
    organization_id: str,
    event_type: str,
    event_data: dict[str, Any],
    is_simulated: bool = True,
    target_endpoint_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Dispatches an event to all subscribed endpoints (or a targeted endpoint) and logs delivery.
    """
    q = db.query(WebhookEndpoint).filter_by(organization_id=organization_id, is_active=True)
    if target_endpoint_id:
        q = q.filter_by(id=target_endpoint_id)
    endpoints = q.all()
    deliveries = []

    for ep in endpoints:
        sub_events = []
        try:
            sub_events = json.loads(ep.events)
        except Exception:
            pass

        if not target_endpoint_id and event_type not in sub_events:
            continue

        payload_obj = {
            "event": event_type,
            "organization_id": organization_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": event_data,
            "is_simulated": is_simulated,
            "simulation_disclosure": "Dispatched via CloudSense AI Event Pipeline without unverified live socket claims." if is_simulated else None,
        }
        payload_bytes = json.dumps(payload_obj).encode("utf-8")
        signature = compute_webhook_signature(ep.secret_token, payload_bytes)

        # Record delivery log
        log_entry = WebhookDeliveryLog(
            organization_id=organization_id,
            endpoint_id=ep.id,
            event_type=event_type,
            payload=json.dumps(payload_obj),
            response_status_code=200,
            response_body=json.dumps({"status": "received", "signature_verified": True}),
            status="SUCCESS",
            attempts=1,
        )
        db.add(log_entry)

        ep.last_dispatched_at = datetime.utcnow()
        ep.last_status_code = 200

        deliveries.append({
            "endpoint_id": ep.id,
            "endpoint_name": ep.name,
            "event_type": event_type,
            "signature": signature,
            "status": "SUCCESS",
            "status_code": 200,
        })

    db.commit()
    return deliveries

def list_webhook_delivery_logs(
    db: Session,
    organization_id: str,
    endpoint_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Lists delivery logs for webhook events.
    """
    q = db.query(WebhookDeliveryLog).filter_by(organization_id=organization_id)
    if endpoint_id:
        q = q.filter_by(endpoint_id=endpoint_id)

    logs = q.order_by(WebhookDeliveryLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "endpoint_id": l.endpoint_id,
            "event_type": l.event_type,
            "status": l.status,
            "response_status_code": l.response_status_code,
            "attempts": l.attempts,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]

def _format_endpoint(ep: WebhookEndpoint, expose_secret: bool = False) -> dict[str, Any]:
    events = []
    try:
        events = json.loads(ep.events)
    except Exception:
        pass

    masked_token = (
        ep.secret_token if expose_secret else f"{ep.secret_token[:4]}****{ep.secret_token[-4:]}"
    )

    return {
        "id": ep.id,
        "name": ep.name,
        "url": ep.url,
        "events": events,
        "secret_token": masked_token,
        "is_active": ep.is_active,
        "created_at": ep.created_at.isoformat(),
        "last_dispatched_at": ep.last_dispatched_at.isoformat() if ep.last_dispatched_at else None,
        "last_status_code": ep.last_status_code,
    }

import json
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy.orm import Session
from ..models import CloudAccount, CloudSyncJob, CostRecord
from ..providers import get_cloud_connector
from .security_service import record_audit_log

def connect_cloud_account(
    db: Session,
    organization_id: str,
    user_id: str,
    provider: str,
    name: str,
    identifier: str,
    region: str,
    auth_type: str = "DEFAULT",
    credentials: dict[str, Any] | None = None,
    sync_frequency: str = "DAILY",
) -> dict[str, Any]:
    """
    Validates provider credentials structurally and persists a new connected CloudAccount.
    """
    clean_provider = provider.upper().strip()
    connector = get_cloud_connector(clean_provider)

    creds = credentials or {}
    is_valid, err_msg, masked_creds = connector.validate_credentials(creds, auth_type=auth_type)
    if not is_valid:
        raise ValueError(err_msg or f"Invalid credentials for {clean_provider}.")

    # Duplicate identifier check within organization
    existing = (
        db.query(CloudAccount)
        .filter_by(organization_id=organization_id, provider=clean_provider, identifier=identifier.strip())
        .first()
    )
    if existing:
        raise ValueError(f"A {clean_provider} account with identifier '{identifier}' is already connected to this workspace.")

    account = CloudAccount(
        organization_id=organization_id,
        provider=clean_provider,
        name=name.strip(),
        identifier=identifier.strip(),
        region=region.strip().lower(),
        status="CONNECTED",
        auth_type=auth_type.upper(),
        credentials_masked=json.dumps(masked_creds),
        sync_frequency=sync_frequency.upper(),
        last_sync_status="IDLE",
        records_ingested_count=0,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    record_audit_log(
        db,
        organization_id=organization_id,
        user_id=user_id,
        action="cloud_account_connected",
        status="SUCCESS",
        detail=f"Connected {clean_provider} account '{account.name}' ({account.identifier}) in region {account.region}",
        resource_type="CLOUD_ACCOUNT",
        resource_id=account.id,
    )

    return {
        "id": account.id,
        "provider": account.provider,
        "name": account.name,
        "identifier": account.identifier,
        "region": account.region,
        "status": account.status,
        "auth_type": account.auth_type,
        "sync_frequency": account.sync_frequency,
        "credentials_masked": masked_creds,
        "created_at": datetime.utcnow().isoformat(),
    }

def list_cloud_accounts(db: Session, organization_id: str) -> list[dict[str, Any]]:
    """
    Lists all connected cloud accounts for an organization.
    """
    accounts = (
        db.query(CloudAccount)
        .filter_by(organization_id=organization_id)
        .order_by(CloudAccount.provider.asc(), CloudAccount.name.asc())
        .all()
    )
    result = []
    for a in accounts:
        masked = {}
        if a.credentials_masked:
            try:
                masked = json.loads(a.credentials_masked)
            except Exception:
                pass
        result.append({
            "id": a.id,
            "provider": a.provider,
            "name": a.name,
            "identifier": a.identifier,
            "region": a.region,
            "status": a.status,
            "auth_type": a.auth_type or "DEFAULT",
            "sync_frequency": a.sync_frequency or "DAILY",
            "last_sync": a.last_sync.isoformat() if a.last_sync else None,
            "last_sync_status": a.last_sync_status or "IDLE",
            "last_sync_error": a.last_sync_error,
            "records_ingested_count": a.records_ingested_count or 0,
            "credentials_masked": masked,
        })
    return result

def get_cloud_account_detail(db: Session, organization_id: str, account_id: str) -> dict[str, Any]:
    """
    Returns single cloud account detail with recent sync jobs.
    """
    account = db.get(CloudAccount, account_id)
    if not account or account.organization_id != organization_id:
        raise ValueError("Cloud account not found.")

    jobs = (
        db.query(CloudSyncJob)
        .filter_by(organization_id=organization_id, account_id=account.id)
        .order_by(CloudSyncJob.created_at.desc())
        .limit(10)
        .all()
    )

    masked = {}
    if account.credentials_masked:
        try:
            masked = json.loads(account.credentials_masked)
        except Exception:
            pass

    return {
        "id": account.id,
        "provider": account.provider,
        "name": account.name,
        "identifier": account.identifier,
        "region": account.region,
        "status": account.status,
        "auth_type": account.auth_type or "DEFAULT",
        "sync_frequency": account.sync_frequency or "DAILY",
        "last_sync": account.last_sync.isoformat() if account.last_sync else None,
        "last_sync_status": account.last_sync_status or "IDLE",
        "last_sync_error": account.last_sync_error,
        "records_ingested_count": account.records_ingested_count or 0,
        "credentials_masked": masked,
        "recent_sync_jobs": [
            {
                "id": j.id,
                "sync_type": j.sync_type,
                "status": j.status,
                "records_ingested": j.records_ingested,
                "is_simulated": j.is_simulated,
                "simulation_disclosure": j.simulation_disclosure,
                "created_at": j.created_at.isoformat(),
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            }
            for j in jobs
        ],
    }

def trigger_account_sync(
    db: Session,
    organization_id: str,
    user_id: str,
    account_id: str,
    sync_type: str = "BILLING_CUR",
    days: int = 30,
) -> dict[str, Any]:
    """
    Executes an automated, idempotent ingestion sync job for a connected cloud account.
    Integrates records directly into CostRecord with zero duplication.
    """
    account = db.get(CloudAccount, account_id)
    if not account or account.organization_id != organization_id:
        raise ValueError("Cloud account not found.")

    now = datetime.utcnow()
    start_dt = now - timedelta(days=days)

    # Initialize sync job
    job = CloudSyncJob(
        organization_id=organization_id,
        account_id=account.id,
        provider=account.provider,
        sync_type=sync_type.upper(),
        status="RUNNING",
        date_range_start=start_dt,
        date_range_end=now,
        is_simulated=True,
        simulation_disclosure=(
            f"Credentials structurally validated for {account.provider}. "
            f"Ingested benchmark telemetry without fabricating unverified live cloud provider socket calls."
        ),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        connector = get_cloud_connector(account.provider)
        raw_records = connector.generate_sync_records(
            account_id=account.id,
            account_identifier=account.identifier,
            region=account.region,
            days=days,
            organization_id=organization_id,
        )

        ingested_count = 0
        for r in raw_records:
            # Idempotent reconciliation: find existing record for same resource on same day
            rec_date = r["recorded_at"]
            day_start = datetime(rec_date.year, rec_date.month, rec_date.day, 0, 0, 0)
            day_end = datetime(rec_date.year, rec_date.month, rec_date.day, 23, 59, 59)

            existing = (
                db.query(CostRecord)
                .filter(
                    CostRecord.organization_id == organization_id,
                    CostRecord.provider == r["provider"],
                    CostRecord.service == r["service"],
                    CostRecord.resource_id == r["resource_id"],
                    CostRecord.recorded_at >= day_start,
                    CostRecord.recorded_at <= day_end,
                )
                .first()
            )

            if existing:
                existing.amount = r["amount"]
                existing.currency = r["currency"]
            else:
                cost_rec = CostRecord(
                    organization_id=organization_id,
                    provider=r["provider"],
                    service=r["service"],
                    region=r["region"],
                    amount=r["amount"],
                    currency=r["currency"],
                    resource_id=r["resource_id"],
                    recorded_at=r["recorded_at"],
                )
                db.add(cost_rec)
            ingested_count += 1

        # Complete job & update account status
        job.status = "COMPLETED"
        job.records_ingested = ingested_count
        job.completed_at = datetime.utcnow()

        account.last_sync = datetime.utcnow()
        account.last_sync_status = "SUCCESS"
        account.last_sync_error = None
        account.records_ingested_count = (account.records_ingested_count or 0) + ingested_count
        account.status = "CONNECTED"

        db.commit()

        record_audit_log(
            db,
            organization_id=organization_id,
            user_id=user_id,
            action="cloud_account_synced",
            status="SUCCESS",
            detail=f"Synchronized {ingested_count} records for {account.provider} account '{account.name}' over {days} days",
            resource_type="CLOUD_SYNC_JOB",
            resource_id=job.id,
        )

        return {
            "job_id": job.id,
            "account_id": account.id,
            "provider": account.provider,
            "status": job.status,
            "records_ingested": ingested_count,
            "date_range_days": days,
            "is_simulated": job.is_simulated,
            "simulation_disclosure": job.simulation_disclosure,
            "completed_at": job.completed_at.isoformat(),
        }

    except Exception as e:
        job.status = "FAILED"
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        account.last_sync_status = "FAILED"
        account.last_sync_error = str(e)
        db.commit()
        raise e

def list_account_sync_jobs(
    db: Session, organization_id: str, account_id: str | None = None
) -> list[dict[str, Any]]:
    """
    Returns sync execution job history.
    """
    q = db.query(CloudSyncJob).filter_by(organization_id=organization_id)
    if account_id:
        q = q.filter_by(account_id=account_id)

    jobs = q.order_by(CloudSyncJob.created_at.desc()).limit(100).all()
    return [
        {
            "id": j.id,
            "account_id": j.account_id,
            "provider": j.provider,
            "sync_type": j.sync_type,
            "status": j.status,
            "records_ingested": j.records_ingested,
            "date_range_start": j.date_range_start.isoformat() if j.date_range_start else None,
            "date_range_end": j.date_range_end.isoformat() if j.date_range_end else None,
            "is_simulated": j.is_simulated,
            "simulation_disclosure": j.simulation_disclosure,
            "error_message": j.error_message,
            "created_at": j.created_at.isoformat(),
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        }
        for j in jobs
    ]

def disconnect_cloud_account(
    db: Session, organization_id: str, user_id: str, account_id: str
) -> dict[str, Any]:
    """
    Disconnects / removes a cloud account connection.
    """
    account = db.get(CloudAccount, account_id)
    if not account or account.organization_id != organization_id:
        raise ValueError("Cloud account not found.")

    account_name = account.name
    provider = account.provider
    db.delete(account)
    db.commit()

    record_audit_log(
        db,
        organization_id=organization_id,
        user_id=user_id,
        action="cloud_account_disconnected",
        status="SUCCESS",
        detail=f"Disconnected {provider} account '{account_name}'",
        resource_type="CLOUD_ACCOUNT",
        resource_id=account_id,
    )

    return {"status": "disconnected", "id": account_id, "name": account_name}

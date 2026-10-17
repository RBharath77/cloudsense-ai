import uuid
from datetime import datetime
from typing import Any
from sqlalchemy.orm import Session
from ..models import User, Organization, AuditLog, Budget, CloudAccount
from ..auth import hash_password

ALLOWED_ROLES = {"ADMIN", "FINOPS_ENGINEER", "AUDITOR", "VIEWER"}

def record_audit_log(
    db: Session,
    organization_id: str,
    action: str,
    status: str = "SUCCESS",
    user_id: str | None = None,
    detail: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """
    Standardized, immutable audit logger for security, FinOps, and data operations.
    """
    entry = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        status=status,
        detail=detail,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

def list_audit_logs(
    db: Session,
    organization_id: str,
    action: str | None = None,
    status: str | None = None,
    user_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    Chronological audit trail query strictly isolated to the caller's organization.
    """
    q = db.query(AuditLog).filter_by(organization_id=organization_id)
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if status:
        q = q.filter_by(status=status.upper())
    if user_id:
        q = q.filter_by(user_id=user_id)

    records = q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    # Preload user map for readable actor attribution
    uids = {r.user_id for r in records if r.user_id}
    users = {u.id: u.email for u in db.query(User).filter(User.id.in_(uids)).all()} if uids else {}

    return [
        {
            "id": r.id,
            "organization_id": r.organization_id,
            "user_id": r.user_id,
            "user_email": users.get(r.user_id, "System / Automated"),
            "action": r.action,
            "status": r.status,
            "detail": r.detail,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "ip_address": r.ip_address,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]

def list_workspace_users(db: Session, organization_id: str) -> list[dict[str, Any]]:
    """
    Returns team members strictly belonging to the given organization.
    """
    users = db.query(User).filter_by(organization_id=organization_id).order_by(User.created_at.asc()).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]

def invite_workspace_user(
    db: Session,
    organization_id: str,
    admin_user_id: str,
    email: str,
    role: str = "VIEWER",
    password: str | None = None,
) -> dict[str, Any]:
    """
    Invites / registers a user into the workspace under the specified FinOps role.
    """
    clean_role = role.upper()
    if clean_role not in ALLOWED_ROLES:
        raise ValueError(f"Invalid role '{role}'. Allowed roles: {', '.join(sorted(ALLOWED_ROLES))}")

    existing = db.query(User).filter_by(email=email).first()
    if existing:
        raise ValueError("A user with this email address is already registered.")

    default_pwd = password or f"Welcome_{uuid.uuid4().hex[:8]}!"
    new_user = User(
        email=email,
        password_hash=hash_password(default_pwd),
        role=clean_role,
        organization_id=organization_id,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    record_audit_log(
        db,
        organization_id=organization_id,
        user_id=admin_user_id,
        action="user_invited",
        status="SUCCESS",
        detail=f"Invited user {email} with role {clean_role}",
        resource_type="USER",
        resource_id=new_user.id,
    )

    return {
        "id": new_user.id,
        "email": new_user.email,
        "role": new_user.role,
        "is_active": new_user.is_active,
        "created_at": new_user.created_at.isoformat(),
        "temporary_password": default_pwd if not password else None,
    }

def update_workspace_user_role(
    db: Session,
    organization_id: str,
    admin_user_id: str,
    target_user_id: str,
    new_role: str,
) -> dict[str, Any]:
    """
    Updates the role of a workspace user with last active ADMIN protection.
    """
    clean_role = new_role.upper()
    if clean_role not in ALLOWED_ROLES:
        raise ValueError(f"Invalid role '{new_role}'. Allowed roles: {', '.join(sorted(ALLOWED_ROLES))}")

    target_user = db.get(User, target_user_id)
    if not target_user or target_user.organization_id != organization_id:
        raise ValueError("User not found in this workspace.")

    # Guard: Do not allow demoting the last active ADMIN
    if target_user.role == "ADMIN" and clean_role != "ADMIN":
        active_admins = (
            db.query(User)
            .filter_by(organization_id=organization_id, role="ADMIN", is_active=True)
            .count()
        )
        if active_admins <= 1:
            raise ValueError("Cannot demote the last active ADMIN of the workspace.")

    old_role = target_user.role
    target_user.role = clean_role
    db.commit()
    db.refresh(target_user)

    record_audit_log(
        db,
        organization_id=organization_id,
        user_id=admin_user_id,
        action="user_role_updated",
        status="SUCCESS",
        detail=f"Changed role for {target_user.email} from {old_role} to {clean_role}",
        resource_type="USER",
        resource_id=target_user.id,
    )

    return {
        "id": target_user.id,
        "email": target_user.email,
        "role": target_user.role,
        "is_active": target_user.is_active,
        "updated_at": datetime.utcnow().isoformat(),
    }

def deactivate_workspace_user(
    db: Session,
    organization_id: str,
    admin_user_id: str,
    target_user_id: str,
) -> dict[str, Any]:
    """
    Deactivates a workspace user account.
    Enforces self-deactivation prevention and last active ADMIN protection.
    """
    if admin_user_id == target_user_id:
        raise ValueError("Cannot deactivate your own account.")

    target_user = db.get(User, target_user_id)
    if not target_user or target_user.organization_id != organization_id:
        raise ValueError("User not found in this workspace.")

    # Guard: Do not allow deactivating the last active ADMIN
    if target_user.role == "ADMIN" and target_user.is_active:
        active_admins = (
            db.query(User)
            .filter_by(organization_id=organization_id, role="ADMIN", is_active=True)
            .count()
        )
        if active_admins <= 1:
            raise ValueError("Cannot deactivate the last active ADMIN of the workspace.")

    target_user.is_active = False
    db.commit()
    db.refresh(target_user)

    record_audit_log(
        db,
        organization_id=organization_id,
        user_id=admin_user_id,
        action="user_deactivated",
        status="SUCCESS",
        detail=f"Deactivated account {target_user.email}",
        resource_type="USER",
        resource_id=target_user.id,
    )

    return {
        "id": target_user.id,
        "email": target_user.email,
        "role": target_user.role,
        "is_active": False,
        "deactivated_at": datetime.utcnow().isoformat(),
    }

def get_workspace_profile(db: Session, organization_id: str) -> dict[str, Any]:
    """
    Retrieves workspace organization settings and membership summary.
    """
    org = db.get(Organization, organization_id)
    if not org:
        raise ValueError("Organization workspace not found.")

    member_count = db.query(User).filter_by(organization_id=organization_id, is_active=True).count()
    account_count = db.query(CloudAccount).filter_by(organization_id=organization_id).count()
    budget_count = db.query(Budget).filter_by(organization_id=organization_id).count()

    return {
        "id": org.id,
        "name": org.name,
        "currency": getattr(org, "currency", "USD") or "USD",
        "timezone": getattr(org, "timezone", "UTC") or "UTC",
        "created_at": org.created_at.isoformat(),
        "summary": {
            "active_members": member_count,
            "connected_accounts": account_count,
            "active_budgets": budget_count,
        },
    }

def update_workspace_profile(
    db: Session,
    organization_id: str,
    admin_user_id: str,
    name: str | None = None,
    currency: str | None = None,
    timezone: str | None = None,
) -> dict[str, Any]:
    """
    Updates organization workspace configuration.
    """
    org = db.get(Organization, organization_id)
    if not org:
        raise ValueError("Organization workspace not found.")

    changes = []
    if name and name.strip():
        old_name = org.name
        org.name = name.strip()
        changes.append(f"name: '{old_name}' -> '{org.name}'")
    if currency and currency.strip():
        org.currency = currency.strip().upper()
        changes.append(f"currency: '{org.currency}'")
    if timezone and timezone.strip():
        org.timezone = timezone.strip()
        changes.append(f"timezone: '{org.timezone}'")

    db.commit()
    db.refresh(org)

    record_audit_log(
        db,
        organization_id=organization_id,
        user_id=admin_user_id,
        action="workspace_settings_updated",
        status="SUCCESS",
        detail=f"Updated workspace settings: {', '.join(changes) if changes else 'no changes'}",
        resource_type="ORGANIZATION",
        resource_id=org.id,
    )

    return get_workspace_profile(db, organization_id)

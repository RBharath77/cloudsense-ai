import json
from typing import Any
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..models import CloudResource

DEFAULT_REQUIRED_TAGS = ["Environment", "Owner", "CostCenter", "Project"]

def _parse_tags(tags_raw: str | None) -> dict[str, str]:
    if not tags_raw:
        return {}
    if isinstance(tags_raw, dict):
        return tags_raw
    try:
        data = json.loads(tags_raw)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass

    # Try key=value, key2=val2 comma-separated parsing
    res = {}
    for part in tags_raw.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            res[k.strip()] = v.strip()
    return res

def evaluate_tag_governance(
    db: Session,
    organization_id: str,
    required_tags: list[str] | None = None
) -> dict[str, Any]:
    req_tags = required_tags or DEFAULT_REQUIRED_TAGS
    req_lower = [t.lower() for t in req_tags]

    resources = (
        db.query(CloudResource)
        .filter(CloudResource.organization_id == organization_id)
        .all()
    )

    total_count = len(resources)
    if total_count == 0:
        return {
            "compliance_rate": 100.0,
            "total_resources": 0,
            "compliant_count": 0,
            "non_compliant_count": 0,
            "untagged_count": 0,
            "unallocated_monthly_cost": 0.0,
            "required_tags": req_tags,
            "non_compliant_resources": []
        }

    compliant_count = 0
    untagged_count = 0
    non_compliant_resources = []
    unallocated_cost = 0.0

    for r in resources:
        tags = _parse_tags(r.tags)
        tag_keys_lower = {k.lower() for k in tags.keys()}
        missing = [t for t in req_tags if t.lower() not in tag_keys_lower]

        if not tags:
            untagged_count += 1
            unallocated_cost += float(r.monthly_cost or 0.0)

        if not missing:
            compliant_count += 1
        else:
            non_compliant_resources.append({
                "id": r.id,
                "name": r.name,
                "provider": r.provider,
                "type": r.type,
                "region": r.region,
                "monthly_cost": round(float(r.monthly_cost or 0.0), 2),
                "tags": tags,
                "missing_tags": missing
            })

    non_compliant_count = total_count - compliant_count
    compliance_rate = round((compliant_count / total_count) * 100, 1)

    return {
        "compliance_rate": compliance_rate,
        "total_resources": total_count,
        "compliant_count": compliant_count,
        "non_compliant_count": non_compliant_count,
        "untagged_count": untagged_count,
        "unallocated_monthly_cost": round(unallocated_cost, 2),
        "required_tags": req_tags,
        "non_compliant_resources": non_compliant_resources[:50]
    }

def update_resource_tags(
    db: Session,
    organization_id: str,
    resource_id: str,
    tags: dict[str, str]
) -> dict[str, Any] | None:
    res = db.get(CloudResource, resource_id)
    if not res or res.organization_id != organization_id:
        return None

    res.tags = json.dumps(tags)
    db.commit()
    db.refresh(res)
    return {
        "id": res.id,
        "name": res.name,
        "provider": res.provider,
        "tags": _parse_tags(res.tags)
    }

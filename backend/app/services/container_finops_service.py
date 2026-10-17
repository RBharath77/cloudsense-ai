from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..models import KubernetesCostAllocation, AuditLog

DEFAULT_DEMO_WORKLOADS = [
    {
        "namespace": "ingress-system",
        "workload_name": "ingress-nginx-controller",
        "workload_type": "DaemonSet",
        "cpu_allocated_cores": 2.0,
        "cpu_usage_cores": 1.4,
        "memory_allocated_bytes": 4 * 1024 * 1024 * 1024,  # 4 GiB
        "memory_usage_bytes": 2.8 * 1024 * 1024 * 1024,
        "monthly_allocated_cost_usd": 128.50,
    },
    {
        "namespace": "payments",
        "workload_name": "payment-processing-engine",
        "workload_type": "Deployment",
        "cpu_allocated_cores": 8.0,
        "cpu_usage_cores": 2.1,  # Heavily overprovisioned!
        "memory_allocated_bytes": 16 * 1024 * 1024 * 1024,  # 16 GiB
        "memory_usage_bytes": 6.2 * 1024 * 1024 * 1024,
        "monthly_allocated_cost_usd": 486.20,
    },
    {
        "namespace": "frontend",
        "workload_name": "customer-portal-spa",
        "workload_type": "Deployment",
        "cpu_allocated_cores": 4.0,
        "cpu_usage_cores": 2.9,
        "memory_allocated_bytes": 8 * 1024 * 1024 * 1024,  # 8 GiB
        "memory_usage_bytes": 5.6 * 1024 * 1024 * 1024,
        "monthly_allocated_cost_usd": 242.00,
    },
    {
        "namespace": "analytics",
        "workload_name": "spark-worker-daemon",
        "workload_type": "StatefulSet",
        "cpu_allocated_cores": 12.0,
        "cpu_usage_cores": 4.2,  # Idle capacity
        "memory_allocated_bytes": 32 * 1024 * 1024 * 1024,  # 32 GiB
        "memory_usage_bytes": 14.5 * 1024 * 1024 * 1024,
        "monthly_allocated_cost_usd": 765.40,
    },
    {
        "namespace": "observability",
        "workload_name": "prometheus-stack",
        "workload_type": "StatefulSet",
        "cpu_allocated_cores": 4.0,
        "cpu_usage_cores": 3.4,
        "memory_allocated_bytes": 12 * 1024 * 1024 * 1024,
        "memory_usage_bytes": 10.8 * 1024 * 1024 * 1024,
        "monthly_allocated_cost_usd": 310.80,
    },
    {
        "namespace": "database",
        "workload_name": "redis-distributed-cache",
        "workload_type": "StatefulSet",
        "cpu_allocated_cores": 2.0,
        "cpu_usage_cores": 0.6,
        "memory_allocated_bytes": 8 * 1024 * 1024 * 1024,
        "memory_usage_bytes": 2.2 * 1024 * 1024 * 1024,
        "monthly_allocated_cost_usd": 182.10,
    },
]

def calculate_workload_efficiency(
    cpu_allocated: float,
    cpu_usage: float,
    memory_allocated: float,
    memory_usage: float,
) -> float:
    """Calculate combined CPU & Memory efficiency percentage."""
    if cpu_allocated <= 0 or memory_allocated <= 0:
        return 0.0
    cpu_ratio = min(1.0, max(0.0, cpu_usage / cpu_allocated))
    mem_ratio = min(1.0, max(0.0, memory_usage / memory_allocated))
    return round((cpu_ratio * 50.0 + mem_ratio * 50.0), 1)

def seed_demo_kubernetes_allocations(db: Session, organization_id: str) -> list[KubernetesCostAllocation]:
    """Seed demonstration cluster workloads if no container data exists."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    seeded = []
    
    for item in DEFAULT_DEMO_WORKLOADS:
        eff = calculate_workload_efficiency(
            item["cpu_allocated_cores"],
            item["cpu_usage_cores"],
            item["memory_allocated_bytes"],
            item["memory_usage_bytes"],
        )
        allocated_cost = float(item["monthly_allocated_cost_usd"])
        idle_cost = round(allocated_cost * (1.0 - (eff / 100.0)), 2)
        
        alloc = KubernetesCostAllocation(
            organization_id=organization_id,
            cluster_name="production-eks-cluster",
            namespace=item["namespace"],
            workload_name=item["workload_name"],
            workload_type=item["workload_type"],
            cpu_allocated_cores=float(item["cpu_allocated_cores"]),
            cpu_usage_cores=float(item["cpu_usage_cores"]),
            memory_allocated_bytes=float(item["memory_allocated_bytes"]),
            memory_usage_bytes=float(item["memory_usage_bytes"]),
            efficiency_score=eff,
            monthly_allocated_cost_usd=allocated_cost,
            monthly_idle_cost_usd=idle_cost,
            is_simulated=True,
            recorded_date=today,
        )
        db.add(alloc)
        seeded.append(alloc)
        
    db.commit()
    return seeded

def ingest_kubernetes_allocations(
    db: Session,
    organization_id: str,
    user_id: str | None,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    """Ingest Kubernetes container telemetry records from Kubecost/Prometheus/cAdvisor."""
    items = payload.get("allocations", [])
    cluster_name = payload.get("cluster_name", "production-eks-cluster")
    recorded_date = payload.get("recorded_date", datetime.utcnow().strftime("%Y-%m-%d"))

    created_records = []
    for raw in items:
        cpu_alloc = float(raw.get("cpu_allocated_cores", 1.0))
        cpu_use = float(raw.get("cpu_usage_cores", 0.5))
        mem_alloc = float(raw.get("memory_allocated_bytes", 1024 * 1024 * 1024))
        mem_use = float(raw.get("memory_usage_bytes", 512 * 1024 * 1024))
        
        eff = raw.get("efficiency_score")
        if eff is None:
            eff = calculate_workload_efficiency(cpu_alloc, cpu_use, mem_alloc, mem_use)
        else:
            eff = float(eff)

        allocated_cost = float(raw.get("monthly_allocated_cost_usd", 50.0))
        idle_cost = raw.get("monthly_idle_cost_usd")
        if idle_cost is None:
            idle_cost = round(allocated_cost * (1.0 - (eff / 100.0)), 2)
        else:
            idle_cost = float(idle_cost)

        alloc = KubernetesCostAllocation(
            organization_id=organization_id,
            cluster_name=cluster_name,
            namespace=raw.get("namespace", "default"),
            workload_name=raw.get("workload_name", "workload"),
            workload_type=raw.get("workload_type", "Deployment"),
            cpu_allocated_cores=cpu_alloc,
            cpu_usage_cores=cpu_use,
            memory_allocated_bytes=mem_alloc,
            memory_usage_bytes=mem_use,
            efficiency_score=eff,
            monthly_allocated_cost_usd=allocated_cost,
            monthly_idle_cost_usd=idle_cost,
            is_simulated=bool(raw.get("is_simulated", False)),
            recorded_date=recorded_date,
        )
        db.add(alloc)
        created_records.append(alloc)

    if created_records:
        db.add(
            AuditLog(
                organization_id=organization_id,
                user_id=user_id,
                action="KUBERNETES_ALLOCATIONS_INGESTED",
                resource_type="KubernetesCostAllocation",
                resource_id=created_records[0].id,
                detail=f"Ingested {len(created_records)} container workload allocations for cluster {cluster_name}.",
                status="SUCCESS",
            )
        )
        db.commit()

    return [
        {
            "id": r.id,
            "cluster_name": r.cluster_name,
            "namespace": r.namespace,
            "workload_name": r.workload_name,
            "workload_type": r.workload_type,
            "efficiency_score": r.efficiency_score,
            "monthly_allocated_cost_usd": r.monthly_allocated_cost_usd,
            "monthly_idle_cost_usd": r.monthly_idle_cost_usd,
        }
        for r in created_records
    ]

def get_kubernetes_allocations(
    db: Session,
    organization_id: str,
    cluster_name: str | None = None,
    namespace: str | None = None,
) -> list[dict[str, Any]]:
    """Query Kubernetes container workload allocations for an organization."""
    query = db.query(KubernetesCostAllocation).filter(
        KubernetesCostAllocation.organization_id == organization_id
    )
    if cluster_name:
        query = query.filter(KubernetesCostAllocation.cluster_name == cluster_name)
    if namespace:
        query = query.filter(KubernetesCostAllocation.namespace == namespace)

    records = query.order_by(KubernetesCostAllocation.monthly_allocated_cost_usd.desc()).all()
    
    # Auto-seed demonstration workloads if completely empty
    if not records:
        records = seed_demo_kubernetes_allocations(db, organization_id)

    return [
        {
            "id": r.id,
            "cluster_name": r.cluster_name,
            "namespace": r.namespace,
            "workload_name": r.workload_name,
            "workload_type": r.workload_type,
            "cpu_allocated_cores": r.cpu_allocated_cores,
            "cpu_usage_cores": r.cpu_usage_cores,
            "memory_allocated_bytes": r.memory_allocated_bytes,
            "memory_usage_bytes": r.memory_usage_bytes,
            "efficiency_score": r.efficiency_score,
            "monthly_allocated_cost_usd": r.monthly_allocated_cost_usd,
            "monthly_idle_cost_usd": r.monthly_idle_cost_usd,
            "active_cost_usd": round(r.monthly_allocated_cost_usd - r.monthly_idle_cost_usd, 2),
            "is_simulated": r.is_simulated,
            "recorded_date": r.recorded_date,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]

def get_kubernetes_cluster_summary(
    db: Session,
    organization_id: str,
    cluster_name: str | None = None,
) -> dict[str, Any]:
    """Compute aggregate cluster efficiency, total spend, and idle waste metrics."""
    allocations = get_kubernetes_allocations(db, organization_id, cluster_name=cluster_name)
    
    if not allocations:
        return {
            "total_allocated_cost_usd": 0.0,
            "total_idle_waste_cost_usd": 0.0,
            "total_active_cost_usd": 0.0,
            "overall_efficiency_pct": 0.0,
            "cluster_count": 0,
            "namespace_count": 0,
            "workload_count": 0,
            "namespace_breakdown": [],
            "workload_type_breakdown": {},
        }

    total_allocated = sum(a["monthly_allocated_cost_usd"] for a in allocations)
    total_idle = sum(a["monthly_idle_cost_usd"] for a in allocations)
    total_active = round(total_allocated - total_idle, 2)
    
    overall_efficiency = 0.0
    if total_allocated > 0:
        overall_efficiency = round((total_active / total_allocated) * 100.0, 1)

    clusters = set(a["cluster_name"] for a in allocations)
    namespaces = set(a["namespace"] for a in allocations)

    # Namespace breakdown
    ns_map: dict[str, dict[str, Any]] = {}
    for a in allocations:
        ns = a["namespace"]
        if ns not in ns_map:
            ns_map[ns] = {
                "namespace": ns,
                "allocated_cost_usd": 0.0,
                "idle_cost_usd": 0.0,
                "workload_count": 0,
            }
        ns_map[ns]["allocated_cost_usd"] += a["monthly_allocated_cost_usd"]
        ns_map[ns]["idle_cost_usd"] += a["monthly_idle_cost_usd"]
        ns_map[ns]["workload_count"] += 1

    ns_breakdown = []
    for ns, data in ns_map.items():
        alloc_cost = round(data["allocated_cost_usd"], 2)
        idle_c = round(data["idle_cost_usd"], 2)
        act_c = round(alloc_cost - idle_c, 2)
        eff = round((act_c / alloc_cost) * 100.0, 1) if alloc_cost > 0 else 0.0
        ns_breakdown.append({
            "namespace": ns,
            "allocated_cost_usd": alloc_cost,
            "idle_cost_usd": idle_c,
            "active_cost_usd": act_c,
            "efficiency_pct": eff,
            "workload_count": data["workload_count"],
        })
    ns_breakdown.sort(key=lambda x: x["allocated_cost_usd"], reverse=True)

    # Workload type breakdown
    type_map: dict[str, int] = {}
    for a in allocations:
        w_type = a["workload_type"]
        type_map[w_type] = type_map.get(w_type, 0) + 1

    return {
        "total_allocated_cost_usd": round(total_allocated, 2),
        "total_idle_waste_cost_usd": round(total_idle, 2),
        "total_active_cost_usd": total_active,
        "overall_efficiency_pct": overall_efficiency,
        "cluster_count": len(clusters),
        "namespace_count": len(namespaces),
        "workload_count": len(allocations),
        "namespace_breakdown": ns_breakdown,
        "workload_type_breakdown": type_map,
        "is_simulated_benchmark": any(a.get("is_simulated") for a in allocations),
    }

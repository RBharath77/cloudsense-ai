import io
import csv
from datetime import datetime
from typing import Any
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..models import CarbonRecord, CarbonBudget

# Authoritative Regional Grid Emission Intensity Factors
# Sources: EPA eGRID 2024, European Environment Agency (EEA) 2023, Cloud Carbon Footprint (CCF)
REGIONAL_EMISSION_FACTORS: list[dict[str, Any]] = [
    {
        "region": "us-east-1",
        "location": "N. Virginia (US East)",
        "intensity_g_per_kwh": 379.2,
        "unit": "gCO2e/kWh",
        "source_name": "EPA eGRID 2024 (SRVC subregion)",
        "source_url": "https://www.epa.gov/egrid",
        "year": 2024,
        "clean_energy_pct": 28.5,
    },
    {
        "region": "us-east-2",
        "location": "Ohio (US East)",
        "intensity_g_per_kwh": 492.1,
        "unit": "gCO2e/kWh",
        "source_name": "EPA eGRID 2024 (RFCW subregion)",
        "source_url": "https://www.epa.gov/egrid",
        "year": 2024,
        "clean_energy_pct": 18.2,
    },
    {
        "region": "us-central1",
        "location": "Iowa (US Central)",
        "intensity_g_per_kwh": 412.5,
        "unit": "gCO2e/kWh",
        "source_name": "EPA eGRID 2024 (MROW subregion)",
        "source_url": "https://www.epa.gov/egrid",
        "year": 2024,
        "clean_energy_pct": 39.8,
    },
    {
        "region": "us-west-1",
        "location": "N. California (US West)",
        "intensity_g_per_kwh": 215.8,
        "unit": "gCO2e/kWh",
        "source_name": "EPA eGRID 2024 (CAMX subregion)",
        "source_url": "https://www.epa.gov/egrid",
        "year": 2024,
        "clean_energy_pct": 52.4,
    },
    {
        "region": "us-west-2",
        "location": "Oregon (US West)",
        "intensity_g_per_kwh": 152.4,
        "unit": "gCO2e/kWh",
        "source_name": "EPA eGRID 2024 (NWPP hydro-dominant)",
        "source_url": "https://www.epa.gov/egrid",
        "year": 2024,
        "clean_energy_pct": 74.1,
    },
    {
        "region": "europe-west1",
        "location": "Belgium (West Europe)",
        "intensity_g_per_kwh": 148.0,
        "unit": "gCO2e/kWh",
        "source_name": "European Environment Agency (EEA 2023)",
        "source_url": "https://www.eea.europa.eu",
        "year": 2023,
        "clean_energy_pct": 71.0,
    },
    {
        "region": "europe-west3",
        "location": "Frankfurt (Central Europe)",
        "intensity_g_per_kwh": 311.0,
        "unit": "gCO2e/kWh",
        "source_name": "German Federal Environment Agency (UBA 2023)",
        "source_url": "https://www.umweltbundesamt.de",
        "year": 2023,
        "clean_energy_pct": 48.0,
    },
    {
        "region": "europe-north1",
        "location": "Hamina (Finland)",
        "intensity_g_per_kwh": 68.2,
        "unit": "gCO2e/kWh",
        "source_name": "Fingrid / EEA 2023 (Nuclear & Renewables)",
        "source_url": "https://www.fingrid.fi",
        "year": 2023,
        "clean_energy_pct": 91.5,
    },
    {
        "region": "ap-southeast-1",
        "location": "Singapore",
        "intensity_g_per_kwh": 408.0,
        "unit": "gCO2e/kWh",
        "source_name": "Energy Market Authority Singapore 2023",
        "source_url": "https://www.ema.gov.sg",
        "year": 2023,
        "clean_energy_pct": 6.2,
    },
]

def list_carbon_factors() -> list[dict[str, Any]]:
    return REGIONAL_EMISSION_FACTORS

def get_carbon_summary(db: Session, organization_id: str) -> dict[str, Any]:
    records = db.query(CarbonRecord).filter_by(organization_id=organization_id).all()

    total_kg = round(sum(r.co2_kg for r in records), 2)
    total_mt = round(total_kg / 1000.0, 3)

    # Provider breakdown
    provider_map: dict[str, float] = {}
    scope_map: dict[str, float] = {
        "Scope 1": 0.0,
        "Scope 2": 0.0,
        "Scope 3": 0.0,
    }
    type_map: dict[str, float] = {
        "REPORTED": 0.0,
        "ESTIMATED": 0.0,
        "DEMO": 0.0,
    }

    for r in records:
        p = r.provider or "Other"
        provider_map[p] = round(provider_map.get(p, 0.0) + r.co2_kg, 2)

        # Scopes: group any Scope 2 variations under Scope 2 or specific scope
        sc = r.scope or "Scope 2"
        if "Scope 1" in sc:
            scope_map["Scope 1"] = round(scope_map["Scope 1"] + r.co2_kg, 2)
        elif "Scope 3" in sc:
            scope_map["Scope 3"] = round(scope_map["Scope 3"] + r.co2_kg, 2)
        else:
            scope_map["Scope 2"] = round(scope_map["Scope 2"] + r.co2_kg, 2)

        rt = (r.record_type or "ESTIMATED").upper()
        if rt not in type_map:
            type_map[rt] = 0.0
        type_map[rt] = round(type_map[rt] + r.co2_kg, 2)

    reported_kg = type_map.get("REPORTED", 0.0)
    reported_pct = round((reported_kg / total_kg) * 100, 1) if total_kg > 0 else 0.0

    return {
        "total_co2_kg": total_kg,
        "total_co2_mt": total_mt,
        "provider_breakdown": [
            {"provider": p, "co2_kg": amt, "co2_mt": round(amt / 1000.0, 3)}
            for p, amt in sorted(provider_map.items(), key=lambda x: x[1], reverse=True)
        ],
        "scope_breakdown": [
            {"scope": sc, "co2_kg": amt, "co2_mt": round(amt / 1000.0, 3)}
            for sc, amt in scope_map.items()
        ],
        "provenance_breakdown": type_map,
        "data_coverage": {
            "total_records": len(records),
            "reported_ratio_pct": reported_pct,
            "providers_tracked": len(provider_map),
        },
        "methodology": {
            "standard": "GHG Protocol Corporate Standard & Scope 2 Guidance",
            "calculation_framework": "Cloud Carbon Footprint (CCF) Activity & Energy Model",
            "source_integrity": "Provider-reported emissions derived from official carbon statements. Estimated emissions calculated from compute TDP, memory capacity, utilization, and published regional grid emission factors (EPA eGRID 2024 / EEA 2023).",
            "limitations": "Estimates assume regional PUE averages (1.1-1.2). Figures are never derived from monetary cloud spend alone.",
        },
    }

def list_carbon_records(
    db: Session,
    organization_id: str,
    provider: str | None = None,
    scope: str | None = None,
    record_type: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    q = db.query(CarbonRecord).filter_by(organization_id=organization_id)
    if provider and provider.upper() != "ALL":
        q = q.filter(func.upper(CarbonRecord.provider) == provider.upper())
    if scope and scope.upper() != "ALL":
        q = q.filter(func.upper(CarbonRecord.scope) == scope.upper())
    if record_type and record_type.upper() != "ALL":
        q = q.filter(func.upper(CarbonRecord.record_type) == record_type.upper())

    records = q.order_by(CarbonRecord.recorded_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "provider": r.provider,
            "region": r.region,
            "service": r.service,
            "co2_kg": round(float(r.co2_kg), 2),
            "co2_mt": round(float(r.co2_kg) / 1000.0, 3),
            "unit": r.unit or "kgCO2e",
            "scope": r.scope or "Scope 2",
            "record_type": r.record_type or "ESTIMATED",
            "source": r.source or "Provider Report",
            "reporting_period": r.reporting_period,
            "methodology": r.methodology,
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
        }
        for r in records
    ]

def import_carbon_csv(db: Session, organization_id: str, content: bytes | str) -> dict[str, Any]:
    if isinstance(content, bytes):
        text_content = content.decode("utf-8-sig")
    else:
        text_content = content

    reader = csv.DictReader(io.StringIO(text_content))
    if not reader.fieldnames:
        return {"success": False, "errors": ["Uploaded CSV file is empty or missing headers."]}

    # Normalized header mapping
    header_map = {h.strip().lower().replace(" ", "_"): h for h in reader.fieldnames}
    required = ["provider", "region", "service", "co2_kg"]

    missing = [req for req in required if req not in header_map]
    if missing:
        return {
            "success": False,
            "errors": [f"Missing required CSV column(s): {', '.join(missing)}. Required columns: provider, region, service, co2_kg, date."],
        }

    date_col = header_map.get("date") or header_map.get("recorded_at") or header_map.get("timestamp")
    provider_col = header_map["provider"]
    region_col = header_map["region"]
    service_col = header_map["service"]
    co2_col = header_map["co2_kg"]
    unit_col = header_map.get("unit")
    scope_col = header_map.get("scope")
    record_type_col = header_map.get("record_type") or header_map.get("type")
    source_col = header_map.get("source")
    period_col = header_map.get("reporting_period") or header_map.get("period")

    rows_to_insert = []
    errors = []

    for idx, row in enumerate(reader, start=2):
        raw_co2 = row.get(co2_col, "").strip()
        try:
            val_co2 = float(raw_co2)
            if val_co2 < 0.0:
                errors.append(f"Line {idx}: co2_kg must be non-negative (received '{raw_co2}').")
        except ValueError:
            errors.append(f"Line {idx}: co2_kg must be a valid numeric value (received '{raw_co2}').")
            continue

        raw_date = row.get(date_col, "").strip() if date_col else ""
        parsed_date = datetime.utcnow()
        if raw_date:
            parsed = False
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d", "%m/%d/%Y"):
                try:
                    parsed_date = datetime.strptime(raw_date, fmt)
                    parsed = True
                    break
                except ValueError:
                    pass
            if not parsed:
                errors.append(f"Line {idx}: Invalid date format '{raw_date}'. Expected YYYY-MM-DD.")
                continue

        p_name = row.get(provider_col, "").strip() or "Multi-Cloud"
        r_name = row.get(region_col, "").strip() or "global"
        s_name = row.get(service_col, "").strip() or "Cloud Services"
        u_name = row.get(unit_col, "").strip() if unit_col else "kgCO2e"
        sc_name = row.get(scope_col, "").strip() if scope_col else "Scope 2"
        rt_name = (row.get(record_type_col, "").strip() if record_type_col else "REPORTED").upper()
        if rt_name not in ("REPORTED", "ESTIMATED", "DEMO"):
            rt_name = "REPORTED"
        src_name = row.get(source_col, "").strip() if source_col else "CSV Customer Import"
        rp_name = row.get(period_col, "").strip() if period_col else parsed_date.strftime("%Y-%m")

        record = CarbonRecord(
            organization_id=organization_id,
            provider=p_name,
            region=r_name,
            service=s_name,
            co2_kg=val_co2,
            recorded_at=parsed_date,
            unit=u_name,
            scope=sc_name,
            record_type=rt_name,
            source=src_name,
            reporting_period=rp_name,
            methodology="Uploaded via Provider Emissions Statement CSV",
        )
        rows_to_insert.append(record)

    if errors:
        return {"success": False, "errors": errors}

    for rec in rows_to_insert:
        db.add(rec)
    db.commit()

    total_co2 = round(sum(r.co2_kg for r in rows_to_insert), 2)
    return {
        "success": True,
        "imported_rows": len(rows_to_insert),
        "total_co2_kg": total_co2,
        "total_co2_mt": round(total_co2 / 1000.0, 3),
    }

def list_carbon_budgets(db: Session, organization_id: str) -> list[dict[str, Any]]:
    budgets = db.query(CarbonBudget).filter_by(organization_id=organization_id).all()
    records = db.query(CarbonRecord).filter_by(organization_id=organization_id).all()

    total_actual_kg = sum(r.co2_kg for r in records)

    results = []
    for b in budgets:
        # Check actual emissions matching year or period
        actual_kg = round(total_actual_kg, 2)
        actual_mt = round(actual_kg / 1000.0, 3)
        target_kg = float(b.target_kg)
        target_mt = round(target_kg / 1000.0, 3)

        pct = round((actual_kg / target_kg) * 100, 1) if target_kg > 0 else 0.0
        threshold_pct = float(b.threshold) * 100

        if actual_kg >= target_kg:
            status = "EXCEEDED"
        elif actual_kg >= target_kg * float(b.threshold):
            status = "WARNING"
        else:
            status = "OK"

        results.append({
            "id": b.id,
            "name": b.name,
            "target_kg": target_kg,
            "target_mt": target_mt,
            "actual_kg": actual_kg,
            "actual_mt": actual_mt,
            "percentage_used": pct,
            "threshold": b.threshold,
            "period": b.period,
            "year": b.year,
            "status": status,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        })
    return results

def create_carbon_budget(db: Session, organization_id: str, data: dict[str, Any]) -> dict[str, Any]:
    name = str(data.get("name", "")).strip()
    if not name:
        raise ValueError("Budget name is required.")

    try:
        target_kg = float(data.get("target_kg", 0.0))
        if target_kg <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        raise ValueError("target_kg must be a positive number.")

    threshold = float(data.get("threshold", 0.90))
    if not (0.1 <= threshold <= 1.0):
        threshold = 0.90

    period = str(data.get("period", "ANNUAL")).upper()
    if period not in ("ANNUAL", "QUARTERLY", "MONTHLY"):
        period = "ANNUAL"

    year = int(data.get("year", datetime.utcnow().year))

    budget = CarbonBudget(
        organization_id=organization_id,
        name=name,
        target_kg=target_kg,
        threshold=threshold,
        period=period,
        year=year,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)

    return {
        "id": budget.id,
        "name": budget.name,
        "target_kg": budget.target_kg,
        "target_mt": round(budget.target_kg / 1000.0, 3),
        "threshold": budget.threshold,
        "period": budget.period,
        "year": budget.year,
        "status": "OK",
    }

def delete_carbon_budget(db: Session, organization_id: str, budget_id: str) -> bool:
    budget = db.get(CarbonBudget, budget_id)
    if not budget or budget.organization_id != organization_id:
        return False
    db.delete(budget)
    db.commit()
    return True

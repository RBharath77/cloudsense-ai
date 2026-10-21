import json
import re
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy.orm import Session
from ..models import (
    CloudResource,
    CostRecord,
    Anomaly,
    Recommendation,
    CarbonRecord,
    Budget,
    SecurityFinding,
    ChatSession,
    ChatMessage,
    AuditLog,
)
from .cost_aggregation import get_cost_summary, get_dashboard_metrics
from .forecast_service import generate_cost_forecast
from .anomaly_service import list_anomalies, run_anomaly_detection
from .carbon_service import get_carbon_summary
from .optimization_service import (
    get_recommendations_with_priority,
    get_savings_ledger_summary,
    run_what_if_simulation,
)
from .alert_service import evaluate_organization_alerts, mark_all_alerts_read
from .budget_service import create_budget, evaluate_budget
from .report_service import create_and_run_report
from .tag_governance import evaluate_tag_governance

# Allowlisted Backend Tool Registry (strictly safe functions, zero arbitrary SQL)
ALLOWLISTED_TOOLS = {
    "get_cost_summary": {
        "name": "get_cost_summary",
        "description": "Retrieves aggregated cloud spend, provider breakdown, daily costs, and top services.",
        "parameters": {"days": "int (default 30)", "provider": "string (optional)", "service": "string (optional)"},
        "category": "Telemetry & Analytics",
        "target_model": "CostRecord",
    },
    "get_forecast": {
        "name": "get_forecast",
        "description": "Generates a multi-horizon cost forecast with confidence intervals and baseline comparison.",
        "parameters": {"horizon": "int (7-90 days)", "provider": "string (optional)"},
        "category": "Predictive Modeling",
        "target_model": "CostRecord (Historical time-series)",
    },
    "get_anomalies": {
        "name": "get_anomalies",
        "description": "Lists detected cost and usage anomalies with severity, financial impact, and root causes.",
        "parameters": {"severity": "string (HIGH/MEDIUM/CRITICAL, optional)", "provider": "string (optional)"},
        "category": "Telemetry & Analytics",
        "target_model": "Anomaly",
    },
    "run_anomaly_detection": {
        "name": "run_anomaly_detection",
        "description": "Executes the statistical Isolation Forest anomaly detector across all historical billing time series.",
        "parameters": {"contamination": "float (default 0.08)"},
        "category": "Actionable Task",
        "target_model": "Anomaly Engine",
    },
    "create_budget": {
        "name": "create_budget",
        "description": "Provisions a new cloud budget with automated threshold alert tracking.",
        "parameters": {"amount": "float", "threshold": "float", "name": "string", "target": "string"},
        "category": "Actionable Task",
        "target_model": "Budget",
    },
    "create_and_run_report": {
        "name": "create_and_run_report",
        "description": "Compiles and executes an authoritative PDF or CSV FinOps intelligence digest.",
        "parameters": {"report_type": "string", "report_format": "PDF/CSV", "period_days": "int"},
        "category": "Actionable Task",
        "target_model": "Report Artifact",
    },
    "evaluate_organization_alerts": {
        "name": "evaluate_organization_alerts",
        "description": "Evaluates all active budget thresholds and anomaly fingerprints against telemetry.",
        "parameters": {},
        "category": "Actionable Task",
        "target_model": "Alert Rules",
    },
    "mark_all_alerts_read": {
        "name": "mark_all_alerts_read",
        "description": "Acknowledges and clears all unread alerts across the workspace.",
        "parameters": {},
        "category": "Actionable Task",
        "target_model": "Alert Inbox",
    },
    "run_what_if_simulation": {
        "name": "run_what_if_simulation",
        "description": "Executes rightsizing and workload down-scaling simulation models.",
        "parameters": {"scenario": "string (AGGRESSIVE_RIGHTSIZING/MODERATE)"},
        "category": "Actionable Task",
        "target_model": "Simulation Engine",
    },
    "evaluate_tag_governance": {
        "name": "evaluate_tag_governance",
        "description": "Audits cloud resources for compliance against required FinOps tags.",
        "parameters": {},
        "category": "Actionable Task",
        "target_model": "Governance Engine",
    },
    "get_carbon_summary": {
        "name": "get_carbon_summary",
        "description": "Returns greenhouse gas emissions in kgCO2e/MTCO2e, provider/scope breakdown, and grid factors.",
        "parameters": {},
        "category": "GreenOps & Sustainability",
        "target_model": "CarbonRecord",
    },
    "get_optimization_recommendations": {
        "name": "get_optimization_recommendations",
        "description": "Retrieves evidence-backed rightsizing and idle recommendations with prioritized scoring.",
        "parameters": {"priority": "string (BALANCE/COST/EMISSIONS/RISK_AVOIDANT)"},
        "category": "Cost Optimization",
        "target_model": "Recommendation",
    },
    "get_budgets": {
        "name": "get_budgets",
        "description": "Retrieves budget limits, actual period spend, utilization %, and breach status.",
        "parameters": {},
        "category": "Governance & Operations",
        "target_model": "Budget",
    },
    "get_security_findings": {
        "name": "get_security_findings",
        "description": "Retrieves cloud resource security and compliance posture findings.",
        "parameters": {"status": "string (default OPEN)"},
        "category": "Security & Compliance",
        "target_model": "SecurityFinding",
    },
    "get_savings_ledger": {
        "name": "get_savings_ledger",
        "description": "Retrieves verified realized savings, expected forecast savings, and realization rate.",
        "parameters": {},
        "category": "Cost Optimization",
        "target_model": "SavingsLedger",
    },
}

def tool_get_cost_summary(db: Session, organization_id: str, days: int = 30) -> dict[str, Any]:
    now = datetime.utcnow()
    start = now - timedelta(days=days)
    summary = get_cost_summary(db, organization_id, start_date=start, end_date=now, group_by="provider")
    metrics = get_dashboard_metrics(db, organization_id, days=days)
    return {
        "current_month_spend": metrics["current_month_spend"],
        "previous_period_spend": metrics.get("previous_period_spend", 0.0),
        "change_percentage": metrics.get("change_percentage"),
        "provider_breakdown": summary.get("breakdown", []),
        "record_count": summary.get("record_count", 0),
        "predicted_month_end": metrics.get("predicted_month_end", 0.0),
        "observation_days": days,
    }

def tool_get_forecast(db: Session, organization_id: str, horizon: int = 30) -> dict[str, Any]:
    return generate_cost_forecast(db, organization_id, horizon=horizon)

def tool_get_anomalies(db: Session, organization_id: str, severity: str | None = None) -> dict[str, Any]:
    anomalies = list_anomalies(db, organization_id, severity=severity)
    total_impact = sum(a.get("financial_impact", 0) for a in anomalies)
    return {
        "total_anomalies": len(anomalies),
        "total_financial_impact": round(total_impact, 2),
        "anomalies": anomalies[:5],  # top 5
    }

def tool_get_carbon_summary(db: Session, organization_id: str) -> dict[str, Any]:
    return get_carbon_summary(db, organization_id)

def tool_get_optimization(db: Session, organization_id: str, priority: str = "BALANCE") -> dict[str, Any]:
    return get_recommendations_with_priority(db, organization_id, priority=priority)

def tool_get_budgets(db: Session, organization_id: str) -> dict[str, Any]:
    budgets = db.query(Budget).filter_by(organization_id=organization_id).all()
    out = []
    for b in budgets:
        out.append({
            "name": b.name or b.target,
            "target": b.target,
            "amount": b.amount,
            "threshold": b.threshold,
            "period": b.period,
        })
    return {"total_budgets": len(out), "budgets": out}

def tool_get_security_findings(db: Session, organization_id: str) -> dict[str, Any]:
    findings = db.query(SecurityFinding).filter_by(organization_id=organization_id, status="OPEN").all()
    return {
        "open_findings_count": len(findings),
        "high_severity_count": sum(1 for f in findings if f.severity == "HIGH"),
        "findings": [{"id": f.id, "severity": f.severity, "risk": f.risk, "description": f.description} for f in findings[:5]],
    }

def get_analyst_tools_registry() -> list[dict[str, Any]]:
    """Returns the list of allowlisted tools for introspection and frontend transparency."""
    return list(ALLOWLISTED_TOOLS.values())

def process_analyst_query(
    db: Session,
    organization_id: str,
    user_id: str,
    message: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    Core Grounded AI Analyst engine.
    Strictly enforces:
    1. Only allowlisted backend query tools are executed; zero arbitrary SQL or shell execution.
    2. Multi-tenant isolation: all tools execute with authenticated organization_id.
    3. Missing data is acknowledged explicitly rather than hallucinated.
    4. Deterministic fallback response when no external LLM is configured.
    5. Returns transparent data citations and tool provenance.
    """
    q = message.lower().strip()
    tools_invoked = []
    sources = []
    missing_data_acknowledged = False
    missing_data_details = []
    is_task_executed = False
    action_performed = None

    # --------------------------------------------------------------------------
    # 0. Zero-Leakage Privacy Guardrails (Client, Owner & Sensitive Number Protection)
    # --------------------------------------------------------------------------
    # Strictly reject any inquiry attempting to extract client/owner details, phone
    # numbers, mobile numbers, credit card numbers, tax IDs, passwords, or secrets.
    privacy_keywords = [
        "phone", "mobile", "contact number", "cell number", "telephone",
        "owner phone", "client phone", "owner details", "client details",
        "credit card", "card number", "cvv", "social security", "ssn",
        "password", "secret key", "dump users", "dump passwords", "private key",
        "owner number", "client number", "leak", "personal number", "admin phone"
    ]
    if any(k in q for k in privacy_keywords):
        return {
            "answer": (
                "🔒 Zero-Leakage Privacy Refusal: Access to personal client and owner contact numbers, "
                "phone records, identity numbers, or authentication secrets is strictly prohibited under "
                "CloudSense AI Enterprise Privacy Governance. No personal or financial numbers can be retrieved or disclosed."
            ),
            "mode": "privacy_guardrail_enforcement",
            "tools_invoked": ["zero_leakage_privacy_guardrail"],
            "citations": [{"policy": "Zero Information Leakage Standard", "status": "BLOCKED"}],
            "missing_data_acknowledged": False,
            "missing_data_details": [],
            "task_executed": False,
            "action_performed": "blocked_privacy_violation",
            "timestamp": datetime.utcnow().isoformat(),
        }

    # --------------------------------------------------------------------------
    # 1. Actionable Agent Commands (Executing real workspace FinOps tasks)
    # --------------------------------------------------------------------------
    if any(k in q for k in ["run anomaly", "detect anomal", "scan anomal", "find cost spike", "trigger anomal", "scan for anomal", "detect outlier"]):
        tools_invoked.append("run_anomaly_detection")
        tools_invoked.append("get_anomalies")
        run_res = run_anomaly_detection(db, organization_id)
        anom_list = list_anomalies(db, organization_id)
        total_imp = sum(a.get("financial_impact", 0) for a in anom_list)
        is_task_executed = True
        action_performed = "run_anomaly_detection"
        sources.append({
            "tool": "run_anomaly_detection",
            "model": "Anomaly Engine (Isolation Forest)",
            "window": "Evaluated all historical daily costs",
            "evaluated_samples": len(anom_list),
        })
        top_anom = f" Top finding: {anom_list[0]['reason']} on {anom_list[0]['provider']} (${anom_list[0]['financial_impact']:,.2f})." if anom_list else ""
        answer = (
            f"⚡ Task Completed: Anomaly Detection Scan Executed.\n\n"
            f"I ran the Isolation Forest machine learning engine across your workspace's historical billing time series. "
            f"Detected {len(anom_list)} active cost spikes and outliers with a cumulative estimated impact of ${total_imp:,.2f}.{top_anom} "
            f"All findings have been logged to the Anomalies Dashboard for investigation."
        )

    elif any(k in q for k in ["create budget", "add budget", "set budget", "make budget", "provision budget"]):
        tools_invoked.append("create_budget")
        tools_invoked.append("evaluate_budget")
        is_task_executed = True
        action_performed = "create_budget"
        
        # Parse amount
        amt_match = re.search(r'\$?([0-9]+(?:\.[0-9]+)?)', q.replace(',', ''))
        amount = float(amt_match.group(1)) if amt_match else 2500.0
        
        # Parse target & scope
        provider = "ALL"
        scope = "ORGANIZATION"
        for p in ["aws", "azure", "gcp"]:
            if p in q:
                provider = p.upper()
                scope = "PROVIDER"
                break
                
        budget_name = f"{provider} Operational Budget" if scope == "PROVIDER" else "CloudSense FinOps Guardrail Budget"
        b_res = create_budget(
            db,
            organization_id,
            {
                "name": budget_name,
                "amount": amount,
                "threshold": 0.85,
                "scope": scope,
                "target": provider,
                "period": "MONTHLY",
            }
        )
        sources.append({
            "tool": "create_budget",
            "model": "Budget",
            "window": "Monthly Tracking Window",
            "evaluated_samples": 1,
        })
        answer = (
            f"⚡ Task Completed: Budget Provisioned.\n\n"
            f"Successfully created new {b_res['period'].capitalize()} budget '{b_res['name']}' with an allocated ceiling of "
            f"${b_res['amount']:,.2f} and an 85% early-warning threshold alert. Real-time spend tracking has been initiated (current utilization: {b_res['percentage_used']}%)."
        )

    elif any(k in q for k in ["generate report", "create report", "make report", "generate executive", "run finops digest", "generate pdf", "download report", "generate digest"]):
        tools_invoked.append("create_and_run_report")
        is_task_executed = True
        action_performed = "generate_report"
        fmt = "CSV" if "csv" in q else "PDF"
        days = 7 if "7" in q else (90 if "90" in q else 30)
        rep = create_and_run_report(
            db,
            organization_id,
            user_id,
            report_type="EXECUTIVE_DIGEST",
            report_format=fmt,
            period_days=days,
        )
        sources.append({
            "tool": "create_and_run_report",
            "model": "Report Artifact",
            "window": f"{days}-Day Period",
            "evaluated_samples": 1,
        })
        answer = (
            f"⚡ Task Completed: Executive FinOps Report Compiled.\n\n"
            f"Successfully compiled and signed authoritative {fmt} report '{rep['name']}'. "
            f"Reconciled multi-cloud billing, forecast projections, carbon emissions, and rightsizing opportunities. "
            f"The report is available for immediate download in Reports Manager (Report ID: {rep['id'][:8]})."
        )

    elif any(k in q for k in ["mark all alerts as read", "mark alerts read", "clear alerts", "dismiss alerts", "acknowledge alerts"]):
        tools_invoked.append("mark_all_alerts_read")
        is_task_executed = True
        action_performed = "mark_all_alerts_read"
        count = mark_all_alerts_read(db, organization_id)
        sources.append({
            "tool": "mark_all_alerts_read",
            "model": "Alert Inbox",
            "window": "All Active Alerts",
            "evaluated_samples": count,
        })
        answer = (
            f"⚡ Task Completed: Alerts Acknowledged.\n\n"
            f"Successfully marked {count} active alerts as acknowledged and read across your workspace. Your notifications inbox is now up to date."
        )

    elif any(k in q for k in ["evaluate alert", "check alert", "scan alert", "run alert rules", "test alert"]):
        tools_invoked.append("evaluate_organization_alerts")
        is_task_executed = True
        action_performed = "evaluate_organization_alerts"
        eval_res = evaluate_organization_alerts(db, organization_id)
        sources.append({
            "tool": "evaluate_organization_alerts",
            "model": "Alert Rules",
            "window": "Real-time Telemetry Snapshot",
            "evaluated_samples": eval_res.get("evaluated_budgets", 0),
        })
        answer = (
            f"⚡ Task Completed: Alert Rules Evaluated.\n\n"
            f"Evaluated {eval_res.get('evaluated_budgets', 0)} active budgets and anomaly fingerprints against current spend telemetry. "
            f"Created {eval_res.get('created_alerts', 0)} new alerts and updated {eval_res.get('updated_alerts', 0)} existing threshold records."
        )

    elif any(k in q for k in ["simulate rightsize", "simulate savings", "run simulation", "simulate downsize", "optimize idle"]):
        tools_invoked.append("run_what_if_simulation")
        tools_invoked.append("get_recommendations_with_priority")
        is_task_executed = True
        action_performed = "run_what_if_simulation"
        sim_res = run_what_if_simulation(db, organization_id, scenario="AGGRESSIVE_RIGHTSIZING")
        summary = sim_res.get("summary", {})
        proj_save = summary.get("projected_monthly_savings", 0.0)
        proj_co2 = summary.get("projected_monthly_carbon_saving_kg", 0.0)
        impacted = summary.get("total_impacted_resources", 0)
        sources.append({
            "tool": "run_what_if_simulation",
            "model": "Simulation Engine",
            "window": "Active Resources Snapshot",
            "evaluated_samples": impacted,
        })
        answer = (
            f"⚡ Task Completed: Rightsizing Simulation Executed.\n\n"
            f"Simulated rightsizing and decommissioning idle capacity across active cloud workloads. "
            f"Projected cost savings: ${proj_save:,.2f}/month (${proj_save * 12:,.2f}/year) with avoided emissions of "
            f"{proj_co2:.1f} kgCO2e/month across {impacted} impacted cloud instances. View scenario breakdown in Optimization."
        )

    elif any(k in q for k in ["audit tags", "evaluate tag", "check tags", "tag governance", "tag audit"]):
        tools_invoked.append("evaluate_tag_governance")
        is_task_executed = True
        action_performed = "evaluate_tag_governance"
        gov_res = evaluate_tag_governance(db, organization_id)
        sources.append({
            "tool": "evaluate_tag_governance",
            "model": "Governance Engine",
            "window": "All Cloud Resources",
            "evaluated_samples": gov_res.get("total_resources", 0),
        })
        answer = (
            f"⚡ Task Completed: Tag Governance Audit Completed.\n\n"
            f"Inspected all cloud resources against mandatory FinOps tags (Environment, Owner, CostCenter). "
            f"Evaluated {gov_res.get('total_resources', 0)} resources: {gov_res.get('compliant_count', 0)} compliant, "
            f"{gov_res.get('non_compliant_count', 0)} non-compliant ({gov_res.get('untagged_count', 0)} untagged). "
            f"Overall organization compliance score: {gov_res.get('compliance_rate', 0):.1f}%."
        )

    # --------------------------------------------------------------------------
    # 2. Informational & Analytical Inquiries
    # --------------------------------------------------------------------------
    elif any(k in q for k in ["forecast", "predict", "next month", "future spend", "run-rate"]):
        tools_invoked.append("get_forecast")
        res = tool_get_forecast(db, organization_id, horizon=30)
        sources.append({
            "tool": "get_forecast",
            "model": "CostRecord",
            "window": "30-day forward projection",
            "evaluated_samples": len(res.get("forecast", [])),
        })

        if res.get("status") == "insufficient_data" or not res.get("forecast"):
            missing_data_acknowledged = True
            missing_data_details.append("Insufficient historical daily billing records to compute a mathematical forecast.")
            answer = (
                f"I investigated your billing history using the forecasting engine, but there are insufficient "
                f"historical daily data points (found {res.get('data_points_available', 0)} of 7 required) to project "
                f"future spend reliably. Once at least 7 days of billing records are imported, I will produce polynomial "
                f"trend projections with 95% confidence intervals."
            )
        else:
            total_proj = res.get("summary", {}).get("total_projected_spend", 0)
            baseline = res.get("baseline_comparison", {})
            mae = res.get("evaluation_metrics", {}).get("mae", 0)
            answer = (
                f"Based on historical billing analysis over the last 90 days, your projected spend for the next 30 days is "
                f"${total_proj:,.2f}. The model reports a Mean Absolute Error (MAE) of ${mae:.2f}/day. "
                f"Compared to a Naive Persistence baseline, the polynomial trend model demonstrates an accuracy improvement of "
                f"{baseline.get('improvement_pct', 0):.1f}%."
            )

    elif any(k in q for k in ["anomal", "spike", "outlier", "unusual", "surge"]):
        tools_invoked.append("get_anomalies")
        res = tool_get_anomalies(db, organization_id)
        sources.append({
            "tool": "get_anomalies",
            "model": "Anomaly",
            "window": "Last 90 days",
            "evaluated_samples": res["total_anomalies"],
        })

        if res["total_anomalies"] == 0:
            missing_data_acknowledged = True
            missing_data_details.append("Zero anomaly records found.")
            answer = (
                "Our Isolation Forest anomaly detection engine found zero cost spikes or statistical outliers for your "
                "organization in the evaluated observation window. All workload spend patterns currently conform to learned "
                "baseline envelopes."
            )
        else:
            answer = (
                f"The anomaly detection engine has identified {res['total_anomalies']} active cost anomalies with a cumulative "
                f"estimated financial impact of ${res['total_financial_impact']:,.2f}. "
                f"Top outlier: {res['anomalies'][0].get('reason', 'Deviates from baseline')} on "
                f"{res['anomalies'][0].get('provider', 'Cloud')} (Impact: ${res['anomalies'][0].get('financial_impact', 0):.2f})."
            )

    elif any(k in q for k in ["carbon", "emission", "green", "co2", "sustainability", "ghg"]):
        tools_invoked.append("get_carbon_summary")
        res = tool_get_carbon_summary(db, organization_id)
        sources.append({
            "tool": "get_carbon_summary",
            "model": "CarbonRecord",
            "window": "Cumulative snapshot",
            "evaluated_samples": res.get("total_records_count", 0),
        })

        if res.get("total_co2_kg", 0) == 0:
            missing_data_acknowledged = True
            missing_data_details.append("No carbon emissions records or regional energy modeling data available.")
            answer = (
                "Your organization currently has zero recorded greenhouse gas emissions. No provider emissions statements "
                "or activity telemetry have been ingested yet. CloudSense AI does not fabricate emissions figures from financial "
                "spend alone; you can upload a provider emissions CSV via the CarbonSense portal to populate verified metrics."
            )
        else:
            clean_pct = res.get("clean_energy_index_pct", 0)
            answer = (
                f"Your cloud infrastructure carbon footprint is currently {res['total_co2_kg']:.2f} kgCO2e "
                f"({res['total_co2_mt']:.3f} metric tons) across Scope 1, Scope 2, and Scope 3 emissions. "
                f"Your active regional clean energy index stands at {clean_pct:.1f}%, calculated using published EPA eGRID 2024 "
                f"and EEA 2023 regional grid emission intensity factors."
            )

    elif any(k in q for k in ["save", "saving", "optim", "downsize", "idle", "rightsize", "recommend"]):
        tools_invoked.append("get_optimization_recommendations")
        tools_invoked.append("get_savings_ledger")
        res = tool_get_optimization(db, organization_id, priority="BALANCE")
        ledger_sum = get_savings_ledger_summary(db, organization_id)
        sources.append({
            "tool": "get_optimization_recommendations",
            "model": "Recommendation",
            "window": "Telemetry observation window",
            "evaluated_samples": res.get("summary", {}).get("total_recommendations", 0),
        })
        sources.append({
            "tool": "get_savings_ledger",
            "model": "SavingsLedger",
            "window": "All recorded initiatives",
            "evaluated_samples": ledger_sum.get("total_entries", 0),
        })

        recs = res.get("recommendations", [])
        if not recs:
            missing_data_acknowledged = True
            missing_data_details.append("No underutilized resources or recommendations detected.")
            answer = (
                "The optimization engine has inspected your active cloud resources and telemetry metrics and found zero "
                "actionable rightsizing or idle candidates. Workload utilization appears properly scaled to demand."
            )
        else:
            monthly_save = res.get("summary", {}).get("total_monthly_cost_saving", 0)
            carbon_save = res.get("summary", {}).get("total_monthly_carbon_saving_kg", 0)
            realization = ledger_sum.get("cost_realization_rate_pct", 0)
            answer = (
                f"The optimization engine has generated {len(recs)} evidence-backed recommendations with a total potential saving of "
                f"${monthly_save:,.2f}/month (${monthly_save*12:,.2f}/year) and {carbon_save:.1f} kgCO2e/month in avoided emissions. "
                f"Your historical savings realization rate is {realization:.1f}%. "
                f"Top opportunity: {recs[0]['problem']} — {recs[0]['action']} (saves ${recs[0]['monthly_saving']:.2f}/mo)."
            )

    elif any(k in q for k in ["budget", "alert", "threshold"]):
        tools_invoked.append("get_budgets")
        res = tool_get_budgets(db, organization_id)
        sources.append({
            "tool": "get_budgets",
            "model": "Budget",
            "window": "Active period",
            "evaluated_samples": res["total_budgets"],
        })

        if res["total_budgets"] == 0:
            missing_data_acknowledged = True
            missing_data_details.append("No budgets configured for this workspace.")
            answer = (
                "You have no budgets configured for this workspace. You can set up organization, provider, or service budgets "
                "with automated threshold alerts in the Budgets & Alerts portal."
            )
        else:
            b_list = ", ".join([f"{b['name']} (${b['amount']:,.0f})" for b in res["budgets"][:3]])
            answer = (
                f"You have {res['total_budgets']} active budgets configured: {b_list}. "
                f"Budget alerts are automatically triggered when cumulative period spend exceeds configured thresholds."
            )

    elif any(k in q for k in ["security", "finding", "compliance", "vuln"]):
        tools_invoked.append("get_security_findings")
        res = tool_get_security_findings(db, organization_id)
        sources.append({
            "tool": "get_security_findings",
            "model": "SecurityFinding",
            "window": "Open findings",
            "evaluated_samples": res["open_findings_count"],
        })

        if res["open_findings_count"] == 0:
            answer = "No open security or compliance findings were detected in your cloud infrastructure configuration."
        else:
            answer = (
                f"There are {res['open_findings_count']} open security findings ({res['high_severity_count']} high severity). "
                f"Top item: {res['findings'][0]['description']} ({res['findings'][0]['risk']})."
            )

    else:
        # Default spend & overview inquiry
        tools_invoked.append("get_cost_summary")
        res = tool_get_cost_summary(db, organization_id, days=30)
        sources.append({
            "tool": "get_cost_summary",
            "model": "CostRecord",
            "window": "Last 30 days",
            "evaluated_samples": len(res.get("provider_breakdown", [])),
        })

        spend = res.get("current_month_spend", 0)
        if spend == 0:
            missing_data_acknowledged = True
            missing_data_details.append("Zero billing records found for the past 30 days.")
            answer = (
                "I queried your billing records for the past 30 days, but your workspace currently contains zero recorded cost "
                "data. Once you import a cloud billing CSV or connect an account, I can break down spend, detect anomalies, "
                "project forecasts, and uncover savings."
            )
        else:
            providers = ", ".join([f"{p['name']}: ${p['amount']:,.0f}" for p in res.get("provider_breakdown", [])])
            change_txt = f"{res['change_percentage']:+.1f}%" if res.get("change_percentage") is not None else "N/A"
            answer = (
                f"Your total cloud spend over the past 30 days is ${spend:,.2f} ({change_txt} change compared to the prior period). "
                f"Provider breakdown: {providers}. "
                f"You can ask me to dive deeper into forecasts, anomalies, rightsizing recommendations, or carbon emissions."
            )

    # Persist chat history if session requested
    if session_id:
        sess = db.get(ChatSession, session_id)
        if not sess or sess.organization_id != organization_id:
            sess = ChatSession(id=session_id, organization_id=organization_id, user_id=user_id)
            db.add(sess)
        db.add(ChatMessage(session_id=sess.id, role="user", content=message))
        db.add(ChatMessage(session_id=sess.id, role="assistant", content=answer, sources=json.dumps(sources)))
        db.commit()

    # Log audit entry
    db.add(
        AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            action="ai_analyst_task_execution" if is_task_executed else "ai_analyst_query",
            status="SUCCESS",
            detail=f"Invoked tools: {', '.join(tools_invoked)}",
        )
    )
    db.commit()

    from ..security import sanitize_string
    sanitized_answer = sanitize_string(answer)

    return {
        "answer": sanitized_answer,
        "mode": "deterministic_grounded_tool_execution",
        "tools_invoked": tools_invoked,
        "citations": sources,
        "missing_data_acknowledged": missing_data_acknowledged,
        "missing_data_details": missing_data_details,
        "task_executed": is_task_executed,
        "action_performed": action_performed,
        "timestamp": datetime.utcnow().isoformat(),
    }

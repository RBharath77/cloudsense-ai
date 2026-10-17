# CloudSense AI — Project Status

Last Updated: Phase 6 CarbonSense and Emissions Data Provenance — COMPLETED

## 1. System Inventory & Verified Status

| Component | Status | Details |
|---|---|---|
| **CarbonSense™ Intelligence Engine** | Verified Working (Phase 6) | Source-aware greenhouse gas accounting (`backend/app/services/carbon_service.py`) supporting Scope 1, Scope 2 (market/location-based), and Scope 3 classification per GHG Protocol. Evaluates footprint without deriving emissions from financial spend. |
| **Provider Emissions CSV Ingestion** | Verified Working (Phase 6) | Transactional import endpoint (`POST /api/carbon/import`) accepting customer statements (AWS, Azure, GCP, or audit reports) with strict header/numeric validation, non-negative assertions, and zero partial writes. |
| **Regional Grid Intensity Factors Registry** | Verified Working (Phase 6) | Authoritative factor registry citing published benchmarks (EPA eGRID 2024, EEA 2023, Fingrid) mapping regional intensity (gCO2e/kWh) and clean energy percentages across cloud regions. |
| **Persistent Carbon Budgets** | Verified Working (Phase 6) | Persistent targets (`CarbonBudget` model) tracking cumulative emissions against reduction goals, calculating utilization %, and evaluating dynamic status transitions (`OK`, `WARNING`, `EXCEEDED`). |
| **Frontend UI (CarbonSense Dashboard)** | Verified Working (Phase 6) | Rich interface in `frontend/components/Analytics.tsx` and `frontend/app/carbon/page.tsx` featuring KPI cards (Total kgCO2e/MTCO2e, Reported vs Estimated ratio), Provider & GHG Scopes bar charts, clean energy index, methodology disclosure, CSV import modal, and budget creation dialog. Passed clean Next.js build (23/23 static pages). |
| **Multi-Horizon ML Forecasting Engine** | Verified Working (Phase 5) | Trend forecasting model (`backend/app/services/forecast_service.py` & `backend/app/ml.py`) supporting multi-horizon forecasting (7D–90D), provider filtering, dynamic confidence intervals (80%/95%), and non-negative clamping. |
| **Model Registry & Zero-Leakage Backtesting** | Verified Working (Phase 5) | Chronological backtest evaluation ($t < split$ train, $t \ge split$ test) evaluating MAE, RMSE, and benchmark comparison against a strict Naive Persistence Baseline (`improvement_pct`). |
| **Isolation Forest Anomaly Engine & RCA** | Verified Working (Phase 5) | Unsupervised anomaly detection (`backend/app/services/anomaly_service.py`) evaluating residual deviations against learned median envelopes with financial impact calculation and deterministic Root Cause Analysis. |
| **Persistent Budget Engine** | Verified Working (Phase 4) | Full CRUD service (`backend/app/services/budget_service.py`) supporting Organization, Provider, and Service scopes, configurable alert thresholds, live spend aggregation, and burn-rate projections. |
| **Deduplicated Alert Engine** | Verified Working (Phase 4) | Alert evaluation engine (`backend/app/services/alert_service.py`) with fingerprint-based SHA-256 deduplication: `sha256(org:entity:type:period)`. |
| **Tag Governance & Compliance** | Verified Working (Phase 4) | Resource compliance auditor (`backend/app/services/tag_governance.py`) checking resources against required tags (`Environment`, `Owner`, `CostCenter`, `Project`). |
| **Cost Aggregation & Explorer Service** | Verified Working (Phase 3) | Authoritative aggregation service (`backend/app/services/cost_aggregation.py`) providing multi-dimensional filtering, grouping, period-over-period comparison, and data lineage extraction. |
| **Reconciliation & Export Engine** | Verified Working (Phase 3) | Streaming CSV export endpoint (`/api/costs/export`) guaranteed to match API summary totals 100%. Sanitizes cells against formula injection (`=`, `+`, `-`, `@`, `\t`, `\r`). |
| **Billing Ingestion** | Verified Working (Phase 2) | Normalized, transactional CSV ingestion engine (`backend/app/services/billing_import.py`) with SHA-256 duplicate rejection and idempotency replay. |
| **Backend API** | Verified Working | FastAPI 0.116.1 running on Python 3.11.16 with tenant-scoped isolation. |
| **Test Suite** | Passing (47/47) | `pytest` passes 47/47 tests across all 8 test suites (`test_auth.py`, `test_billing_import.py`, `test_cost_explorer.py`, `test_budgets_alerts.py`, `test_dashboard.py`, `test_forecast_anomalies.py`, `test_carbonsense.py`, and `test_ml.py`). |
| **Git Version Control** | Active | Branch `phase-6-carbonsense-provenance` with clean diff. |

## 2. CarbonSense & Sustainability Invariants Verified

1. **Non-Fabrication Guarantee:** Emissions figures are never derived from financial dollar spend alone. Estimated figures are modeled from resource utilization, TDP energy consumption, PUE, and published grid intensity factors (EPA eGRID 2024 / EEA 2023).
2. **Provenance Distinction Invariant:** Provider-reported (`REPORTED`), activity-modeled (`ESTIMATED`), and synthetic (`DEMO`) records are distinctly identified in all API responses, summaries, and ledger tables.
3. **Unit Consistency:** All carbon weights are represented authoritatively in `kgCO2e`, with standardized metric ton conversion ($1\text{ MT} = 1000\text{ kg}$).
4. **CSV Ingestion Atomicity:** Carbon CSV imports enforce strict validation on dates, provider names, services, and non-negative `co2_kg`. Any single invalid row causes a complete transaction rollback with line-numbered diagnostics.
5. **Multi-Tenant Sustainability Isolation:** Carbon records, factors, imports, and reduction targets are strictly partitioned by authenticated `organization_id`. Tenant A cannot access Tenant B's emissions data or modify Tenant B's targets. Empty organizations safely return zeroed summaries without 500 crashes.

## 3. Test Evidence

```
============================= test session starts ==============================
platform darwin -- Python 3.11.16, pytest-8.4.1, pluggy-1.7.0 -- /Users/BharathR/Downloads/cloudsense-ai/.venv/bin/python3.11
cachedir: .pytest_cache
rootdir: /Users/BharathR/Downloads/cloudsense-ai
configfile: pytest.ini
testpaths: backend/tests
plugins: anyio-4.15.1
collected 47 items

backend/tests/test_auth.py::test_password_hash PASSED                    [  2%]
backend/tests/test_billing_import.py::test_valid_billing_csv_import PASSED [  4%]
backend/tests/test_billing_import.py::test_duplicate_file_rejection PASSED [  6%]
backend/tests/test_billing_import.py::test_idempotency_key_replay PASSED [  8%]
backend/tests/test_billing_import.py::test_invalid_rows_reporting_and_zero_partial_writes PASSED [ 10%]
backend/tests/test_billing_import.py::test_empty_csv_rejection PASSED    [ 12%]
backend/tests/test_billing_import.py::test_missing_required_headers PASSED [ 14%]
backend/tests/test_billing_import.py::test_multi_tenant_isolation_billing_imports PASSED [ 17%]
backend/tests/test_budgets_alerts.py::test_budget_crud_lifecycle PASSED  [ 19%]
backend/tests/test_budgets_alerts.py::test_budget_validation_errors PASSED [ 21%]
backend/tests/test_budgets_alerts.py::test_budget_spend_evaluation_and_status_transitions PASSED [ 23%]
backend/tests/test_budgets_alerts.py::test_alert_evaluation_and_deduplication PASSED [ 25%]
backend/tests/test_budgets_alerts.py::test_alert_triage_workflows PASSED [ 27%]
backend/tests/test_budgets_alerts.py::test_tag_governance_and_resource_compliance PASSED [ 29%]
backend/tests/test_budgets_alerts.py::test_empty_organization_budgets_and_alerts PASSED [ 31%]
backend/tests/test_budgets_alerts.py::test_multi_tenant_isolation_budgets_alerts PASSED [ 34%]
backend/tests/test_carbonsense.py::test_carbon_summary_aggregation PASSED [ 36%]
backend/tests/test_carbonsense.py::test_carbon_records_filtering PASSED  [ 38%]
backend/tests/test_carbonsense.py::test_carbon_factors_registry PASSED   [ 40%]
backend/tests/test_carbonsense.py::test_carbon_csv_import_success PASSED [ 42%]
backend/tests/test_carbonsense.py::test_carbon_csv_import_validation_errors PASSED [ 44%]
backend/tests/test_carbon_budget_lifecycle_and_status_transitions PASSED [ 46%]
backend/tests/test_carbonsense.py::test_empty_organization_carbon_safety PASSED [ 48%]
backend/tests/test_carbonsense.py::test_multi_tenant_isolation_carbon PASSED [ 51%]
backend/tests/test_cost_explorer.py::test_reconciliation_invariant PASSED [ 53%]
backend/tests/test_cost_explorer.py::test_cost_filtering_and_grouping PASSED [ 55%]
backend/tests/test_cost_explorer.py::test_cost_data_lineage PASSED       [ 57%]
backend/tests/test_cost_explorer.py::test_formula_injection_sanitization_in_csv_export PASSED [ 59%]
backend/tests/test_cost_explorer.py::test_empty_org_costs_and_dashboard PASSED [ 61%]
backend/tests/test_cost_explorer.py::test_multi_tenant_isolation_costs PASSED [ 63%]
backend/tests/test_dashboard.py::test_health PASSED                      [ 65%]
backend/tests/test_dashboard.py::test_login_demo_user PASSED             [ 68%]
backend/tests/test_dashboard.py::test_dashboard_seeded_organization PASSED [ 70%]
backend/tests/test_dashboard.py::test_dashboard_empty_organization_regression PASSED [ 72%]
backend/tests/test_dashboard.py::test_forecast_endpoint PASSED           [ 74%]
backend/tests/test_forecast_anomalies.py::test_multi_horizon_forecasting PASSED [ 76%]
backend/tests/test_forecast_anomalies.py::test_forecasting_evaluation_metrics_and_baseline PASSED [ 78%]
backend/tests/test_forecast_anomalies.py::test_provider_filtered_forecasting PASSED [ 80%]
backend/tests/test_forecast_anomalies.py::test_empty_organization_forecast_graceful PASSED [ 82%]
backend/tests/test_forecast_anomalies.py::test_list_anomalies_and_filtering PASSED [ 85%]
backend/tests/test_forecast_anomalies.py::test_dynamic_anomaly_detection_execution PASSED [ 87%]
backend/tests/test_forecast_anomalies.py::test_root_cause_analysis_endpoint PASSED [ 89%]
backend/tests/test_forecast_anomalies.py::test_multi_tenant_isolation_forecast_and_anomalies PASSED [ 91%]
backend/tests/test_ml.py::test_forecast PASSED                           [ 93%]
backend/tests/test_ml.py::test_forecast_multiple_horizons PASSED         [ 95%]
backend/tests/test_ml.py::test_forecast_insufficient_data PASSED         [ 97%]
backend/tests/test_ml.py::test_anomaly PASSED                            [100%]

======================= 47 passed, 4 warnings in 25.12s ========================
```

## 4. Next Phase: Phase 7 — Optimization, Savings Ledger, and What-If Simulator
- Target: Evidence-backed recommendation engine (idle detection, rightsizing, unattached volumes, RI/Savings Plans coverage). Scenario what-if simulator and verified savings ledger without altering live cloud infrastructure.
